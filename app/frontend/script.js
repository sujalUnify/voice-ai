const startBtn = document.getElementById("startBtn");
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
    };
    // 3. Updated WebSocket Listener
    socket.onmessage = async (event) => {
        //  Ignore raw microphone binary data packets bouncing back from the server
        if (event.data instanceof ArrayBuffer) {
            return;
        }

        try {
            const data = JSON.parse(event.data);

            // A. Handle User Speech Transcription
            if (data.user) {
                ai.textContent = "";
                user.textContent = data.user;
            }

            // B. Handle Streaming AI Response Text
            else if (data.ai) {
                ai.textContent += data.ai;
            }
            else if(data.audio){

            }
        } catch (error) {
            console.error("Error parsing WebSocket data:", error);
        }
    };


    socket.onclose = () => {
        console.log("WebSocket closed");
    };

    socket.onerror = (error) => {
        console.log("WebSocket error:", error);
    };
});
