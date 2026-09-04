from fastapi import APIRouter,WebSocket,WebSocketDisconnect
from app.helpers import VADSession
from app.helpers.stt import PcmToWav 
from app.services.stt import SpeechToText
from app.services.llm import TextToText
from app.services.tts import TextToSpeech


router = APIRouter(
    prefix="/ws",
    tags=["voice-to-voice"]
)

@router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    vad = VADSession()

    # Keep only last 70 ms
    MAX_PREBUFFER = 2240

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
            # print(states)
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
                        print("\nYou : ",transcription) 
                        print("Audio received of: ", len(wav_bytes) / 1024, "KB")  
                        print("AI response : ",end=" ")
                        async for chunk in llm.generate_response(transcription):
                            print(chunk, end="", flush=True) 
                            text_buffer += chunk 

                            if len(text_buffer) >= 5: 
                                sentence = text_buffer 
                                text_buffer = "" 

                                async for audio_chunk in tts.audio_generation(sentence): 
                                    await websocket.send_bytes(audio_chunk)
                    else: 
                        print("Transcipsion is empty")
                else: 
                    print("collected audio is empty.")


    except WebSocketDisconnect as e:
        print(f"Client had disconnected.")
    except Exception as e:
        print(f"Unexpected error: {e}")