"""Probe 1) STT latency: Groq direct vs OpenRouter models. 2) LLM TTFT via OpenRouter.

Generates a test utterance WAV via a cheap TTS call, then times transcriptions.
Times LLM first-token latency with the project's real system prompt.
"""
import asyncio
import base64
import io
import json
import time
import wave

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

PHRASE = "Yes, I can pay two hundred and forty five dollars today, thank you."

TEST_PHRASES = [
    "Hi, who is this?",
    "I lost my job last month, I really cannot pay the full amount right now.",
    "Okay so what happens if I just ignore this?",
]

SYSTEM_PROMPT = open("app/prompts/patient_prompt.md", encoding="utf-8").read()


def pcm24k_to_wav16k(pcm: bytes, rate_in=24000, rate_out=16000) -> bytes:
    """Cheap linear resample to 16k mono wav (test-only)."""
    n_in = len(pcm) // 2
    import array
    a = array.array("h"); a.frombytes(pcm)
    n_out = int(n_in * rate_out / rate_in)
    out = array.array("h", bytes(2 * n_out))
    step = (n_in - 1) / max(n_out - 1, 1)
    for i in range(n_out):
        pos = i * step
        i0 = int(pos); frac = pos - i0
        out[i] = int(a[i0] * (1 - frac) + a[min(i0 + 1, n_in - 1)] * frac)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate_out)
        w.writeframes(out.tobytes())
    return buf.getvalue()


async def make_test_wav(session) -> bytes:
    t0 = time.perf_counter()
    async with session.post(
        "https://openrouter.ai/api/v1/audio/speech",
        headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"},
        json={"model": "deepgram/aura-2", "voice": "aura-2-thalia-en",
              "input": PHRASE, "response_format": "pcm"},
    ) as r:
        pcm = await r.read()
        print(f"test wav: {len(pcm)}B pcm24k in {(time.perf_counter()-t0)*1000:.0f}ms")
        return pcm24k_to_wav16k(pcm)


async def probe_stt(session, label, model, wav, via_openrouter=True):
    t0 = time.perf_counter()
    try:
        if via_openrouter:
            async with session.post(
                "https://openrouter.ai/api/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {OR_KEY}"},
                data={"model": model, "response_format": "json"},
                data_files=None,
            ) as r:
                pass
    except Exception:
        pass
    # aiohttp multipart
    form = aiohttp.FormData()
    form.add_field("file", wav, filename="audio.wav", content_type="audio/wav")
    form.add_field("model", model)
    form.add_field("response_format", "json")
    url = "https://openrouter.ai/api/v1/audio/transcriptions"
    key = OR_KEY
    if not via_openrouter:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        key = GROQ_KEY
        form = aiohttp.FormData()
        form.add_field("file", wav, filename="audio.wav", content_type="audio/wav")
        form.add_field("model", model)
        form.add_field("response_format", "text")
        form.add_field("temperature", "0")
    t0 = time.perf_counter()
    try:
        async with session.post(url, headers={"Authorization": f"Bearer {key}"}, data=form) as r:
            body = await r.text()
            ms = (time.perf_counter() - t0) * 1000
            txt = ""
            try:
                j = json.loads(body)
                txt = j.get("text", body[:80])
            except Exception:
                txt = body[:80]
            print(f"STT {label:42s} {ms:7.1f} ms  -> {txt[:70]}")
    except Exception as e:
        print(f"STT {label:42s} ERROR {(time.perf_counter()-t0)*1000:6.1f}ms {type(e).__name__}: {str(e)[:80]}")


LLM_CANDIDATES = [
    "openai/gpt-oss-20b",
    "meta-llama/llama-3.1-8b-instruct",
    "meta-llama/llama-3.3-70b-instruct",
    "google/gemini-2.5-flash-lite",
    "google/gemini-3.5-flash-lite",
    "openai/gpt-5-nano",
    "openai/gpt-4.1-nano",
    "x-ai/grok-4-fast",
    "mistralai/mistral-small-3.2-24b-instruct",
    "minimax/minimax-m2.5",
]


async def probe_llm(session, model, user_msg):
    body = {
        "model": model,
        "stream": True,
        "max_tokens": 120,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    }
    t0 = time.perf_counter()
    first = None
    ntok = 0
    try:
        async with session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"},
            json=body,
        ) as r:
            if r.status != 200:
                txt = await r.text()
                print(f"LLM {model:42s} HTTP {r.status}: {txt[:110]}")
                return
            async for line in r.content:
                line = line.strip()
                if not line.startswith(b"data:"):
                    continue
                data = line[5:].strip()
                if data == b"[DONE]":
                    break
                try:
                    j = json.loads(data)
                    delta = (j.get("choices") or [{}])[0].get("delta") or {}
                    c = delta.get("content") or ""
                    rc = delta.get("reasoning") or ""
                    if c:
                        if first is None:
                            first = (time.perf_counter() - t0) * 1000
                        ntok += 1
                except Exception:
                    pass
            total = (time.perf_counter() - t0) * 1000
            if first is None:
                print(f"LLM {model:42s} no content tokens (reasoning-only?) total {total:.0f}ms")
            else:
                tpot = (total - first) / max(ntok - 1, 1)
                print(f"LLM {model:42s} TTFT {first:7.1f} ms | total {total:7.1f} ms | {ntok:3d} chunks | tpot {tpot:5.1f} ms")
    except Exception as e:
        print(f"LLM {model:42s} ERROR {(time.perf_counter()-t0)*1000:6.1f}ms {type(e).__name__}: {str(e)[:90]}")


async def main():
    timeout = aiohttp.ClientTimeout(total=60)
    conn = aiohttp.TCPConnector(limit=8, keepalive_timeout=60, ttl_dns_cache=300)
    async with aiohttp.ClientSession(timeout=timeout, connector=conn) as s:
        wav = await make_test_wav(s)
        print("\n=== STT (utterance: %r)" % PHRASE)
        await probe_stt(s, "groq whisper-large-v3-turbo (current)", "whisper-large-v3-turbo", wav, via_openrouter=False)
        await probe_stt(s, "groq whisper-large-v3-turbo (repeat)", "whisper-large-v3-turbo", wav, via_openrouter=False)
        await probe_stt(s, "or openai/whisper-large-v3-turbo", "openai/whisper-large-v3-turbo", wav)
        await probe_stt(s, "or openai/gpt-4o-mini-transcribe", "openai/gpt-4o-mini-transcribe", wav)
        await probe_stt(s, "or qwen/qwen3-asr-flash-2026-02-10", "qwen/qwen3-asr-flash-2026-02-10", wav)
        await probe_stt(s, "or nvidia/parakeet-tdt-0.6b-v3", "nvidia/parakeet-tdt-0.6b-v3", wav)
        await probe_stt(s, "or deepgram/nova-3", "deepgram/nova-3", wav)
        await probe_stt(s, "or x-ai/grok-stt-1.0", "x-ai/grok-stt-1.0", wav)
        await probe_stt(s, "or nvidia/nemotron-3.5-asr-streaming", "nvidia/nemotron-3.5-asr-streaming-multilingual-0.6b", wav)

        print("\n=== LLM TTFT (system prompt + 1 short user turn)")
        for m in LLM_CANDIDATES:
            await probe_llm(s, m, TEST_PHRASES[1])
        print("\n=== LLM repeat top candidate (warm)")
        await probe_llm(s, "meta-llama/llama-3.1-8b-instruct", TEST_PHRASES[2])

asyncio.run(main())
