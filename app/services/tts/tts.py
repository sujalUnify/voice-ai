import asyncio
import logging
from openai import AsyncOpenAI 

from app.config import OPENROUTER_API_KEY,TTS_MODEL  
from app.exceptions import LLMGenerationError


logger = logging.getLogger(__name__)

class TextToSpeech:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )

    async def audio_generation(self,text: str):  
        try:
            async with self.client.audio.speech.with_streaming_response.create(
                model=TTS_MODEL,
                input=text,
                voice="af_heart",
                response_format="pcm",
            ) as response: 
                async for chunk in response.iter_bytes():
                    yield chunk  

        except asyncio.CancelledError: 
            logger.info("STT generation cancelled")
            raise 

        except Exception as e: 
            logger.info("There is exception in TTS : %s",str(e))
            raise LLMGenerationError(1003,detail=str(e))