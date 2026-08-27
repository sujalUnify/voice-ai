from fastapi import WebSocket,FastAPI,WebSocketDisconnect
import asyncio
from app.helpers import VADSession

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    vad = VADSession()
    try:
        while True:
            data = await websocket.receive_bytes()
            states = vad.detect_speech(data)
            print(states)
    except WebSocketDisconnect as e:
        print(f"Client disconnected. Code: {e.code}")
    except Exception as e:
        print(f"Unexpected error: {e}")
