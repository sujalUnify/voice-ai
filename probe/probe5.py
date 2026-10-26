"""Round 5: Groq orpheus voices; gpt-4o-mini-tts reappear?; mai no-voice route; RTT breakdown."""
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


async def probe(session, url, key, payload, tag):
    t0 = time.perf_counter()
    try:
        async with session.post(
            url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        ) as resp:
            if resp.status != 200:
                return f"{tag:44s} HTTP {resp.status}: {(await resp.text())[:95]}"
            first = None
            n = 0
            nb = 0
            last = 0
            async for chunk in resp.content.iter_any():
                if first is None:
                    first = (time.perf_counter() - t0) * 1000
                nb += len(chunk)
                n += 1
                last = (time.perf_counter() - t0) * 1000
            return f"{tag:44s} TTFB {first:6.1f}ms total {last:6.1f}ms {nb}B/{n}ch {resp.headers.get('content-type','?')}"
    except Exception as e:
        return f"{tag:44s} ERR {type(e).__name__}: {str(e)[:60]}"


async def main():
    timeout = aiohttp.ClientTimeout(total=40)
    conn = aiohttp.TCPConnector(limit=4, keepalive_timeout=75, ttl_dns_cache=300)
    OR = "https://openrouter.ai/api/v1/audio/speech"
    GROQ = "https://api.groq.com/openai/v1/audio/speech"
    async with aiohttp.ClientSession(timeout=timeout, connector=conn) as s:
        print("=== Groq orpheus-v1-english (voice required)")
        for v in ["tara", "leah", "zac"]:
            for fmt in ["pcm", "wav"]:
                r = await probe(s, GROQ, GROQ_KEY,
                                {"model": "canopylabs/orpheus-v1-english", "input": SHORT, "voice": v, "response_format": fmt},
                                f"groq orpheus v={v} fmt={fmt}")
                print(r)

        print("\n=== gpt-4o-mini-tts retry x3 (both slugs)")
        for i in range(3):
            for slug in ["openai/gpt-4o-mini-tts-2025-12-15", "openai/gpt-4o-mini-tts"]:
                r = await probe(s, OR, OR_KEY, {"model": slug, "input": SHORT, "voice": "alloy", "response_format": "pcm"}, slug)
                print(r)
            await asyncio.sleep(1)

        print("\n=== mai-2.1-flash no-voice x4 (does lenient route return?)")
        for i in range(4):
            r = await probe(s, OR, OR_KEY, {"model": "microsoft/mai-voice-2.1-flash", "input": SHORT, "response_format": "pcm"}, "mai flash voice=None")
            print(r)
            await asyncio.sleep(1)

        print("\n=== mai-2.1 (non-flash) + mai-2.1-flash with voice, x3 each")
        for model, voice in [
            ("microsoft/mai-voice-2.1", "en-US-Grant:MAI-Voice-2.1"),
            ("microsoft/mai-voice-2.1-flash", "en-US-Grant:MAI-Voice-2.1-Flash"),
        ]:
            for i in range(3):
                r = await probe(s, OR, OR_KEY, {"model": model, "input": SHORT, "voice": voice, "response_format": "pcm"}, f"{model.split('/')[-1]} v=Grant")
                print(r)
            await asyncio.sleep(0.5)

asyncio.run(main())
