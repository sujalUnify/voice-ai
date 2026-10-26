"""End-to-end latency harness.

Simulates the browser: streams a recorded utterance to /ws as 32 ms PCM16
frames (paced by wall clock, like the real mic), then keeps sending
silence, and measures
  t0 = first silence frame sent after speech  (≈ end of user speech)
  t1 = first assistant audio byte received
"""
import asyncio
import io
import json
import sys
import time
import wave

import aiohttp


def load_env(path=".env"):
    env = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


ENV = load_env()
OR_KEY = ENV["OPENROUTER_API_KEY"]

UTTERANCE = "I can pay two hundred forty five dollars today"

FRAME_BYTES = 512  # 32 ms @ 16 kHz mono PCM16
FRAME_SEC = 0.032
SILENCE = bytes(FRAME_BYTES)


def pcm24k_to_wav16k(pcm: bytes, rate_in=24000, rate_out=16000) -> bytes:
    import array
    a = array.array("h")
    a.frombytes(pcm)
    n_in = len(a)
    n_out = int(n_in * rate_out / rate_in)
    out = array.array("h", bytes(2 * n_out))
    step = (n_in - 1) / max(n_out - 1, 1)
    for i in range(n_out):
        pos = i * step
        i0 = int(pos)
        frac = pos - i0
        out[i] = int(a[i0] * (1 - frac) + a[min(i0 + 1, n_in - 1)] * frac)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate_out)
        w.writeframes(out.tobytes())
    return buf.getvalue()


async def make_speech_pcm():
    import os
    cache = "probe/_utterance_16k.wav"
    if os.path.exists(cache):
        with wave.open(cache, "rb") as w:
            return w.readframes(w.getnframes())
    async with aiohttp.ClientSession() as s:
        async with s.post(
            "https://openrouter.ai/api/v1/audio/speech",
            headers={"Authorization": f"Bearer {OR_KEY}", "Content-Type": "application/json"},
            json={"model": "deepgram/aura-2", "voice": "aura-2-thalia-en",
                  "input": UTTERANCE, "response_format": "pcm"},
        ) as r:
            pcm = await r.read()
    wav = pcm24k_to_wav16k(pcm)
    with wave.open(cache, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(wav[44:])
    return wav[44:]


async def paced_frames(ws, pcm, stop_after=None):
    """Send PCM as 32 ms frames on a wall-clock schedule. Returns send time."""
    t0 = time.perf_counter()
    sent = 0
    total = len(pcm) // FRAME_BYTES
    while sent < total:
        target = int((time.perf_counter() - t0) / FRAME_SEC)
        for _ in range(min(target - sent, total - sent)):
            await ws.send_bytes(pcm[sent * FRAME_BYTES:(sent + 1) * FRAME_BYTES])
            sent += 1
        await asyncio.sleep(0.002)
    return time.perf_counter() - t0


async def run_turn(ws, speech_pcm, turn_no, last_audio):
    first_audio_ms = None
    audio_bytes = 0
    n_audio_msgs = 0
    t0_turn = time.perf_counter()

    async def reader():
        nonlocal first_audio_ms, audio_bytes, n_audio_msgs
        while True:
            msg = await ws.receive()
            if msg.type == 2:  # binary
                last_audio[0] = time.perf_counter()
                now = (time.perf_counter() - t0_turn) * 1000
                if first_audio_ms is None:
                    first_audio_ms = now
                    print(f"    turn {turn_no}: FIRST AUDIO at {now:.0f} ms after end-of-speech")
                audio_bytes += len(msg.data) - 4
                n_audio_msgs += 1
            elif msg.type == 1:
                data = json.loads(msg.data)
                if "user" in data:
                    print(f"    turn {turn_no}: transcript at {(time.perf_counter()-t0_turn)*1000:.0f} ms -> {data['user']!r}")
            elif msg.type == 8:
                return

    reader_task = asyncio.create_task(reader())
    last_audio[0] = time.perf_counter()

    # 0. drain: let any leftover audio from the previous response finish
    while time.perf_counter() - last_audio[0] < 0.8:
        await asyncio.sleep(0.05)

    # 1. ~350 ms lead-in silence
    await paced_frames(ws, SILENCE * 11)

    # 2. speech, wall-clock paced
    sp = await paced_frames(ws, speech_pcm)

    # 3. t0 = end of speech; switch to silence
    t0_turn = time.perf_counter()

    # 4. ~5 s of silence, exit once the response has fully arrived
    for _ in range(160):
        await ws.send_bytes(SILENCE)
        await asyncio.sleep(0.032)
        if first_audio_ms is not None and audio_bytes > 60000:
            break

    await asyncio.sleep(1.5)
    reader_task.cancel()
    return first_audio_ms, audio_bytes, n_audio_msgs, sp * 1000


async def main():
    speech_pcm = await make_speech_pcm()
    dur = len(speech_pcm) / 32000
    print(f"utterance: {UTTERANCE!r} ({dur:.1f}s, {len(speech_pcm)} B)")

    session = aiohttp.ClientSession()
    ws = await session.ws_connect("ws://127.0.0.1:8001/ws", max_msg_size=0)
    print("connected to /ws")

    turns = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    last_audio = [time.perf_counter()]
    results = []
    for t in range(1, turns + 1):
        print(f"  --- turn {t} ---")
        fa, ab, nm, sp = await run_turn(ws, speech_pcm, t, last_audio)
        results.append(fa)
        print(f"    speech {sp:.0f} ms | audio {ab} B in {nm} msgs")
        await asyncio.sleep(1.0)

    good = [r for r in results if r]
    if good:
        print("\nE2E end-of-speech -> first audio: " + ", ".join(f"{r:.0f} ms" for r in good))
        print(f"median {sorted(good)[len(good)//2]:.0f} ms | min {min(good):.0f} ms")
    else:
        print("\nNO AUDIO RECEIVED on any turn")
    await ws.close()
    await session.close()

asyncio.run(main())
