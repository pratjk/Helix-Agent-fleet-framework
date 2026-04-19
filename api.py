import asyncio
import sys
import io
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
from dotenv import load_dotenv

from crewai import Crew, Process
from src.agents import create_architect, create_researcher, create_coder, create_debugger, create_qa, create_reviewer, create_scribe
from src.tasks import create_tasks

load_dotenv()

app = FastAPI(title="Project Helix API")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from the UI build directory
# We check if the dist directory exists, if not we skip it (for dev mode)
dist_path = os.path.join(os.getcwd(), "ui", "dist")
if os.path.exists(dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(dist_path, "index.html"))

class WebSocketStream(io.TextIOBase):
    def __init__(self, queue, loop):
        self.queue = queue
        self.loop = loop
        
    def write(self, text):
        if text:
            # Safely put message into the queue from the background thread
            self.loop.call_soon_threadsafe(self.queue.put_nowait, text)
        return len(text)

    def flush(self):
        pass

@app.websocket("/ws/mission")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        # Wait for the client to send the configuration (goal, model, api_keys)
        config_data = await websocket.receive_text()
        config = json.loads(config_data)
        
        goal = config.get("goal")
        model = config.get("model", "gpt-4o-mini")
        api_keys = config.get("api_keys", {})
        
        # Inject API keys into the environment dynamically
        for key_name, key_value in api_keys.items():
            if key_value:
                os.environ[key_name] = key_value
                
        os.environ["MODEL"] = model
        
        # Setup streaming queue
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        stream = WebSocketStream(queue, loop)
        
        # Background task to send messages from the queue to the websocket
        async def send_logs():
            while True:
                msg = await queue.get()
                if msg == "__DONE__":
                    break
                await websocket.send_text(json.dumps({"type": "log", "content": msg}))
                
        sender_task = asyncio.create_task(send_logs())
        
        # Define the mission execution function
        def run_mission():
            original_stdout = sys.stdout
            sys.stdout = stream
            result_str = ""
            try:
                print(f"🚀 Starting Mission with model: {model}\n")
                
                architect = create_architect(llm=model)
                researcher = create_researcher(llm=model)
                coder = create_coder(llm=model)
                debugger = create_debugger(llm=model)
                qa = create_qa(llm=model)
                reviewer = create_reviewer(llm=model)
                scribe = create_scribe(llm=model)
                
                tasks = create_tasks(goal, architect, researcher, coder, debugger, qa, reviewer, scribe)
                
                crew = Crew(
                    agents=[architect, researcher, coder, debugger, qa, reviewer, scribe],
                    tasks=tasks,
                    verbose=True,
                    process=Process.sequential,
                    memory=True
                )
                
                result = crew.kickoff()
                result_str = str(result)
            except Exception as e:
                print(f"\n❌ Error during execution: {str(e)}\n")
                result_str = f"Mission Failed: {str(e)}"
            finally:
                sys.stdout = original_stdout
                # Signal the sender task to finish
                loop.call_soon_threadsafe(queue.put_nowait, "__DONE__")
            return result_str
            
        # Run the crew AI logic in a separate thread so it doesn't block the async loop
        final_result = await asyncio.to_thread(run_mission)
        
        # Wait for the sender task to finish sending all remaining logs
        await sender_task
        
        # Send the final completion message
        await websocket.send_text(json.dumps({"type": "done", "content": final_result}))
        
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
