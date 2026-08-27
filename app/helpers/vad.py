from ten_vad import TenVad
from numpy import frombuffer, int16


class VADSession:
    def __init__(self):
        self.vad = TenVad(
            hop_size=256,
            threshold=0.5
        )

        self.buffer = bytearray()

    def detect_speech(self, pcm_bytes):
        self.buffer.extend(pcm_bytes)

        results = []

        while len(self.buffer) >= 512:
            frame_bytes = self.buffer[:512]
            del self.buffer[:512]

            audio = frombuffer(
                frame_bytes,
                dtype=int16
            )

            result = self.vad.process(audio)

            results.append(result)

        return results