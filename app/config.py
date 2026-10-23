import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- STT -------------------------------------------------------------------
# Groq direct. Measured on this machine: 284-333 ms for a 4 s clip vs
# 800-5580 ms for every OpenRouter STT route, so STT stays on Groq.
STT_MODEL = os.getenv("STT_MODEL", "whisper-large-v3-turbo")

# --- LLM (TTT) --------------------------------------------------------------
# Any OpenAI-compatible gateway works. Groq direct measured TTFT ~145 ms with
# the patient prompt (gpt-oss-20b ~480 ms; anything via OpenRouter 865+ ms).
# Point LLM_BASE_URL at https://openrouter.ai/api/v1 to route via OpenRouter.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY") or (
    GROQ_API_KEY if "groq.com" in LLM_BASE_URL else OPENROUTER_API_KEY
)
LLM_MODEL = os.getenv("TTT_MODEL", "qwen/qwen3.8-27b")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "200"))
# abort + retry a stream that produces no first token within this budget
LLM_STALL_TIMEOUT = float(os.getenv("LLM_STALL_TIMEOUT", "4"))

# STT hard ceiling; Groq occasionally hiccups for seconds (measured once: 6.3 s
# vs the usual ~300 ms) — fail fast and retry instead of stalling the turn
STT_TIMEOUT = float(os.getenv("STT_TIMEOUT", "8"))

# --- TTS --------------------------------------------------------------------
# Output contract is identical for both gateways: 16-bit LE mono PCM at
# TTS_SAMPLE_RATE (24 kHz), streamed chunk-by-chunk.
#   groq       -> canopylabs/orpheus-v1-english, ~200-240 ms TTFB (recommended)
#   openrouter -> deepgram/aura-2, ~700-740 ms TTFB (same-model catalog, slower hop)
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "groq").lower()
TTS_MODEL = os.getenv("TTS_MODEL", "canopylabs/orpheus-v1-english")
TTS_VOICE = os.getenv("TTS_VOICE", "autumn")
TTS_SAMPLE_RATE = int(os.getenv("TTS_SAMPLE_RATE", "24000"))

if TTS_PROVIDER == "groq":
    TTS_URL = "https://api.groq.com/openai/v1/audio/speech"
    TTS_API_KEY = GROQ_API_KEY
    TTS_KEEPALIVE_URL = "https://api.groq.com/openai/v1/models"
    # streamed WAV (needs RIFF header strip); raw PCM otherwise
    TTS_WIRE_FORMAT = "wav"
else:
    TTS_URL = "https://openrouter.ai/api/v1/audio/speech"
    TTS_API_KEY = OPENROUTER_API_KEY
    TTS_KEEPALIVE_URL = "https://openrouter.ai/api/v1/models"
    TTS_WIRE_FORMAT = "pcm"

# Cross-gateway fallback: when the primary is rate-limited or errors, fragments
# are spoken via OpenRouter (deepgram/aura-2, ~700 ms TTFB — slower but reliable).
TTS_FALLBACK_PROVIDER = os.getenv("TTS_FALLBACK_PROVIDER", "openrouter" if TTS_PROVIDER == "groq" else "").lower()
TTS_FALLBACK_MODEL = os.getenv("TTS_FALLBACK_MODEL", "deepgram/aura-2")
TTS_FALLBACK_VOICE = os.getenv("TTS_FALLBACK_VOICE", "aura-2-thalia-en")

# --- VAD / endpointing ------------------------------------------------------
# Trailing-silence budget before we declare end-of-speech. The VAD frame is
# 16 ms (512 bytes @ 16 kHz). Every ms here adds 1:1 to response latency, but
# too low chops natural mid-sentence pauses (humans pause 200-600 ms between
# clauses). 200 ms is the balance point; drop to 150 for maximum snappiness.
SILENCE_DURATION_MS = int(os.getenv("SILENCE_DURATION_MS", "200"))
VAD_THRESHOLD = float(os.getenv("VAD_THRESHOLD", "0.65"))
VAD_ONSET_FRAMES = int(os.getenv("VAD_ONSET_FRAMES", "7"))
