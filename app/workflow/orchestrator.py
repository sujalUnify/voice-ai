import json
import logging
import asyncio 
import contextlib
from fastapi import APIRouter,WebSocket,WebSocketDisconnect

from app.helpers import VADSession
from app.helpers import GenerateAndSpeak
from app.helpers.stt import PcmToWav
from app.services.stt import SpeechToText


logger = logging.getLogger(__name__)

response_id = 0
def get_current_response_id():
    global response_id
    return response_id
router = APIRouter(
    prefix="/ws",
    tags=["voice-to-voice"]
)
@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    global response_id
    await websocket.accept()
    logger.info("Client connected")

    # Keep only last 110 ms
    MAX_PREBUFFER = 3500
    CURRENT_TASK: None | asyncio.Task = None

    vad = VADSession()
    before_speak_audio_buffer = bytearray()
    after_speak_audio_buffer = bytearray()
    full_audio_buffer = bytearray()
    stt = SpeechToText()
    core_task = GenerateAndSpeak(websocket)

    was_speaking = False
    try:
        while True:
            data = await websocket.receive_bytes()
            before_speak_audio_buffer.extend(data)
            if len(before_speak_audio_buffer) > MAX_PREBUFFER:
                del before_speak_audio_buffer[:-MAX_PREBUFFER]
            # detech user speech
            is_speaking = vad.detect_speech(data)
            # if speaking then collect it 
            if is_speaking:
                if CURRENT_TASK and not CURRENT_TASK.done():
                    CURRENT_TASK.cancel() 

                    with contextlib.suppress(asyncio.CancelledError):
                        await CURRENT_TASK 

                    CURRENT_TASK = None
                    logger.info("Current task is cancelled.")
                    await websocket.send_text(json.dumps({"message":"cancel","response_id":response_id})) 
                was_speaking = True
                after_speak_audio_buffer.extend(bytearray(data)) 
            elif was_speaking:
                # if he finished speaking
                was_speaking = False
                if after_speak_audio_buffer:
                    response_id+=1
                    #logic for Pre-Buffer

                    full_audio_buffer.extend(before_speak_audio_buffer)
                    full_audio_buffer.extend(after_speak_audio_buffer)

                    # create a wav file
                    wav_bytes = PcmToWav.convert_pcm_to_wav(full_audio_buffer)

                    #clear the buffer of audio
                    after_speak_audio_buffer.clear()
                    full_audio_buffer.clear()
                    before_speak_audio_buffer.clear()

                    #send audio for transcription
                    transcription = await stt.transcribe(wav_bytes)
                    if transcription != "":
                        CURRENT_TASK = asyncio.create_task(
                            core_task.generate_and_speak(
                                transcription,response_id,get_current_response_id))
                        # await core_task.generate_and_speak(transcription)
                    else:
                        logger.warning("Client disconnected")
                else:
                    logger.warning("Client disconnected")


    except WebSocketDisconnect as e:
        logger.info("Client disconnected")
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
