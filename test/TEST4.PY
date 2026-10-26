
import os
import time
import statistics

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

client = ElevenLabs(
    api_key="sk_17e5b0760efecee30441562ca7df693f468064c819a0b92b"
)

VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
MODEL_ID = "eleven_flash_v2_5"
TEXT = "Hello! This is a test of ElevenLabs text to speech latency."
RUNS = 5


def measure_latency():
    start = time.perf_counter()
    first_chunk_ms = None
    total_bytes = 0

    audio_stream = client.text_to_speech.stream(
        voice_id=VOICE_ID,
        text=TEXT,
        model_id=MODEL_ID,
        output_format="mp3_22050_32",
    )

    for chunk in audio_stream:
        if chunk:
            if first_chunk_ms is None:
                first_chunk_ms = (
                    time.perf_counter() - start
                ) * 1000

            total_bytes += len(chunk)

    total_ms = (time.perf_counter() - start) * 1000

    return first_chunk_ms, total_ms, total_bytes


def main():
    results = []

    for i in range(RUNS):
        try:
            first, total, size = measure_latency()
            results.append((first, total, size))

            print(
                f"Run {i + 1}: "
                f"First chunk: {first:.2f} ms | "
                f"Total: {total:.2f} ms | "
                f"Audio: {size / 1024:.2f} KB"
            )

        except Exception as exc:
            print(f"Run {i + 1} failed: {exc}")

    if results:
        print("\n--- SUMMARY ---")
        print(f"Successful runs: {len(results)}/{RUNS}")
        print(
            "Average first chunk: "
            f"{statistics.mean(r[0] for r in results):.2f} ms"
        )
        print(
            "Average total latency: "
            f"{statistics.mean(r[1] for r in results):.2f} ms"
        )
        print(
            "Fastest first chunk: "
            f"{min(r[0] for r in results):.2f} ms"
        )


if __name__ == "__main__":
    main()
