# 🧬 Project Helix: Agentic Development Fleet

Project Helix is a local-first, multi-agent orchestration framework designed to automate full-stack development missions. It utilizes **CrewAI** for agent orchestration, **LiteLLM** for model-agnostic routing, and **Docker** for secure, sandboxed code execution.

![Helix Dashboard](https://img.shields.io/badge/Fleet-7_Agents-blueviolet?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

## 🚀 Features

-   **7 Specialized Agents:** Architect, Researcher, Principal Engineer, Debugger, QA Engineer, Code Reviewer, and Scribe.
-   **Local-First & Private:** Integrated **ChromaDB** memory ensures project context stays on your machine.
-   **Model Agnostic:** Support for 100+ LLMs (OpenRouter, OpenAI, Anthropic, DeepSeek, Qwen, Ollama) via LiteLLM.
-   **Secure Sandboxing:** Every line of code is written and tested inside isolated Docker containers.
-   **Premium UI:** A high-performance web dashboard built with Vite and FastAPI, featuring real-time WebSocket log streaming.
-   **Desktop App:** Single-executable desktop wrapper for a native experience.

---

## 🛠️ Installation

### Prerequisites
-   **Python 3.11+**
-   **Node.js & npm** (for frontend development)
-   **Docker Desktop** (Required for the sandbox)

### Setup
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/helix.git
    cd helix
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    venv\Scripts\activate  # Windows
    source venv/bin/activate  # Mac/Linux
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment:**
    Copy `.env.example` to `.env` and add your API keys.

---

## 💻 Usage

### 🚀 The Recommended Way (Native Desktop App)
For the best experience, simply use the pre-built desktop application. No terminal commands required!

1.  Navigate to the `dist/` folder.
2.  Double-click **`Helix.exe`**.
3.  Click the **Settings** gear icon ⚙️ in the app to add your API keys.
4.  Enter your mission objective and launch the fleet!

---

### 🛠️ Developer Mode (Running from Source)
If you want to modify the code or contribute to the project:
1.  **Start the Backend:**
    ```bash
    python api.py
    ```
2.  **Start the Frontend:**
    ```bash
    cd ui
    npm run dev
    ```
3.  Open `http://localhost:5173` in your browser.

---

## 🤖 The Agent Fleet

1.  **Architect:** Designs the project structure and implementation plan.
2.  **Researcher:** Finds best practices and library documentation.
3.  **Principal Engineer:** Writes the core code and tests it in the sandbox.
4.  **Debugger (Code Surgeon):** Fixes execution errors surgically.
5.  **Guardian (QA):** Deliberately tries to break the app and reports failures.
6.  **Gatekeeper (Reviewer):** Final review for security and performance.
7.  **Scribe:** Generates final documentation and READMEs.

---

## 📜 License
This project is licensed under the MIT License.
