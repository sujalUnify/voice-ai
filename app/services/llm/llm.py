import logging
import asyncio

from app.exceptions import LLMGenerationError
from app.config import OPENROUTER_API_KEY, LLM_MODEL 
from langchain_openai import ChatOpenAI,StreamChunkTimeoutError


logger = logging.getLogger(__name__)

class TextToText:

    def __init__(self):

        with open("app/prompts/patient_prompt.md","r") as f: 
            self.prompt = f.read()

        self.client = ChatOpenAI(
            api_key=OPENROUTER_API_KEY,
            model=LLM_MODEL,
            streaming=True,
            base_url="https://openrouter.ai/api/v1",
        )


    async def generate_response(self, transcription: str,history_context):
        try:
            history = history_context.get_conversation()
            print("here is history : ",history)
            messages = [
                ("system", self.prompt),
            ]
            for conversation in history:
                if conversation.get("user"):
                    messages.append(("user", conversation["user"]))
                elif conversation.get("ai"):
                    messages.append(("ai", conversation["ai"]))

            messages.append(("user", transcription))

            async for chunk in self.client.astream(messages): 
                yield chunk.content

        except asyncio.CancelledError:
            logger.info("LLM generation cancelled")
            raise

        except StreamChunkTimeoutError as e:
            logger.warning("LLM stream timed out: %s", e)
            raise

        except Exception as e:
            logger.exception("Failed in text generation")
            raise LLMGenerationError(1002, detail=str(e)) from e