"""Round 3: Groq current model catalog + LLM TTFT; deep-validate fast TTS models."""
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
SYSTEM_PROMPT = open("app/prompts/patient_prompt.md", encoding="utf-8").read()

SHORT = "Sure, John."
MEDIUM = "Absolutely, John. I can help you set up a payment of two hundred and forty five dollars today."


async def groq_models(session):
    async with session.get(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {GROQ_KEY}"},
    ) as r:
        d = await r.json()
        return [m["id"] for m in d.get("data", [])]


async def llm_probe(session, base, key, model, extra=None, label=""):
    body = {
        "model": model, "stream": True, "max_tokens": 100,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "I lost my job last month, I really cannot pay the full amount right now."},
        ],
        **(extra or {}),
    }
    t0 = time.perf_counter()
    first = None
    ntok = 0
    try:
        async with session.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=body,
        ) as r:
            if r.status != 200:
                return f"{label} HTTP {r.status}: {(await r.text())[:90]}"
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
        return f"{label} TTFT {first if first else -1:7.1f}ms total {total:7.1f}ms {ntok:3d}ch tpot {tpot:5.1f}"
    except Exception as e:
        return f"{label} ERR {type(e).__name__}: {str(e)[:70]}"


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
                return -1, -1, f"HTTP {resp.status}: {(await resp.text())[:90]}", "?"
            first = None
            n = 0
            last = 0
            nbytes = 0
            async for chunk in resp.content.iter_any():
                if first is None:
                    first = (time.perf_counter() - t0) * 1000
                nbytes += len(chunk)
                n += 1
                last = (time.perf_counter() - t0) * 1000
            ct = resp.headers.get("content-type", "?")
            return first, last, f"{n}ch {nbytes}B", ct
    except Exception as e:
        return -1, -1, f"{type(e).__name__}: {str(e)[:70]}, ?"


async def main():
    timeout = aiohttp.ClientTimeout(total=40)
    conn = aiohttp.TCPConnector(limit=4, keepalive_timeout=75, ttl_dns_cache=300)
    async with aiohttp.ClientSession(timeout=timeout, connector=conn) as s:
        print("=== Groq model catalog")
        try:
            models = await groq_models(s)
            for m in models:
                print("  ", m)
        except Exception as e:
            print("  catalog error:", e)

        print("\n=== Groq DIRECT LLM TTFT (2 runs each)")
        for m in models:
            if any(k in m for k in ("whisper", "tts", "guard", "embed", "prompt-guard", "compound")):
                continue
            for i in range(2):
                r = await llm_probe(s, "https://api.groq.com/openai/v1", GROQ_KEY, m,
                                    label=f"  {m:48s}")
                print(r)

        print("\n=== TTS deep validation (5x short, 2x medium)")
        for model, voice in [
            ("openai/gpt-4o-mini-tts-2025-12-15", "alloy"),
            ("microsoft/mai-voice-2.1-flash", None),
            ("microsoft/mai-voice-2.1-flash", "en-US-Andrew:MAI-Voice-2.1-Flash"),
        ]:
            ts = []
            for i in range(5):
                f, tot, info, ct = await tts_probe(s, model, voice, SHORT)
                ts.append(f)
                if f < 0:
                    print(f"  {model:48s} voice={voice} FAIL {info}")
                    break
                await asyncio.sleep(0.3)
            else:
                print(f"  {model:48s} voice={str(voice)[:28]:28s} TTFB: {', '.join(f'{t:.0f}' for t in ts)} min={min(ts):.0f} med={sorted(ts)[2]:.0f} {ct}")
            for i in range(2):
                f, tot, info, ct = await tts_probe(s, model, voice, MEDIUM)
                if f > 0:
                    print(f"    medium: TTFB {f:.0f}ms total {tot:.0f}ms {info}")

asyncio.run(main())
