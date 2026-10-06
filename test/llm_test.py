import asyncio
import time
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
load_dotenv()
# We use Groq instead of OpenRouter for the LLM because latency is critical
# in our real-time voice pipeline.
# OpenRouter + Gemini 2.5 Flash Lite showed ~1.1–1.5s first-token latency.
# Groq + GPT-OSS 20B showed ~380–630ms first-token latency in our tests.
# This significantly reduces the delay before TTS can start generating audio.
# The goal is to keep the overall voice response latency around 1–1.2s.
# This benchmark verifies the LLM latency independently before integrating it.
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="openai/gpt-oss-20b",
    streaming=True,
)
async def main():

    messages = [
        (
            "system",
            "You are a helpful voice assistant. Keep your answer concise."
        ),
        (
            "user",
            "Hello, how are you doing today?"
        ),
    ]
    start = time.perf_counter()
    first_token = True
    full_response = ""
    print("Starting request...")
    async for chunk in llm.astream(messages):

        content = chunk.content

        if not content:
            continue

        if first_token:
            elapsed = (time.perf_counter() - start) * 1000
            print(f"FIRST NON-EMPTY TOKEN: {elapsed:.1f} ms")
            first_token = False

        print(repr(content))
        full_response += content
    total = (time.perf_counter() - start) * 1000
    print("\nFULL RESPONSE:")
    print(full_response)
    print(f"\nTOTAL TIME: {total:.1f} ms")
if __name__ == "__main__":
    asyncio.run(main())