import json 
import struct
import logging
import asyncio
import contextlib
from app.services.llm import TextToText 
from app.services.tts import TextToSpeech 
from fastapi.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)

class GenerateAndSpeak: 
    def __init__(self,websocket):
        self.websocket = websocket 
        self.llm = TextToText()
        self.tts = TextToSpeech()

    async def generate_and_speak(self, transcription : str, response_id : int, get_current_response_id,history_context):
        try:
            logger.info("Transcription had generated")
            await self.websocket.send_text(json.dumps({"user": transcription, "response_id": response_id}))
            logger.info("Started generating response")

            queue: asyncio.Queue = asyncio.Queue()
            worker = asyncio.create_task(self._tts_worker(queue, response_id, get_current_response_id))

            text_buffer = ""
            full_buffer = ""
            first_fragment = True
            try:
                async for chunk in self.llm.generate_response(transcription,history_context):
                    if response_id != get_current_response_id():
                        return
                    await self.websocket.send_text(json.dumps({"ai": chunk, "response_id": response_id}))
                    text_buffer += chunk 
                    full_buffer += chunk

                    is_sentence_end = text_buffer[-1:] in (".", "!", "?", "\n")
                    # first fragment: flush small so the voice starts fast;
                    # after that: sentence boundaries, with a safety valve
                    long_enough = (first_fragment and (len(text_buffer) > 15) or len(text_buffer) > 120)

                    if is_sentence_end or long_enough:
                        queue.put_nowait(text_buffer)   # never blocks → LLM keeps flowing
                        text_buffer = ""
                        first_fragment = False

                if text_buffer:
                    queue.put_nowait(text_buffer) 
                history_context.add_conversation({"user":transcription,"ai":full_buffer})

                await queue.put(None)   # "no more fragments" signal
                await worker            # normal exit: wait until the last audio is sent
            finally:
                # barge-in / error path: the worker is mid-fragment → kill it, then reap it
                if not worker.done():
                    worker.cancel()
                    history_context.add_conversation({"user":transcription,"ai":full_buffer})

                with contextlib.suppress(asyncio.CancelledError):
                    await worker

        except asyncio.CancelledError:
            logger.info("Cancelled LLM Generation")
            raise
        except WebSocketDisconnect:
            logger.info("Websocket disconnected.")
            raise
        except Exception as e:
            logger.info("There is error : %s", str(e))
            raise

    async def _tts_worker(self, queue, response_id, get_current_response_id):
        while True:
            fragment = await queue.get()
            if fragment is None:
                return
            await self._speak(fragment, response_id, get_current_response_id)
    async def _speak(self,text: str,response_id,get_current_response_id): 
            try:
                async for audio_chunk in self.tts.audio_generation(text):
                    if response_id != get_current_response_id():
                        return
                    response_id_in_bytes = struct.pack("!I",response_id) 
                    final_bytes = response_id_in_bytes + audio_chunk
                    await self.websocket.send_bytes(final_bytes)
            except Exception as e: 
                raise Exception("Something went wrong : ",str(e))