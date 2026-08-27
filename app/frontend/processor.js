class AudioProcessor extends AudioWorkletProcessor {

    process(inputs) {

        const input = inputs[0];

        if (input.length > 0) {

            // Worklet gives Float32 (-1..1); server expects PCM16
            const floats = input[0];
            const pcm16 = new Int16Array(floats.length);
            for (let i = 0; i < floats.length; i++) {
                const s = Math.max(-1, Math.min(1, floats[i]));
                pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }

            this.port.postMessage(pcm16);
        }
        return true;
    }
}

registerProcessor("audio-processor", AudioProcessor);
