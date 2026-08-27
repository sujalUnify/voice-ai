from fastapi import WebSocket,FastAPI,WebSocketDisconnect
import asyncio 
from app.helpers import VADSession

app = FastAPI()

@app.websocket("/ws") 
async def websocket_endpoint(websocket: WebSocket):  
    await websocket.accept()  
    chunks = []
    block_48k = []
    sample_count = 0
    try:
        while True: 
            data = await websocket.receive_bytes() 
            samples = np.frombuffer(data, dtype=np.float32)
            print(samples)

            chunks.append(samples)
            sample_count += len(samples)

            print("Total samples:", sample_count)

            if sample_count >= 512:
                block_48k = np.concatenate(chunks)
                print("Got approximately 1 second of 48k audio!")
                break
    except WebSocketDisconnect as e: 
        print(f"Client disconnected. Code: {e.code}")
    except Exception as e:
        print(f"Unexpected error: {e}") 
    print(len(block_48k))
    with open("received_audio.webm", "wb") as f:
        for chunk in chunks:
            f.write(chunk)
    print("File written")
