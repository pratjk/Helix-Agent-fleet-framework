import webview
import uvicorn
import threading
import os
import sys
import time
from api import app

def start_server():
    # Start the FastAPI server on port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

if __name__ == "__main__":
    # 1. Start the server in a background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # 2. Give the server a second to boot up
    time.sleep(1)

    # 3. Create the desktop window
    # We point it to the local FastAPI server which is now serving the UI
    window = webview.create_window(
        'Project Helix - Agent Fleet',
        'http://127.0.0.1:8000',
        width=1280,
        height=850,
        background_color='#0b0f19'
    )

    # 4. Start the GUI loop
    # On Windows, this will use the Edge Chromium engine
    webview.start()
