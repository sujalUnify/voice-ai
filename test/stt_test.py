import asyncio
import time
import os

from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

client = AsyncGroq(
    api_key=os.getenv("GROQ_API_KEY")
)

TTS_MODEL = "canopylabs/orpheus-v1-english"


async def main():

    text = "Hello, how are you doing today?"

    start = time.perf_counter()
    first_audio = True
    total_bytes = 0

    print("Starting Groq TTS request...")

    response = await client.audio.speech.create(
        model=TTS_MODEL,
        voice="autumn",
        input=text,
        response_format="wav",
    )

    async for chunk in response.iter_bytes():

        if not chunk:
            continue

        if first_audio:
            elapsed = (time.perf_counter() - start) * 1000
            print(f"FIRST AUDIO CHUNK: {elapsed:.1f} ms")
            first_audio = False

        total_bytes += len(chunk)

    total = (time.perf_counter() - start) * 1000

    print(f"\nTOTAL TIME: {total:.1f} ms")
    print(f"TOTAL AUDIO BYTES: {total_bytes}")


if __name__ == "__main__":
    asyncio.run(main())