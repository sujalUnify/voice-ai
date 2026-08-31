import wave
import io


class PcmToWav:

    @staticmethod
    def convert_pcm_to_wav(pcm_audio_array: bytearray) -> bytes:
        return PcmToWav._create_temporary_file(pcm_audio_array)

    @staticmethod
    def _create_temporary_file(pcm_audio_array: bytearray) -> bytes:

        buffer = io.BytesIO()

        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)      # 16-bit PCM
            wav.setframerate(16000)
            wav.writeframes(pcm_audio_array)

        return buffer.getvalue()