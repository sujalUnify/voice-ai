import io
import wave


class PcmToWav:

    @staticmethod
    def convert_pcm_to_wav(pcm_audio_array: bytearray) -> bytes:
        """Wrap 16 kHz mono PCM16 bytes in a canonical WAV container."""
        try:
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)      # 16-bit PCM
                wav.setframerate(16000)
                wav.writeframes(pcm_audio_array)
            return buffer.getvalue()
        except Exception as e:
            print(str(e))
            raise
