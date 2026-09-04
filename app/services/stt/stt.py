from groq import AsyncGroq

from app.config import STT_MODEL, GROQ_API_KEY


class SpeechToText:

    def __init__(self):
        self.client = AsyncGroq(
            api_key=GROQ_API_KEY
        )
    
    async def transcribe(self, wav_bytes: bytes) -> str:
        try:
            transcription = await self.client.audio.transcriptions.create(
                file=("audio.wav", wav_bytes),
                model=STT_MODEL,
                response_format="text",
                temperature=0.01
            )
            return transcription
        except Exception as e: 
            return f"Error in the trasncription : {str(e)}"