"""Probe OpenRouter TTS candidates: TTFB, stream shape, sample rate."""
import asyncio
import time
import sys

import aiohttp

def load_env(path=".env"):
    env = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

ENV = load_env()
KEY = ENV["OPENROUTER_API_KEY"]
URL = "https://openrouter.ai/api/v1/audio/speech"

# (model, voice, note)
CANDIDATES = [
    ("deepgram/flux-tts", "flux-brittany-en", "deepgram flux (voice-agent model)"),
    ("deepgram/aura-2", "aura-2-thalia-en", "deepgram aura-2"),
    ("mistralai/voxtral-mini-tts-2603", "en_paul_neutral", "voxtral mini tts (docs example)"),
    ("google/gemini-3.8-flash-lite-tts", "Zephyr", "gemini flash-lite tts"),
    ("microsoft/mai-voice-2.1-flash", "en-US-Andrew:MAI-Voice-2.1-Flash", "azure mai flash"),
    ("minimax/speech-2.8-turbo", "English_radiant_girl", "minimax turbo"),
    ("hexgrad/kokoro-82m", "af_heart", "kokoro 82m (tiny)"),
    ("x-ai/grok-voice-tts-1.0", "eve", "grok voice"),
    ("qwen/qwen-audio-3.0-tts-flash", "loongjohn", "qwen tts flash"),
    ("canopylabs/orpheus-3b-0.1-ft", "tara", "orpheus 3b"),
    ("sesame/csm-1b", "conversational_a", "sesame csm-1b"),
]

SHORT = "Yes."
MEDIUM = "Absolutely, John. I can help you set up a payment of two hundred and forty five dollars today."


async def probe(session, model, voice, text, label):
    payload = {"model": model, "input": text, "response_format": "pcm", "voice": voice}
    headers = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    t0 = time.perf_counter()
    try:
        async with session.post(URL, headers=headers, json=payload) as resp:
            hdr_ms = (time.perf_counter() - t0) * 1000
            if resp.status != 200:
                body = await resp.text()
                return f"{label:38s} HTTP {resp.status}: {body[:140]}"
            first = None
            nbytes = 0
            nchunks = 0
            last = None
            # record when we cross 32000 bytes (~1s of 16k mono audio)
            t_1s = None
            async for chunk in resp.content.iter_any():
                if first is None:
                    first = (time.perf_counter() - t0) * 1000
                nbytes += len(chunk)
                nchunks += 1
                if nbytes >= 32000 and t_1s is None:
                    t_1s = (time.perf_counter() - t0) * 1000
                last = (time.perf_counter() - t0) * 1000
            ct = resp.headers.get("content-type", "?")
            return (f"{label:38s} TTFB {first:6.1f}ms 1s-audio@{t_1s or -1:6.1f}ms total {last:6.1f}ms "
                    f"{nbytes:7d}B/{nchunks:3d}ch {ct}")
    except Exception as e:
        return f"{label:38s} ERROR {(time.perf_counter()-t0)*1000:6.1f}ms {type(e).__name__}: {e}"


async def main():
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    timeout = aiohttp.ClientTimeout(total=30)
    conn = aiohttp.TCPConnector(limit=4, ttl_dns_cache=300, keepalive_timeout=60)
    async with aiohttp.ClientSession(timeout=timeout, connector=conn) as session:
        for model, voice, note in CANDIDATES:
            if only and not any(o in model for o in only):
                continue
            print("---", model, f"({note})")
            r1 = await probe(session, model, voice, SHORT, "cold  'Yes.'")
            print(r1)
            r2 = await probe(session, model, voice, MEDIUM, "warm  medium sent.")
            print(r2)

asyncio.run(main())
