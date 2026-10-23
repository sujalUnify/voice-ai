import asyncio
import contextlib
import json
import logging
import struct
import time
from collections import deque

from app.config import TTS_SAMPLE_RATE
from app.exceptions import LLMGenerationError
from app.services.llm import TextToText
from app.services.tts import TextToSpeech
from fastapi.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)

# How many TTS requests may be in flight at once: the next fragment's
# request starts while the current one is still streaming, so the model's
# TTFB for sentence N+1 hides inside the playback of sentence N.
MAX_INFLIGHT_TTS = 2


class _TTSStream:
    """A TTS request whose HTTP round-trip starts immediately on creation."""

    def __init__(self, agen):
        self._agen = agen
        self._first = None
        self._task = asyncio.create_task(self._prime())

    async def _prime(self):
        # touches the network: request sent, headers received, first PCM back
        self._first = await self._agen.__anext__()

    async def wait_started(self):
        await self._task

    async def chunks(self):
        if self._first is not None:
            yield self._first
            self._first = None
        async for chunk in self._agen:
            yield chunk

    def close(self):
        if not self._task.done():
            self._task.cancel()

    async def aclose(self):
        self.close()
        await asyncio.gather(self._task, return_exceptions=True)
        await self._agen.aclose()


class GenerateAndSpeak:
    def __init__(self, websocket):
        self.websocket = websocket
        self.llm = TextToText()
        self.tts = TextToSpeech()

    async def generate_and_speak(self, transcription: str, response_id: int, get_current_response_id, history_context):
        try:
            logger.info("Transcription: %r", transcription)
            # tts_rate lets the client build its playback context at the
            # exact rate the TTS emits — zero resampling anywhere.
            await self.websocket.send_text(json.dumps(
                {"user": transcription, "response_id": response_id, "tts_rate": TTS_SAMPLE_RATE}
            ))

            queue: asyncio.Queue = asyncio.Queue()
            worker = asyncio.create_task(self._tts_worker(queue, response_id, get_current_response_id))

            text_buffer = ""
            full_buffer = []
            first_fragment = True
            t0 = time.perf_counter()
            try:
                async for chunk in self.llm.generate_response(transcription, history_context):
                    if response_id != get_current_response_id():
                        return
                    if first_fragment and text_buffer == "":
                        logger.info("[stage] LLM first token %.0f ms", (time.perf_counter() - t0) * 1000)
                    await self.websocket.send_text(json.dumps({"ai": chunk, "response_id": response_id}))

                    text_buffer += chunk
                    full_buffer.append(chunk)

                    if first_fragment:
                        # flush as early as the voice sounds natural — a short
                        # first fragment is what minimises first-audio latency
                        end = text_buffer[-1:]
                        decimal_point = end == "." and text_buffer[-2:-1].isdigit()
                        flush = (end in (".", "!", "?", ",", "\n") and not decimal_point
                                 and len(text_buffer) >= 3) or len(text_buffer) >= 24
                    else:
                        decimal_point = text_buffer[-1:] == "." and text_buffer[-2:-1].isdigit()
                        flush = (text_buffer[-1:] in (".", "!", "?", "\n") and not decimal_point) \
                            or len(text_buffer) >= 200

                    if flush:
                        queue.put_nowait(text_buffer)  # never blocks → LLM keeps flowing
                        text_buffer = ""
                        first_fragment = False

                if text_buffer:
                    queue.put_nowait(text_buffer)
                history_context.add_conversation({"user": transcription, "ai": "".join(full_buffer)})

                await queue.put(None)  # "no more fragments" signal
                await worker           # normal exit: wait until the last audio is sent
            finally:
                # barge-in / error path: kill the worker, then reap it
                if not worker.done():
                    worker.cancel()
                    history_context.add_conversation({"user": transcription, "ai": "".join(full_buffer)})

                await self._reap_worker(worker)

        except asyncio.CancelledError:
            logger.info("Cancelled LLM Generation")
            raise
        except WebSocketDisconnect:
            logger.info("Websocket disconnected.")
            raise
        except LLMGenerationError as e:
            logger.error("Generation failed: %s", e)
            raise
        except Exception as e:
            logger.exception("Unexpected error in generate_and_speak")
            raise

    @staticmethod
    async def _reap_worker(worker: asyncio.Task):
        with contextlib.suppress(asyncio.CancelledError):
            await worker

    async def _tts_worker(self, queue: asyncio.Queue, response_id, get_current_response_id):
        pending: deque[_TTSStream] = deque()
        closed = False
        try:
            while True:
                # keep MAX_INFLIGHT_TTS requests on the wire; each one starts
                # the moment its text exists, not when the previous finishes
                while not closed and len(pending) < MAX_INFLIGHT_TTS:
                    if pending:
                        if queue.empty():
                            break
                        fragment = queue.get_nowait()
                    else:
                        fragment = await queue.get()
                    if fragment is None:
                        closed = True
                        break
                    pending.append(_TTSStream(self.tts.audio_generation(fragment)))

                if not pending:
                    if closed:
                        return
                    continue

                stream = pending.popleft()
                t_tts = time.perf_counter()
                await stream.wait_started()  # request sent + first PCM received
                logger.info("[stage] TTS first audio %.0f ms", (time.perf_counter() - t_tts) * 1000)
                prefix = struct.pack("!I", response_id)
                async for audio_chunk in stream.chunks():
                    if response_id != get_current_response_id():
                        return
                    await self.websocket.send_bytes(prefix + audio_chunk)
        finally:
            for stream in pending:
                await stream.aclose()
