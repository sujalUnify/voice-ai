import asyncio
import aiohttp
import os
import time

from dotenv import load_dotenv

load_dotenv()


async def main():
    url = "https://openrouter.ai/api/v1/audio/speech"

    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "fish-audio/s2.1-pro-free:free",
        "input": "Hello, how are you doing today?",
        "response_format": "pcm",
    }

    start = time.perf_counter()
    first_audio = True
    total_bytes = 0
    chunks = 0

    print("Starting Fish Audio S2.1 Pro TTS...")

    async with aiohttp.ClientSession() as session:

        async with session.post(
            url,
            headers=headers,
            json=payload,
        ) as response:

            print("STATUS:", response.status)
            print("CONTENT TYPE:", response.headers.get("content-type"))

            if response.status != 200:
                print("ERROR:")
                print(await response.text())
                return

            print("SUCCESS")

            async for chunk in response.content.iter_chunked(4096):

                if not chunk:
                    continue

                chunks += 1
                total_bytes += len(chunk)

                if first_audio:
                    elapsed = (time.perf_counter() - start) * 1000
                    print(f"FIRST AUDIO: {elapsed:.1f} ms")
                    first_audio = False


    total = (time.perf_counter() - start) * 1000

    print("\n--- RESULTS ---")
    print(f"TOTAL TIME: {total:.1f} ms")
    print(f"TOTAL BYTES: {total_bytes}")
    print(f"TOTAL CHUNKS: {chunks}")


if __name__ == "__main__":
    asyncio.run(main())