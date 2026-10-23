import asyncio
import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import TTS_PROVIDER, TTS_SAMPLE_RATE
from app.helpers import VADSession, GenerateAndSpeak, reap, ConversationProcessor
from app.helpers.stt import PcmToWav
from app.services.stt import SpeechToText

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ws",
    tags=["voice-to-voice"]
)

# bytes of 16 kHz mono PCM ≈ 100 ms — utterances shorter than this are blips
MIN_UTTERANCE_BYTES = 3200

# Start STT speculatively after this many trailing-silence frames (~16 ms each)
# instead of waiting for the full end-of-speech budget. If speech resumes, the
# barge-in path cancels it; if end-of-speech confirms, STT is already in flight.
SPECULATIVE_STT_FRAMES = 8


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected (tts=%s %d Hz)", TTS_PROVIDER, TTS_SAMPLE_RATE)

    # Keep only last ~110 ms of pre-speech audio (3500 bytes @ 16 kHz)
    MAX_PREBUFFER = 3500
    response_id = 0
    CURRENT_TASK: None | asyncio.Task = None
    CURRENT_STT_TASK: None | asyncio.Task = None

    def get_current_response_id():
        return response_id

    vad = VADSession()

    before_speak_audio_buffer = bytearray()
    after_speak_audio_buffer = bytearray()
    full_audio_buffer = bytearray()
    stt = SpeechToText()
    core_task = GenerateAndSpeak(websocket)
    history_context = ConversationProcessor()
    was_speaking = False

    # Warm every connection in the background while the user starts talking:
    # LLM TLS, TTS session + pooled connection. First turn skips the handshake.
    # (asyncio.gather schedules its children the moment it is created.)
    warmup = asyncio.gather(
        core_task.llm.warm_up(),
        core_task.tts.warm_up(),
        stt.warm_up(),
        return_exceptions=True,
    )

    async def handle_transcript(transcription: str, rid: int, history_context: ConversationProcessor, t_stt_start: float):
        nonlocal CURRENT_TASK
        if not transcription or vad.speaking:
            # empty transcript, or user started talking again while we transcribed
            return
        logger.info("[stage] STT %.0f ms -> %r", (time.perf_counter() - t_stt_start) * 1000, transcription)
        CURRENT_TASK = asyncio.create_task(
            core_task.generate_and_speak(transcription, rid, get_current_response_id, history_context)
        )
        CURRENT_TASK.add_done_callback(reap)

    async def process_utterance(wav_bytes: bytes, rid: int, history_context: ConversationProcessor, t_eou: float):
        try:
            t0 = time.perf_counter()
            transcription = await stt.transcribe(wav_bytes)
        except Exception:
            logger.exception("Transcription failed, dropping utterance")  # session survives
            return
        logger.info("[stage] EOU->transcript %.0f ms", (time.perf_counter() - t_eou) * 1000)
        await handle_transcript(transcription, rid, history_context, t0)

    async def finalize_speculative(speculative: asyncio.Task, rid: int, history_context: ConversationProcessor, t_spec: float):
        """Adopt an in-flight speculative STT when end-of-speech confirms."""
        try:
            transcription = await speculative
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Speculative transcription failed, dropping utterance")
            return
        await handle_transcript(transcription, rid, history_context, t_spec)

    try:
        speculative_started = False
        while True:
            data = await websocket.receive_bytes()
            is_speaking = vad.detect_speech(data)
            if is_speaking:
                if not was_speaking:
                    # SPEECH ONSET: snapshot pre-speech audio NOW, while it still
                    # holds the ~110 ms leading up to the first word
                    full_audio_buffer.extend(before_speak_audio_buffer)
                    before_speak_audio_buffer.clear()
                    speculative_started = False
                    # barge-in: client may still be playing audio even though the
                    # generation task already finished — always tell it to stop
                    await websocket.send_text(json.dumps({"message": "stop", "response_id": response_id}))
                if CURRENT_TASK and not CURRENT_TASK.done():
                    CURRENT_TASK.cancel()
                    CURRENT_TASK.add_done_callback(reap)
                    logger.info("Current task is cancelled.")
                CURRENT_TASK = None
                if CURRENT_STT_TASK and not CURRENT_STT_TASK.done():
                    CURRENT_STT_TASK.cancel()
                    CURRENT_STT_TASK.add_done_callback(reap)
                CURRENT_STT_TASK = None
                was_speaking = True
                after_speak_audio_buffer.extend(data)
                # speculative STT: the user's pause is long enough that this is
                # very likely a turn ending — get the transcription started now
                if not speculative_started and vad.silence_run >= SPECULATIVE_STT_FRAMES:
                    speculative_started = True
                    t_spec = time.perf_counter()
                    wav_bytes = PcmToWav.convert_pcm_to_wav(
                        bytes(full_audio_buffer + after_speak_audio_buffer)
                    )
                    CURRENT_STT_TASK = asyncio.create_task(stt.transcribe(wav_bytes))
            elif was_speaking:
                # END OF UTTERANCE (full silence budget elapsed)
                was_speaking = False
                full_audio_buffer.extend(after_speak_audio_buffer)
                after_speak_audio_buffer.clear()
                before_speak_audio_buffer.clear()
                if len(full_audio_buffer) > MIN_UTTERANCE_BYTES:
                    response_id += 1
                    rid = response_id
                    if speculative_started and CURRENT_STT_TASK and not CURRENT_STT_TASK.done():
                        # adopt the speculative transcription already in flight
                        CURRENT_STT_TASK = asyncio.create_task(
                            finalize_speculative(CURRENT_STT_TASK, rid, history_context, t_spec)
                        )
                    else:
                        wav_bytes = PcmToWav.convert_pcm_to_wav(bytes(full_audio_buffer))
                        CURRENT_STT_TASK = asyncio.create_task(
                            process_utterance(wav_bytes, rid, history_context, time.perf_counter())
                        )
                    full_audio_buffer.clear()
                else:
                    full_audio_buffer.clear()
            else:
                # silence outside any utterance: keep the rolling window fresh
                before_speak_audio_buffer.extend(data)
                if len(before_speak_audio_buffer) > MAX_PREBUFFER:
                    del before_speak_audio_buffer[:-MAX_PREBUFFER]

    except WebSocketDisconnect:
        logger.info("Client disconnected")
        warmup.cancel()
        if CURRENT_TASK and not CURRENT_TASK.done():
            CURRENT_TASK.cancel()
            CURRENT_TASK.add_done_callback(reap)
        if CURRENT_STT_TASK and not CURRENT_STT_TASK.done():
            CURRENT_STT_TASK.cancel()
            CURRENT_STT_TASK.add_done_callback(reap)
    except Exception as e:
        logger.exception("Unexpected error in websocket loop: %s", e)
        raise
