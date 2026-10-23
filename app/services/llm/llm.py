import asyncio
import logging

from openai import AsyncOpenAI

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MAX_TOKENS, LLM_MODEL, LLM_STALL_TIMEOUT
from app.exceptions import LLMGenerationError

logger = logging.getLogger(__name__)


class TextToText:
    """Streaming LLM over any OpenAI-compatible gateway.

    Uses the raw AsyncOpenAI SDK (httpx, connection-pooled) instead of
    langchain: one less abstraction between the SSE bytes and the TTS
    pipeline, and measurably lower time-to-first-token.

    Every stream is closed explicitly on all exit paths (barge-in
    included) — an abandoned stream poisons its pooled connection and the
    next turn's stream then stalls forever. A stall watchdog aborts a
    stream that never produces content and retries once.
    """

    def __init__(self):
        with open("app/prompts/patient_prompt.md", "r", encoding="utf-8") as f:
            self.prompt = f.read()
        self.client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        logger.info("LLM model: %s @ %s", LLM_MODEL, LLM_BASE_URL)

    def _build_messages(self, transcription: str, history_context) -> list[dict]:
        messages = [{"role": "system", "content": self.prompt}]
        for turn in history_context.get_conversation():
            if "user" in turn:
                messages.append({"role": "user", "content": turn["user"]})
            elif "ai" in turn:
                messages.append({"role": "assistant", "content": turn["ai"]})
        messages.append({"role": "user", "content": transcription})
        return messages

    async def warm_up(self):
        """Open the TLS connection (and DNS) before the first real turn."""
        try:
            await self.client.models.list()
        except Exception as e:
            logger.warning("LLM warmup failed (non-fatal): %s", e)

    async def _stream_once(self, transcription: str, history_context):
        return await self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=self._build_messages(transcription, history_context),
            stream=True,
            max_tokens=LLM_MAX_TOKENS,
        )

    async def generate_response(self, transcription: str, history_context):
        try:
            for attempt in (1, 2):
                stream = await self._stream_once(transcription, history_context)
                try:
                    chunks = stream.__aiter__()
                    # watchdog: if no first token arrives in time, the stream
                    # is dead — abort and retry on a fresh connection
                    first = await asyncio.wait_for(chunks.__anext__(), LLM_STALL_TIMEOUT)
                    content = first.choices[0].delta.content if first.choices else None
                    if content:
                        yield content
                    async for chunk in chunks:
                        if not chunk.choices:
                            continue
                        content = chunk.choices[0].delta.content
                        if content:
                            yield content
                    return
                except asyncio.TimeoutError:
                    await stream.close()
                    if attempt == 2:
                        logger.warning("LLM stream stalled twice, giving up")
                        return
                    logger.warning("LLM stream stalled before first token, retrying")
                    continue
                except asyncio.CancelledError:
                    raise
                except GeneratorExit:
                    raise
                finally:
                    # ALWAYS release the HTTP stream — cancellation and
                    # generator-close included — or the pool gets poisoned
                    await stream.close()

        except asyncio.CancelledError:
            logger.info("LLM generation cancelled")
            raise

        except GeneratorExit:
            raise

        except Exception as e:
            logger.exception("Failed in text generation")
            raise LLMGenerationError(1002, detail=str(e)) from e
