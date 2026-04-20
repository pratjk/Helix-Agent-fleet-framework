import asyncio
import os
import json
import datetime
import subprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

from src.mission_control import MissionStateMachine

load_dotenv()

app = FastAPI(title="Project Helix API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_dir = os.path.dirname(os.path.abspath(__file__))
dist_path = os.path.join(base_dir, "ui", "dist")
history_path = os.path.join(base_dir, "history.json")
workspace_path = os.path.join(base_dir, "workspace")

if os.path.exists(dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(dist_path, "index.html"))

@app.get("/api/history")
async def get_history():
    if os.path.exists(history_path):
        with open(history_path, "r") as f:
            return JSONResponse(json.load(f))
    return JSONResponse([])

@app.post("/api/open-workspace")
async def open_workspace(body: dict = {}):
    project = body.get("project", "")
    path = os.path.join(workspace_path, project) if project else workspace_path
    os.makedirs(path, exist_ok=True)
    try:
        os.startfile(path)
    except Exception:
        subprocess.Popen(["explorer", path])
    return {"status": "ok"}

def save_history(goal: str, model: str, project: str, result: str, status: str):
    history = []
    if os.path.exists(history_path):
        try:
            with open(history_path, "r") as f:
                history = json.load(f)
        except Exception:
            history = []
    history.insert(0, {
        "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
        "timestamp": datetime.datetime.now().isoformat(),
        "goal": goal,
        "model": model,
        "project": project,
        "status": status,
        "result": result[:500] if result else ""
    })
    history = history[:50]
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

@app.websocket("/ws/mission")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    machine = None
    
    try:
        config_data = await websocket.receive_text()
        config = json.loads(config_data)

        goal = config.get("goal")
        model = config.get("model", "groq/llama-3.3-70b-versatile")
        api_keys = config.get("api_keys", {})
        project = config.get("project", f"mission_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")

        for key_name, key_value in api_keys.items():
            if key_value and key_value.strip():
                os.environ[key_name] = key_value.strip()

        os.environ["MODEL"] = model

        project_workspace = os.path.join(workspace_path, project)
        os.makedirs(project_workspace, exist_ok=True)
        os.environ["PROJECT_WORKSPACE"] = project_workspace

        queue = asyncio.Queue()
        machine = MissionStateMachine(project, project_workspace, model, queue)
        
        async def send_events():
            while True:
                event = await queue.get()
                try:
                    await websocket.send_text(json.dumps(event))
                except Exception:
                    break
                if event.get("type") in ("done", "error", "cancelled"):
                    break
        
        async def listen_client():
            try:
                while True:
                    msg = await websocket.receive_text()
                    data = json.loads(msg)
                    if data.get("type") == "cancel":
                        machine.cancel()
                    elif data.get("type") == "approval_response":
                        machine.resolve_approval(
                            data.get("step_id"),
                            data.get("action"),
                            data.get("content")
                        )
            except WebSocketDisconnect:
                pass
            except Exception:
                pass
        
        sender = asyncio.create_task(send_events())
        listener = asyncio.create_task(listen_client())
        
        result = await machine.run(goal)
        
        if machine.is_cancelled():
            await queue.put({"type": "cancelled"})
        else:
            await queue.put({
                "type": "done",
                "content": json.dumps(result),
                "project": project,
                "tokens": result.get("tokens", {}),
                "cost": result.get("cost", 0)
            })
        
        await sender
        listener.cancel()
        
        status = "success" if (isinstance(result, dict) and result.get("status") == "success") else "failed"
        save_history(goal, model, project, json.dumps(result), status)

    except WebSocketDisconnect:
        if machine:
            machine.cancel()
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
        except Exception:
            pass
    finally:
        if machine:
            machine.cancel()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)