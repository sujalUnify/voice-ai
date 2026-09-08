from ten_vad import TenVad
from numpy import frombuffer, int16
from app.config import SILENCE_DURATION_MS
import logging

logger = logging.getLogger(__name__)
# ten-vad
class VADSession:
    def __init__(self):
        self.vad = TenVad(
            hop_size=256,
            threshold=0.65
        )
        self.buffer = bytearray()
        self.speaking = False
        self._speech_run = 0   # consecutive speech frames
        self._silence_run = 0  # consecutive silence frames 
        self._silent_duration = SILENCE_DURATION_MS/16

    def detect_speech(self, pcm_bytes):
        """Feed PCM16 mono @16kHz bytes; returns [True] while speaking, [False] when not."""
        try:
            self.buffer.extend(pcm_bytes)
            while len(self.buffer) >= 512:
                frame_bytes = bytes(self.buffer[:512])
                del self.buffer[:512]

                audio = frombuffer(frame_bytes, dtype=int16)
                hit = bool(self.vad.process(audio)[1])

                if hit: 
                    self._speech_run+=1 
                    self._silence_run = 0 
                    # Taking around 7 speech_run around ~102ms if continuous then yes its speech 
                    if self._speech_run >= 7: 
                        self.speaking = True 
                else: 
                    self._speech_run = 0 
                    self._silence_run+=1 
                    if self._silence_run >= self._silent_duration:
                        self.speaking = False
            return self.speaking
        except Exception as e: 
            logger.exception("VAD detection failed : %s",str(e)) 
            return self.speaking

