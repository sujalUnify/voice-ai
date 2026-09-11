import json
import logging
import asyncio 
from fastapi import APIRouter,WebSocket,WebSocketDisconnect

from app.helpers import VADSession,GenerateAndSpeak,reap
from app.helpers.stt import PcmToWav
from app.services.stt import SpeechToText


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ws",
    tags=["voice-to-voice"]
)
@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected")

    # Keep only last 110 ms
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

    was_speaking = False

    async def process_utterance(wav_bytes: bytes, rid: int):
        nonlocal CURRENT_TASK
        try:
            transcription = await stt.transcribe(wav_bytes)
        except Exception:
            logger.exception("Transcription failed, dropping utterance")  # session survives
            return
        if not transcription or vad.speaking:
            # empty transcript, or user started talking again while we transcribed
            return
        CURRENT_TASK = asyncio.create_task(
            core_task.generate_and_speak(transcription, rid, get_current_response_id)
        )
    try:
        while True:
            data = await websocket.receive_bytes()
            # before_speak_audio_buffer.extend(data)
            # if len(before_speak_audio_buffer) > MAX_PREBUFFER:
            #     del before_speak_audio_buffer[:-MAX_PREBUFFER]
            # detech user speech
            is_speaking = vad.detect_speech(data)
            # if speaking then collect it 
            if is_speaking:
                if not was_speaking:
                    # SPEECH ONSET: snapshot pre-speech audio NOW, while it still
                    # holds the ~110 ms leading up to the first word
                    full_audio_buffer.extend(before_speak_audio_buffer)
                    before_speak_audio_buffer.clear()  
                    # barge-in: client may still be playing audio even though the
                    # generation task already finished — always tell it to stop
                    await websocket.send_text(json.dumps({"message":"stop","response_id":response_id})) 
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
                after_speak_audio_buffer.extend(bytearray(data)) 
            elif was_speaking:
                # END OF UTTERANCE
                was_speaking = False
                full_audio_buffer.extend(after_speak_audio_buffer)
                after_speak_audio_buffer.clear()
                before_speak_audio_buffer.clear()
                if len(full_audio_buffer) > 3200:   # ignore <100 ms blips
                    response_id += 1
                    wav_bytes = PcmToWav.convert_pcm_to_wav(bytes(full_audio_buffer))
                    full_audio_buffer.clear()
                    CURRENT_STT_TASK = asyncio.create_task(process_utterance(wav_bytes, response_id))  # don't block the loop
                else:
                    full_audio_buffer.clear() 
            else:
                # silence outside any utterance: keep the rolling window fresh
                before_speak_audio_buffer.extend(data)
                if len(before_speak_audio_buffer) > MAX_PREBUFFER:
                    del before_speak_audio_buffer[:-MAX_PREBUFFER]

    except WebSocketDisconnect as e:
        logger.info("Client disconnected")
        if CURRENT_TASK and not CURRENT_TASK.done():
            CURRENT_TASK.cancel() 
            CURRENT_TASK.add_done_callback(reap)
        if CURRENT_STT_TASK and not CURRENT_STT_TASK.done(): 
            CURRENT_STT_TASK.cancel() 
            CURRENT_STT_TASK.add_done_callback(reap)
    except Exception as e:
        logger.exception("Unexpected error in websocket loop: %s", e) 
        raise
