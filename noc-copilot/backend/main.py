import os
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.ingest import router as ingest_router
from backend.context import router as context_router
from backend.chat import router as chat_router
from backend.websocket import manager

app = FastAPI(title="AI NOC Copilot API")

# Enable CORS for local testing/development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(ingest_router, prefix="/api")
app.include_router(context_router, prefix="/api")
app.include_router(chat_router, prefix="/api")

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Listen to prevent connection timeouts, ignore incoming data (broadcast only)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket connection exception: {e}")
        manager.disconnect(websocket)

# Endpoint to fetch recent history logs (so UI charts do not start blank)
@app.get("/api/history")
async def get_history():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_file = os.path.join(base_dir, "data", "logs.json")
    if os.path.exists(logs_file):
        try:
            with open(logs_file, 'r') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        except Exception as e:
            print(f"Error reading history file: {e}")
    return []

# Serve Frontend static assets from the root path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_root = os.path.join(base_dir, "frontend")
frontend_dist = os.path.join(frontend_root, "dist")

# Prefer serving production build output from `frontend/dist` if present,
# otherwise fall back to serving the frontend folder (useful during development).
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
elif os.path.exists(frontend_root):
    print(f"WARNING: Serving raw frontend sources from {frontend_root}. Consider running `npm run build` to generate a production bundle.")
    app.mount("/", StaticFiles(directory=frontend_root, html=True), name="frontend")
else:
    print(f"WARNING: Frontend directory not found at: {frontend_root}. Frontend will not be served.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
