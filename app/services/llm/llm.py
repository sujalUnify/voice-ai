import logging
import asyncio
import time
from app.exceptions import LLMGenerationError
from app.config import OPENROUTER_API_KEY, LLM_MODEL, GROQ_API_KEY
from langchain_openai import ChatOpenAI,StreamChunkTimeoutError
from langchain_groq import ChatGroq


logger = logging.getLogger(__name__)

class TextToText:

    def __init__(self):

        with open("app/prompts/patient_prompt.md","r") as f: 
            self.prompt = f.read()
        print("model used for LLM : ",LLM_MODEL)

        self.client = ChatGroq(
            api_key=GROQ_API_KEY,
            model=LLM_MODEL,
            streaming=True,
        )


    async def generate_response(self, transcription: str, history_context):
        try:
            history = history_context.get_conversation()

            messages = [
                ("system", self.prompt),
            ]

            for conversation in history:
                if conversation.get("user"):
                    messages.append(("user", conversation["user"]))
                elif conversation.get("ai"):
                    messages.append(("ai", conversation["ai"]))

            messages.append(("user", transcription))

            start = time.perf_counter()
            first_text = True

            async for chunk in self.client.astream(messages):

                content = chunk.content

                if content:
                    if first_text:
                        elapsed = (time.perf_counter() - start) * 1000
                        print(f"FIRST NON-EMPTY CHUNK: {elapsed:.1f} ms")
                        first_text = False
                yield content

        except asyncio.CancelledError:
            logger.info("LLM generation cancelled")
            raise

        except StreamChunkTimeoutError as e:
            logger.warning("LLM stream timed out: %s", e)
            raise

        except Exception as e:
            logger.exception("Failed in text generation")
            raise LLMGenerationError(1002, detail=str(e)) from e