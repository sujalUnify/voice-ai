import asyncio
import sounddevice as sd

from app.services.tts import TextToSpeech


tts = TextToSpeech()

s = """
I am leaving a store when I notice the woman in front of me. There is something familiar in her
walk and then I know who she is—a friend from long ago.

I should say hello but I’m in a hurry. She’s probably in a hurry, too, and there’s no
need to bother. She hasn’t seen me yet and I can let it go.

We’re out the door now and suddenly I change my mind. “Linda,” I say, and she turns around.
"""


async def main():

    stream = sd.RawOutputStream(
        samplerate=24000,
        channels=1,
        dtype="int16",
        blocksize=0,
    )

    stream.start()

    leftover = b""

    try:
        async for chunk in tts.audio_generation(s):

            print("Received:", len(chunk), "bytes")

            # Add new bytes to anything left over
            data = leftover + chunk

            # PCM16 = 2 bytes per sample
            usable_length = len(data) - (len(data) % 2)

            if usable_length:
                stream.write(data[:usable_length])

            # Keep incomplete byte for next chunk
            leftover = data[usable_length:]

    finally:
        stream.stop()
        stream.close()


asyncio.run(main())