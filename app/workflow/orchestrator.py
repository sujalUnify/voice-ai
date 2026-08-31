from fastapi import APIRouter,WebSocket,WebSocketDisconnect
from app.helpers import VADSession
from app.helpers.stt import PcmToWav 
from app.services.stt import SpeechToText


router = APIRouter(
    prefix="/ws",
    tags=["voice-to-voice"]
)


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    vad = VADSession()
    collect_audio =bytearray()
    stt = SpeechToText()
    was_speaking = False
    try:
        while True:
            data = await websocket.receive_bytes()
            states = vad.detect_speech(data)
            if states:  
                was_speaking = True
                collect_audio.extend(data)  
            elif was_speaking: 
                was_speaking = False
                if collect_audio:
                    wav_bytes = PcmToWav.convert_pcm_to_wav(collect_audio)
                    collect_audio.clear()
                    text = await stt.transcribe(wav_bytes)
                    print(text)
                    print("Audio received of:", len(wav_bytes) / 1024, "KB")

    except WebSocketDisconnect as e:
        print(f"Client disconnected. Code: {e.code}")
    except Exception as e:
        print(f"Unexpected error: {e}")