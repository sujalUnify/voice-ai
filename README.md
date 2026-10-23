# Voice AI — minimum-latency voice agent

Sub-second voice-to-voice pipeline:

```
mic → VAD (ten-vad, 16 ms frames) → speculative STT (Groq Whisper) → LLM (Groq, streaming)
     → sentence fragments → TTS (Groq Orpheus, streaming 24 kHz) → WebSocket binary → browser playback
```

## End-of-speech → first-audio budget (measured on this machine)

| Stage | Latency | Where |
|---|---|---|
| VAD end-of-speech wait | 228 ms | ten-vad + `SILENCE_DURATION_MS=200` |
| STT (speculative, warm) | ~250–290 ms | Groq `whisper-large-v3-turbo` |
| LLM first token | ~185–240 ms | Groq `qwen/qwen3.8-27b` |
| TTS first audio | ~210–270 ms | Groq `canopylabs/orpheus-v1-english` |
| WS transport + browser scheduling | ~40 ms | — |
| **Total (warm, off-peak)** | **~950 ms–1.0 s** | ~900 ms at `SILENCE_DURATION_MS=150` |

Provider load moves STT/LLM/TTS by hundreds of ms; the local pipeline adds
< 50 ms over the four network round-trips.

## Run

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `app/frontend/index.html` in a browser, click **Start Talking with AI**.

## Latency harness

`probe/e2e_latency_test.py` simulates a browser turn: streams a TTS-rendered
utterance as 32 ms frames to `/ws` and measures end-of-speech → first audio.

```powershell
# server on :8001
python -m uvicorn app.main:app --port 8001
python probe/e2e_latency_test.py 6
```

## Configuration (`.env`)

| Key | Default | Notes |
|---|---|---
| `TTS_PROVIDER` | `groq` | `openrouter` routes TTS via OpenRouter (`deepgram/aura-2`) at ~+500 ms TTFB |
| `TTS_MODEL` / `TTS_VOICE` | `canopylabs/orpheus-v1-english` / `autumn` | Groq Orpheus free tier: **100 requests/day** — exhausted → automatic fallback |
| `TTS_FALLBACK_PROVIDER` | `openrouter` | aura-2 keeps you talking when Orpheus is rate-limited |
| `TTT_MODEL` | `qwen/qwen3.8-27b` | 144 ms measured TTFT (gpt-oss-20b: ~480 ms) |
| `LLM_BASE_URL` | Groq | point at `https://openrouter.ai/api/v1` to route via OpenRouter (TTFT 865+ ms) |
| `SILENCE_DURATION_MS` | 200 | adds 1:1 to latency; 150 is snappier but splits clause pauses |
| `LLM_STALL_TIMEOUT` | 4 s | dead-stream watchdog + retry |
| `STT_TIMEOUT` | 6–8 s | fail-fast on Groq STT hiccups (observed 6 s spikes) |

## Known tradeoffs

- **Orpheus free tier is 100 req/day** (≈ 25–40 responses). A paid Groq tier or
  `TTS_PROVIDER=openrouter` lifts it. On exhaustion the aura-2 fallback speaks.
- **Endpointing vs pauses**: sub-200 ms silence budgets split natural clause
  pauses into separate turns (the partial response is barged in by the
  remainder — responses stay correct, but you'll hear more barge-ins).
- **Network floor**: STT+LLM+TTS are three serial US round-trips (~600 ms of
  RTT from India). A local STT or closer inference regions would break this.
