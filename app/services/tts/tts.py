from openai import AsyncOpenAI
from app.config import OPENROUTER_API_KEY,TTS_MODEL  
from app.exceptions.generation_exception import LLMGenerationError

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
        except Exception as e: 
            raise LLMGenerationError(1003,detail=str(e))