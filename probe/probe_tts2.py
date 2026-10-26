"""Round 2: TTS TTFB variance + remaining candidates; Groq-direct LLM TTFT."""
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

SHORT = "Sure."
SYSTEM_PROMPT = open("app/prompts/patient_prompt.md", encoding="utf-8").read()


async def tts_probe(session, model, voice, text, fmt="pcm"):
    payload = {"model": model, "input": text, "response_format": fmt}
    if voice:
        payload["voice"] = voice
    t0 = time.perf_counter()
    try:
        async with session.post(
            "https://openrouter.ai/api/v1/audio/speech",
            headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"},
            json=payload,
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                return (time.perf_counter()-t0)*1000, -1, f"HTTP {resp.status}: {body[:90]}"
            first = None
            n = 0
            async for chunk in resp.content.iter_any():
                if first is None:
                    first = (time.perf_counter() - t0) * 1000
                n += 1
            return first, (time.perf_counter()-t0)*1000, f"{n} chunks"
    except Exception as e:
        return -1, -1, f"{type(e).__name__}: {str(e)[:70]}"


async def main():
    timeout = aiohttp.ClientTimeout(total=40)
    conn = aiohttp.TCPConnector(limit=4, keepalive_timeout=75, ttl_dns_cache=300)
    async with aiohttp.ClientSession(timeout=timeout, connector=conn) as s:
        # keepalive pinger in background (like production warm-connection loop)
        async def pinger():
            while True:
                try:
                    async with s.head("https://openrouter.ai/api/v1/models") as r:
                        await r.read()
                except Exception:
                    pass
                await asyncio.sleep(15)
        # ping = asyncio.create_task(pinger())

        print("=== TTS variance (5x short-input, warm conn)")
        for model, voice, fmt, n in [
            ("deepgram/aura-2", "aura-2-thalia-en", "pcm", 5),
            ("fish-audio/s2.1-pro-free:free", None, "pcm", 5),
            ("hexgrad/kokoro-82m", "af_heart", "pcm", 4),
            ("deepgram/flux-tts", "flux-brittany-en", "pcm", 4),
            ("openai/gpt-4o-mini-tts-2025-12-15", "alloy", "pcm", 3),
            ("minimax/speech-2.8-turbo", "English_radiant_girl", "mp3", 3),
            ("x-ai/grok-voice-tts-1.0", "eve", "pcm", 3),
            ("microsoft/mai-voice-2.1-flash", None, "pcm", 2),
            ("qwen/qwen-audio-3.0-tts-flash", "loongjohn", "pcm", 2),
        ]:
            ttfbs = []
            for i in range(n):
                t, tot, info = await tts_probe(s, model, voice, SHORT, fmt)
                ttfbs.append(t)
                if t < 0:
                    print(f"  {model:42s} FAIL {info}")
                    break
                await asyncio.sleep(0.4)
            else:
                good = [t for t in ttfbs if t > 0]
                if good:
                    print(f"  {model:42s} TTFB ms: {', '.join(f'{t:.0f}' for t in good)}  min={min(good):.0f} med={sorted(good)[len(good)//2]:.0f}")

        # Groq-direct LLM TTFT
        print("\n=== LLM TTFT: Groq DIRECT (same models served on OpenRouter)")
        for model, extra in [
            ("llama-3.1-8b-instant", {}),
            ("llama-3.1-8b-instant", {}),
            ("openai/gpt-oss-20b", {"reasoning_effort": "low"}),
            ("openai/gpt-oss-20b", {"reasoning_effort": "low"}),
            ("llama-3.3-70b-versatile", {}),
            ("meta-llama/llama-4-scout-17b-16e-instruct", {}),
        ]:
            body = {
                "model": model,
                "stream": True,
                "max_tokens": 100,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": "I lost my job last month, I really cannot pay the full amount right now."},
                ],
                **extra,
            }
            t0 = time.perf_counter()
            first = None
            ntok = 0
            try:
                async with s.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                    json=body,
                ) as r:
                    if r.status != 200:
                        print(f"  groq {model:44s} HTTP {r.status}: {(await r.text())[:100]}")
                        continue
                    async for line in r.content:
                        line = line.strip()
                        if not line.startswith(b"data:"):
                            continue
                        d = line[5:].strip()
                        if d == b"[DONE]":
                            break
                        try:
                            j = json.loads(d)
                            c = ((j.get("choices") or [{}])[0].get("delta") or {}).get("content") or ""
                            if c:
                                if first is None:
                                    first = (time.perf_counter() - t0) * 1000
                                ntok += 1
                        except Exception:
                            pass
                total = (time.perf_counter() - t0) * 1000
                tpot = (total - first) / max(ntok - 1, 1) if first else 0
                print(f"  groq {model:44s} TTFT {first if first else -1:7.1f} ms | total {total:7.1f} ms | {ntok:3d} ch | tpot {tpot:5.1f}")
            except Exception as e:
                print(f"  groq {model:44s} ERR {type(e).__name__} {str(e)[:60]}")

asyncio.run(main())
