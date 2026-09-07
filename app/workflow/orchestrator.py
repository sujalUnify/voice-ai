from fastapi import APIRouter,WebSocket,WebSocketDisconnect
import logging
import json,base64

from app.helpers import VADSession
from app.helpers.stt import PcmToWav
from app.services.stt import SpeechToText
from app.services.llm import TextToText
from app.services.tts import TextToSpeech


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ws",
    tags=["voice-to-voice"]
)

@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected")
    vad = VADSession()

    # Keep only last 110 ms
    MAX_PREBUFFER = 3500

    before_speak_audio_buffer = bytearray()
    after_speak_audio_buffer = bytearray()
    full_audio_buffer = bytearray()
    stt = SpeechToText()
    llm = TextToText()
    tts = TextToSpeech()
    text_buffer = ""
    was_speaking = False
    try:
        while True:
            data = await websocket.receive_bytes()
            before_speak_audio_buffer.extend(data)
            if len(before_speak_audio_buffer) > MAX_PREBUFFER:
                del before_speak_audio_buffer[:-MAX_PREBUFFER]
            # detech user speech
            states = vad.detect_speech(data)
            # if speaking then collect it
            if states:
                was_speaking = True
                after_speak_audio_buffer.extend(bytearray(data))
            elif was_speaking:
                # if he finished speaking
                was_speaking = False
                if after_speak_audio_buffer:
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
                    transcription.strip()
                    if transcription != "":
                        logger.info("Transcription had generated")
                        await websocket.send_text(json.dumps({"user":transcription}))
                        logger.info("Started generating response")
                        async for chunk in llm.generate_response(transcription):
                            await websocket.send_text(json.dumps({"ai":chunk}))
                            text_buffer += chunk

                            if len(text_buffer) >= 5:
                                sentence = text_buffer
                                text_buffer = ""
                                logger.info("Started voice generation: %s", sentence)

                                async for audio_chunk in tts.audio_generation(sentence):
                                   base64_audio = base64.b64encode(audio_chunk).decode('utf-8')
                                   await websocket.send_text(json.dumps({"audio":base64_audio}))
                    else:
                        print("Transcipsion is empty")
                else:
                    print("collected audio is empty.")


    except WebSocketDisconnect as e:
        logger.info("Client disconnected")
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
