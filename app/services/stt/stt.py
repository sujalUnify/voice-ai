import asyncio
import logging

from openai import AsyncOpenAI

from app.config import GROQ_API_KEY, STT_MODEL, STT_TIMEOUT
from app.exceptions import LLMGenerationError

logger = logging.getLogger(__name__)

# 100 ms of silence as a canonical WAV — a near-free request that opens the
# connection before the user's first real utterance
_SILENCE_WAV = b"RIFF" + (36 + 1600).to_bytes(4, "little") + b"WAVEfmt " + \
    (16).to_bytes(4, "little") + (1).to_bytes(2, "little") + (1).to_bytes(2, "little") + \
    (16000).to_bytes(4, "little") + (32000).to_bytes(4, "little") + (2).to_bytes(2, "little") + \
    (16).to_bytes(2, "little") + b"data" + (1600).to_bytes(4, "little") + bytes(1600)


class SpeechToText:
    """Groq Whisper transcription with a hard timeout and one retry."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )

    async def warm_up(self):
        """Open DNS+TLS to Groq so the first real utterance skips the handshake."""
        try:
            await self.transcribe(_SILENCE_WAV)
        except Exception:
            pass  # warmup best-effort only

    async def transcribe(self, wav_bytes: bytes) -> str:
        last_exc = None
        for attempt in (1, 2):
            try:
                transcription = await asyncio.wait_for(
                    self.client.audio.transcriptions.create(
                        file=("audio.wav", wav_bytes),
                        model=STT_MODEL,
                        response_format="text",
                        temperature=0.01,
                    ),
                    STT_TIMEOUT,
                )
                return transcription
            except asyncio.TimeoutError:
                logger.warning("STT attempt %d timed out after %.0fs", attempt, STT_TIMEOUT)
                last_exc = asyncio.TimeoutError()
            except asyncio.CancelledError:
                logger.info("STT generation cancelled")
                raise
            except Exception as e:
                logger.exception("Failed to create transcription : %s", str(e))
                raise LLMGenerationError(1001, detail=str(e))
        raise LLMGenerationError(1001, detail=f"STT timed out twice: {last_exc!r}")
