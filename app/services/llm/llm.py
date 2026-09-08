import logging
from langchain_openai import ChatOpenAI
from app.config import OPENROUTER_API_KEY, LLM_MODEL


logger = logging.getLogger(__name__)

class TextToText:

    def __init__(self):
        self.client = ChatOpenAI(
            api_key=OPENROUTER_API_KEY,
            model=LLM_MODEL,
            streaming=True,
            base_url="https://openrouter.ai/api/v1",
        )

    async def generate_response(self, transcription: str):
        try:
            async for chunk in self.client._astream(transcription): 
                yield chunk.message.content
        except Exception as e:
            logger.exception("Failed in text Generation : %s",str(e))
            yield f"Error: {str(e)}"