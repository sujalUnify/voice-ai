const startBtn = document.getElementById("startBtn");
let playContext, nextStartTime = 0;
startBtn.addEventListener("click", async () => {
    const user = document.getElementById("user");
    const ai = document.getElementById("ai");
    // 1. Create WebSocket
    const socket = new WebSocket("ws://127.0.0.1:8000/ws");
    socket.binaryType = "arraybuffer";
    socket.onopen = async () => {

        console.log("WebSocket connected");

        // 2. Get microphone
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1
            }
        });

        // 3. Create AudioContext
        const audioContext = new AudioContext({
            sampleRate: 16000
        });

        console.log("Actual sample rate:", audioContext.sampleRate);

        // 4. Load AudioWorklet
        await audioContext.audioWorklet.addModule("processor.js");

        // 5. Microphone → AudioNode
        const source =
            audioContext.createMediaStreamSource(stream);

        // 6. Create processor
        const processor =
            new AudioWorkletNode(audioContext, "audio-processor");

        // 7. Receive raw samples
        processor.port.onmessage = (event) => {

            const samples = event.data;

            // console.log("Samples:", samples);
            // console.log("Number:", samples.length);

            if (socket.readyState === WebSocket.OPEN) {

                // Float32Array → its underlying bytes
                socket.send(samples.buffer);
            }
            else{
                console.log("Disconnected.")
            }
        };

        // 8. Microphone → AudioWorklet
        source.connect(processor);

        // Playback context: TTS pcm is 24 kHz 16-bit mono
        playContext = new AudioContext({ sampleRate: 24000 });
        nextStartTime = 0;
    };

    // base64 → Float32Array (Int16 PCM → float).
    // A 16-bit sample can be split across two chunks, so carry odd leftover bytes over.
    let carry = new Uint8Array(0);
    const base64ToFloat32 = (b64) => {
        const bin = atob(b64);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);

        const merged = new Uint8Array(carry.length + bytes.length);
        merged.set(carry);
        merged.set(bytes, carry.length);

        const sampleCount = (merged.length - (merged.length % 2)) / 2;
        const int16 = new Int16Array(merged.buffer, 0, sampleCount);
        const float32 = new Float32Array(sampleCount);
        for (let i = 0; i < sampleCount; i++) float32[i] = int16[i] / 32768;

        carry = merged.slice(sampleCount * 2);
        return float32;
    };

    const activeSources = new Set();

    const playChunk = (float32, message) => {

        // CANCEL AI AUDIO
        if (message != null) {
            console.log(" STOPPING AI AUDIO");

            for (const source of activeSources) {
                try {
                    source.stop();
                } catch (e) {
                    console.log("Source already stopped");
                }
            }

            activeSources.clear();

            nextStartTime = playContext.currentTime;

            return;
        }

        // NORMAL AUDIO PLAYBACK
        const buffer = playContext.createBuffer(
            1,
            float32.length,
            playContext.sampleRate
        );

        buffer.copyToChannel(float32, 0);

        const source = playContext.createBufferSource();

        source.buffer = buffer;
        source.connect(playContext.destination);

        if (nextStartTime < playContext.currentTime) {
            nextStartTime = playContext.currentTime;
        }

        source.start(nextStartTime);

        nextStartTime += buffer.duration;

        // IMPORTANT
        activeSources.add(source);

        source.onended = () => {
            activeSources.delete(source);
        };
    };
    // 3. Updated WebSocket Listener
    let currentResponseId = 0;

    socket.onmessage = async (event) => {
        if (event.data instanceof ArrayBuffer) return;
        try {
            const data = JSON.parse(event.data);
            // User interrupted AI
            if (data.message) {
                currentResponseId++;
                playChunk([], "cancel");

                ai.textContent = "";
                user.textContent = "";
                return;
            }
            // Ignore old response chunks
            if (data.response_id !== undefined && data.response_id !== currentResponseId){
                return;
            }

            if (data.user) {
                ai.textContent = "";
                user.textContent = data.user;
            }
            else if (data.ai) {
                ai.textContent += data.ai;
            }
            else if (data.audio) {
                playChunk(
                    base64ToFloat32(data.audio),
                    null
                );
            }
        } catch (error) {
            console.error("WebSocket message error:", error);
        }
    };


    socket.onclose = () => {
        console.log("WebSocket closed");
    };

    socket.onerror = (error) => {
        console.log("WebSocket error:", error);
    };
});
