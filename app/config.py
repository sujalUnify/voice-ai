from dotenv import load_dotenv 
import os 

load_dotenv() 

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
STT_MODEL = os.getenv("STT_MODEL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
LLM_MODEL = os.getenv("TTT_MODEL")
# ElevenLabs: model_id + voice_id (default JBFqnCBsd6RMkjVDRZzb = "George").
# Flash is the lowest-latency model; output is raw 24 kHz mono PCM.
TTS_MODEL = os.getenv("TTS_MODEL", "eleven_flash_v2_5")
TTS_VOICE = os.getenv("TTS_VOICE", "JBFqnCBsd6RMkjVDRZzb")
TTS_SAMPLE_RATE = int(os.getenv("TTS_SAMPLE_RATE", "24000"))
SILENCE_DURATION_MS = int(os.getenv("SILENCE_DURATION_MS", "200"))

# --- long-term conversation memory (LLM curator via OpenRouter) ------------
# The last RECENT_MESSAGE_LIMIT individual messages (10 user/ai exchanges)
# stay in the main context. Older turns are distilled into fact entries by
# MEMORY_MODEL and kept in a plain dict; when the store fills, the curator
# picks the least-important entries to remove.
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MEMORY_MODEL = os.getenv("MEMORY_MODEL", "google/gemini-2.5-flash-lite")
MEMORY_MAX_ENTRIES = int(os.getenv("MEMORY_MAX_ENTRIES", "20"))
RECENT_MESSAGE_LIMIT = int(os.getenv("RECENT_MESSAGE_LIMIT", "20"))
