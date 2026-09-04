import wave
import io


class PcmToWav:

    @staticmethod
    def convert_pcm_to_wav(pcm_audio_array: bytearray) -> bytes:
        try:
            file = PcmToWav._create_temporary_file(pcm_audio_array)

            # with open("test_audio.wav", "wb") as f:
            #     f.write(file)

            return file

        except Exception as e:
            print(str(e))
            raise

    @staticmethod
    def _create_temporary_file(pcm_audio_array: bytearray) -> bytes:

        buffer = io.BytesIO()

        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)      # 16-bit PCM
            wav.setframerate(16000)
            wav.writeframes(pcm_audio_array)

        return buffer.getvalue()