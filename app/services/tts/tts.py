from openai import AsyncOpenAI
from app.config import OPENROUTER_API_KEY,TTS_MODEL 

class TextToSpeech:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )

    async def audio_generation(self,text: str): 
        async with self.client.audio.speech.with_streaming_response.create(
            model=TTS_MODEL,
            input=text,
            voice="eve",
            response_format="pcm",
        ) as response: 
            async for chunk in response.iter_bytes():
                yield chunk