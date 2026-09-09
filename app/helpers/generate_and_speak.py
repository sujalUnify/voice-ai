import json 
import base64
import logging
import asyncio
from app.services.llm import TextToText 
from app.services.tts import TextToSpeech

logger = logging.getLogger(__name__)

class GenerateAndSpeak: 
    def __init__(self,websocket):
        self.websocket = websocket 
        self.llm = TextToText()
        self.tts = TextToSpeech()

    async def generate_and_speak(self,transcription,response_id,get_current_response_id):  
        try:
            logger.info("Transcription had generated")
            await self.websocket.send_text(json.dumps({"user":transcription,"response_id":response_id}))
            logger.info("Started generating response")
            text_buffer = ""
            async for chunk in self.llm.generate_response(transcription):
                if response_id != get_current_response_id():
                    return
                await self.websocket.send_text(json.dumps({"ai":chunk,"reponse_id":response_id}))
                text_buffer += chunk

                # flush once a sentence is complete (or buffer gets too long)
                if text_buffer[-1:] in (".", "!", "?", "\n") or len(text_buffer) > 60:
                    logger.info("Started voice generation")
                    await self._speak(text_buffer,response_id,get_current_response_id)
                    text_buffer = ""

            # speak whatever is left after the stream ends
            if text_buffer:
                await self._speak(text_buffer,response_id,get_current_response_id)
                text_buffer = "" 
        except asyncio.CancelledError: 
            logger.info("Task is cancelled") 
            raise
        except Exception as e: 
            logger.info("There is error : %s",str(e)) 

    async def _speak(self,text: str,response_id,get_current_response_id): 
            try:
                async for audio_chunk in self.tts.audio_generation(text):
                    if response_id != get_current_response_id():
                        return
                    await self.websocket.send_text(json.dumps({"audio": base64.b64encode(audio_chunk).decode("utf-8"),"response_id":response_id}))
            except Exception as e: 
                raise Exception("SOmething went wrong : ",str(e))