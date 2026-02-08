import asyncio
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from server.websocket_manager import WebSocketManager
from server.agent.agent_loop import run_agent
from server.config import settings

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(title="TaskPilot")
manager = WebSocketManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)

@app.on_event("startup")
async def startup_event():
    """Verify configuration on startup."""
    if not settings.groq_api_key:
        print("WARNING: GROQ_API_KEY is not set. Task planning will fail.")
        print("  Create a .env file with GROQ_API_KEY=your_api_key")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    await manager.send_event("LOG", {"level": "info", "message": "Connected"})

    try:
        while True:
            message = await ws.receive_json()
            msg_type = message.get("type")
            if msg_type == "START_TASK":
                goal = message.get("goal", "")
                if goal:
                    asyncio.create_task(run_agent(goal, manager))
            elif msg_type == "CREDENTIALS_PROVIDED":
                data = message.get("data", {})
                if isinstance(data, dict):
                    manager.set_credentials(data)
            else:
                await manager.send_log("warn", f"Unknown message: {msg_type}")
    except WebSocketDisconnect:
        await manager.disconnect(ws)
