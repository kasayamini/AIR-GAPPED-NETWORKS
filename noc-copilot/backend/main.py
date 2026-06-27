import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.ingest import router as ingest_router
from backend.context import router as context_router
from backend.chat import router as chat_router
from backend.websocket import manager

app = FastAPI(title="AI NOC Copilot API")

# =========================
# CORS CONFIG (IMPORTANT FIX)
# =========================
FRONTEND_URL = os.getenv("FRONTEND_URL", "*")
allow_origins = ["*"] if FRONTEND_URL == "*" else [FRONTEND_URL]
allow_credentials = False if FRONTEND_URL == "*" else True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# ROUTES
# =========================
app.include_router(ingest_router, prefix="/api")
app.include_router(context_router, prefix="/api")
app.include_router(chat_router, prefix="/api")

# =========================
# HEALTH CHECK (FOR RENDER)
# =========================
@app.get("/health")
def health():
    return {"status": "ok"}

# =========================
# CHAT HISTORY
# =========================
@app.get("/api/history")
async def get_history():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_file = os.path.join(base_dir, "data", "logs.json")

    if os.path.exists(logs_file):
        try:
            with open(logs_file, "r") as f:
                data = f.read().strip()
                if data:
                    return json.loads(data)
        except Exception as e:
            print("History read error:", e)

    return []

# =========================
# WEBSOCKET
# =========================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# =========================
# LOCAL DEV ONLY
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)