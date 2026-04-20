import asyncio
import sys
import io
import os
import json
import datetime
import threading
import subprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

from crewai import Crew, Process
from src.agents import create_architect, create_researcher, create_coder, create_debugger, create_qa, create_reviewer, create_scribe
from src.tasks import create_tasks

load_dotenv()

app = FastAPI(title="Project Helix API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Paths ---
base_dir = os.path.dirname(os.path.abspath(__file__))
dist_path = os.path.join(base_dir, "ui", "dist")
history_path = os.path.join(base_dir, "history.json")
workspace_path = os.path.join(base_dir, "workspace")

# --- Serve Static UI ---
if os.path.exists(dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(dist_path, "index.html"))

# --- History API ---
@app.get("/api/history")
async def get_history():
    if os.path.exists(history_path):
        with open(history_path, "r") as f:
            return JSONResponse(json.load(f))
    return JSONResponse([])

# --- Open Workspace API ---
@app.post("/api/open-workspace")
async def open_workspace(body: dict = {}):
    project = body.get("project", "")
    path = os.path.join(workspace_path, project) if project else workspace_path
    os.makedirs(path, exist_ok=True)
    try:
        os.startfile(path)  # Windows
    except Exception:
        subprocess.Popen(["explorer", path])
    return {"status": "ok"}

def save_history(goal: str, model: str, project: str, result: str, status: str):
    """Append a mission record to history.json."""
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
    # Keep last 50 missions
    history = history[:50]
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

class WebSocketStream(io.TextIOBase):
    def __init__(self, queue, loop):
        self.queue = queue
        self.loop = loop

    def write(self, text):
        if text and text.strip():
            self.loop.call_soon_threadsafe(self.queue.put_nowait, text)
        return len(text)

    def flush(self):
        pass

AGENT_NAMES = [
    "Architect", "Researcher", "Principal Engineer",
    "Code Surgeon", "Guardian (QA)", "Gatekeeper (Reviewer)", "Scribe"
]

@app.websocket("/ws/mission")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    cancel_event = threading.Event()

    try:
        config_data = await websocket.receive_text()
        config = json.loads(config_data)

        goal = config.get("goal")
        model = config.get("model", "groq/llama-3.1-8b-instant")
        api_keys = config.get("api_keys", {})
        project = config.get("project", f"mission_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")

        # Inject API keys into environment
        for key_name, key_value in api_keys.items():
            if key_value and key_value.strip():
                os.environ[key_name] = key_value.strip()

        os.environ["MODEL"] = model

        # Setup project workspace
        project_workspace = os.path.join(workspace_path, project)
        os.makedirs(project_workspace, exist_ok=True)
        os.environ["PROJECT_WORKSPACE"] = project_workspace

        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        stream = WebSocketStream(queue, loop)

        async def send_logs():
            while True:
                msg = await queue.get()
                if msg == "__DONE__":
                    break
                if msg == "__CANCEL__":
                    await websocket.send_text(json.dumps({"type": "cancelled"}))
                    break
                await websocket.send_text(json.dumps({"type": "log", "content": msg}))

        sender_task = asyncio.create_task(send_logs())

        # Listen for cancel messages from client
        async def listen_for_cancel():
            try:
                while True:
                    msg = await websocket.receive_text()
                    data = json.loads(msg)
                    if data.get("type") == "cancel":
                        cancel_event.set()
                        loop.call_soon_threadsafe(queue.put_nowait, "__CANCEL__")
                        break
            except Exception:
                pass

        cancel_listener = asyncio.create_task(listen_for_cancel())

        def run_mission():
            original_stdout = sys.stdout
            sys.stdout = stream
            result_str = ""
            status = "success"
            try:
                print(f"🚀 Starting Mission: '{goal}'\n📦 Model: {model}\n📁 Project: {project}\n")

                # Emit progress for each agent
                def emit_progress(step, name):
                    msg = json.dumps({"type": "progress", "step": step, "total": 7, "agent": name})
                    loop.call_soon_threadsafe(queue.put_nowait, f"\n\n--- Step {step}/7: {name} is now active ---\n\n")

                if cancel_event.is_set():
                    return "Mission cancelled."

                emit_progress(1, "Architect")
                architect = create_architect(llm=model)

                emit_progress(2, "Researcher")
                researcher = create_researcher(llm=model)

                emit_progress(3, "Principal Engineer")
                coder = create_coder(llm=model)

                emit_progress(4, "Code Surgeon")
                debugger = create_debugger(llm=model)

                emit_progress(5, "Guardian (QA)")
                qa = create_qa(llm=model)

                emit_progress(6, "Gatekeeper (Reviewer)")
                reviewer = create_reviewer(llm=model)

                emit_progress(7, "Scribe")
                scribe = create_scribe(llm=model)

                if cancel_event.is_set():
                    return "Mission cancelled."

                tasks = create_tasks(goal, architect, researcher, coder, debugger, qa, reviewer, scribe)

                crew = Crew(
                    agents=[architect, researcher, coder, debugger, qa, reviewer, scribe],
                    tasks=tasks,
                    verbose=True,
                    process=Process.sequential,
                    memory=False
                )

                result = crew.kickoff()
                result_str = str(result)
                print(f"\n\n✅ Mission Complete!\n")

            except Exception as e:
                print(f"\n❌ Mission Failed: {str(e)}\n")
                result_str = f"Mission Failed: {str(e)}"
                status = "failed"
            finally:
                sys.stdout = original_stdout
                signal = "__CANCEL__" if cancel_event.is_set() else "__DONE__"
                loop.call_soon_threadsafe(queue.put_nowait, signal)
                save_history(goal, model, project, result_str, status)

            return result_str

        final_result = await asyncio.to_thread(run_mission)
        await sender_task
        cancel_listener.cancel()

        if not cancel_event.is_set():
            await websocket.send_text(json.dumps({
                "type": "done",
                "content": final_result,
                "project": project
            }))

    except WebSocketDisconnect:
        cancel_event.set()
        print("Client disconnected.")
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
