from dotenv import load_dotenv 
import os 

load_dotenv() 

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
STT_MODEL = os.getenv("STT_MODEL") 
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = os.getenv("TTT_MODEL")  
TTS_MODEL = os.getenv("TTS_MODEL")
SILENCE_DURATION_MS = int(os.getenv("SILENCE_DURATION_MS", "200"))
