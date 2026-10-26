"""Round 4: settle TTS choice. Retest fast candidates w/ correct slugs+voices,
stability check, Groq orpheus comparison."""
import asyncio
import json
import time

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
OR_KEY = ENV["OPENROUTER_API_KEY"]
GROQ_KEY = ENV["GROQ_API_KEY"]

SHORT = "Sure, John."
MEDIUM = "Absolutely, John. I can help you set up a payment of two hundred and forty five dollars today."


async def tts_probe(url, key, model, voice, text, fmt="pcm", model_field="model"):
    payload = {model_field: model, "input": text, "response_format": fmt}
    if voice:
        payload["voice"] = voice
    t0 = time.perf_counter()
    try:
        async with aiohttp.ClientSession() as inner:  # placeholder, replaced below
            pass
    except Exception:
        pass
    return None


async def probe(session, url, key, model, voice, text, fmt="pcm"):
    payload = {"model": model, "input": text, "response_format": fmt}
    if voice:
        payload["voice"] = voice
    t0 = time.perf_counter()
    try:
        async with session.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        ) as resp:
            if resp.status != 200:
                return -1, -1, 0, f"HTTP {resp.status}: {(await resp.text())[:100]}", "?"
            first = None
            n = 0
            nbytes = 0
            last = 0
            async for chunk in resp.content.iter_any():
                if first is None:
                    first = (time.perf_counter() - t0) * 1000
                nbytes += len(chunk)
                n += 1
                last = (time.perf_counter() - t0) * 1000
            return first, last, nbytes, f"{n}ch", resp.headers.get("content-type", "?")
    except Exception as e:
        return -1, -1, 0, f"{type(e).__name__}: {str(e)[:70]}", "?"


async def main():
    timeout = aiohttp.ClientTimeout(total=40)
    conn = aiohttp.TCPConnector(limit=4, keepalive_timeout=75, ttl_dns_cache=300)
    OR = "https://openrouter.ai/api/v1/audio/speech"
    GROQ = "https://api.groq.com/openai/v1/audio/speech"
    async with aiohttp.ClientSession(timeout=timeout, connector=conn) as s:
        cands = [
            ("OR gpt-4o-mini-tts-2025-12-15", OR, OR_KEY, "openai/gpt-4o-mini-tts-2025-12-15", "alloy"),
            ("OR gpt-4o-mini-tts (undated)", OR, OR_KEY, "openai/gpt-4o-mini-tts", "alloy"),
            ("OR mai-2.1-flash en-US-Ethan", OR, OR_KEY, "microsoft/mai-voice-2.1-flash", "en-US-Ethan:MAI-Voice-2.1-Flash"),
            ("OR mai-2.1-flash en-IN-Priya", OR, OR_KEY, "microsoft/mai-voice-2.1-flash", "en-IN-Priya:MAI-Voice-2.1-Flash"),
            ("OR aura-2 (control)", OR, OR_KEY, "deepgram/aura-2", "aura-2-thalia-en"),
            ("GROQ orpheus-v1-english", GROQ, GROQ_KEY, "canopylabs/orpheus-v1-english", None),
        ]
        for label, url, key, model, voice in cands:
            ts = []
            info = ct = ""
            for i in range(5):
                f, tot, nb, info, ct = await probe(s, url, key, model, voice, SHORT)
                if f < 0:
                    print(f"{label:34s} FAIL: {info}")
                    break
                ts.append(f)
                await asyncio.sleep(0.3)
            else:
                print(f"{label:34s} TTFB: {', '.join(f'{t:.0f}' for t in ts)}  min={min(ts):.0f} med={sorted(ts)[2]:.0f}  {ct}")
                f, tot, nb, info, ct = await probe(s, url, key, model, voice, MEDIUM)
                if f > 0:
                    print(f"{'':34s} medium: TTFB {f:.0f}ms total {tot:.0f}ms {nb}B {info}")

asyncio.run(main())
