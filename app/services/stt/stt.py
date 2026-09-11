import logging
import asyncio
from groq import AsyncGroq
from app.config import STT_MODEL, GROQ_API_KEY 
from app.exceptions.generation_exception import LLMGenerationError


logger = logging.getLogger(__name__)
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
                response_format ="text",
                temperature=0.01
            )
            return transcription 
        except asyncio.CancelledError: 
            logger.info("STT generation cancelled") 
            raise 

        except Exception as e:
            logger.exception("Failed to create transcription : %s",str(e)) 
            raise LLMGenerationError(1001,detail=str(e))