const startBtn = document.getElementById("startBtn");
let playContext, nextStartTime = 0;
let currentResponseId = null;     // response id we are currently playing
let carry = new Uint8Array(0);    // leftover odd byte between audio messages
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
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
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

        // convert int16 pcm samples into float32
    const pcm16ToFloat32 = (int16) => {
    const float32 = new Float32Array(int16.length);

    for (let i = 0; i < int16.length; i++) {
        float32[i] = int16[i] / 32768;
    }

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

    socket.onmessage = async (event) => {
        try {
            try{
                if(event.data instanceof ArrayBuffer){
                    const fullBuffer = event.data;  // This is the raw ArrayBuffer

                    // unpack the 4-Byte Integer header 
                    const view = new DataView(fullBuffer); 

                    // getUint32(byteOffset, littleEndian)
                    // We use 0 for the offset (start at the beginning)
                    // We use false for littleEndian because Python's '!I' is Big-Endian
                    const incoming_response_id = view.getUint32(0,false); 

                    if(incoming_response_id != currentResponseId){
                        return 
                    }
                   // 1. Merge the header-stripped payload with any leftover odd
                    // byte from the previous message: a 16-bit sample can be
                    // split across two WebSocket messages, so its first byte
                    // must be carried over instead of being dropped.
                    const body = new Uint8Array(fullBuffer, 4);
                    const merged = new Uint8Array(carry.length + body.length);
                    merged.set(carry);
                    merged.set(body, carry.length);

                    // 2. Only whole samples (even byte count) can be decoded;
                    // the odd byte, if any, is kept for the next message.
                    const usable = merged.length - (merged.length % 2);

                    if (usable > 0) {
                        const pcm16Samples = new Int16Array(merged.buffer, 0, usable / 2);
                        playChunk(pcm16ToFloat32(pcm16Samples));
                    }

                    carry = merged.slice(usable);

                    return
                }
            } catch(error){
                console.log("Error in procesing raw binary audio. Here is details"+error)
            }
            // process rest as it is
            const data = JSON.parse(event.data);
            // console.log(data);
            // User interrupted AI
            if (data.message) {
                console.log("Stopped messaged arrived.")
                playChunk([], "stop");
                currentResponseId = null;       // in-flight stragglers now fail the id check
                carry = new Uint8Array(0);      // reset byte-alignment carry too
                ai.textContent = "";
                user.textContent = "";
                return;
            }
            if (data.user !== undefined) {      // new turn: adopt the server's id
                currentResponseId = data.response_id;
                ai.textContent = "";
                user.textContent = data.user;
                return;
            }
            if (data.response_id !== currentResponseId) return;  // stale chunk

             if(data.ai !== undefined){
                ai.textContent += data.ai;
            }
        } catch (error) {
            console.error("WebSocket message error:"+ error);
        }
    };


    socket.onclose = () => {
        console.log("WebSocket closed");
    };

    socket.onerror = (error) => {
        console.log("WebSocket error:", error);
    };
});
