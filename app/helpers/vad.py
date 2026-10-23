import logging
import math

from numpy import frombuffer, int16
from ten_vad import TenVad

from app.config import SILENCE_DURATION_MS, VAD_ONSET_FRAMES, VAD_THRESHOLD

logger = logging.getLogger(__name__)

# ten-vad hop: 256 samples @ 16 kHz = 16 ms per 512-byte frame
FRAME_MS = 16


class VADSession:
    def __init__(self):
        self.vad = TenVad(
            hop_size=256,
            threshold=VAD_THRESHOLD
        )
        self.buffer = bytearray()
        self.speaking = False
        self._speech_run = 0   # consecutive speech frames
        self._silence_run = 0  # consecutive silence frames
        self._silent_frames_needed = math.ceil(SILENCE_DURATION_MS / FRAME_MS)

    @property
    def silence_run(self) -> int:
        """Consecutive silence frames while speaking (trailing-silence counter)."""
        return self._silence_run

    def detect_speech(self, pcm_bytes):
        """Feed PCM16 mono @16kHz bytes; returns True while speaking, False when not."""
        try:
            self.buffer.extend(pcm_bytes)
            while len(self.buffer) >= 512:
                frame_bytes = bytes(self.buffer[:512])
                del self.buffer[:512]

                audio = frombuffer(frame_bytes, dtype=int16)
                hit = bool(self.vad.process(audio)[1])

                if hit:
                    self._speech_run += 1
                    self._silence_run = 0
                    # ~VAD_ONSET_FRAMES speech frames of continuous audio → speech
                    if self._speech_run >= VAD_ONSET_FRAMES:
                        self.speaking = True
                else:
                    self._speech_run = 0
                    self._silence_run += 1
                    if self._silence_run >= self._silent_frames_needed:
                        self.speaking = False
            return self.speaking
        except Exception as e:
            logger.exception("VAD detection failed : %s", str(e))
            return self.speaking
