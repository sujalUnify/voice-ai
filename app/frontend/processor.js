// Upstream batch: 512 samples @ 16 kHz = 32 ms per WebSocket message.
// The server's VAD consumes 512-byte (32 ms) frames anyway, so batching
// here cuts WS traffic and event-loop wakeups 4x with no added latency
// beyond the 32 ms the VAD would quantize to regardless.
const BATCH_SAMPLES = 512;

class AudioProcessor extends AudioWorkletProcessor {

    constructor() {
        super();
        this.batch = new Int16Array(BATCH_SAMPLES);
        this.filled = 0;
    }

    process(inputs) {

        const input = inputs[0];

        if (input.length > 0) {

            // Worklet gives Float32 (-1..1); server expects PCM16
            const floats = input[0];
            for (let i = 0; i < floats.length; i++) {
                const s = Math.max(-1, Math.min(1, floats[i]));
                this.batch[this.filled++] = s < 0 ? s * 0x8000 : s * 0x7FFF;

                if (this.filled === BATCH_SAMPLES) {
                    // copy: the buffer travels to the main thread
                    this.port.postMessage(this.batch.slice(0));
                    this.filled = 0;
                }
            }
        }
        return true;
    }
}

registerProcessor("audio-processor", AudioProcessor);
