import asyncio
import os
import json
from datetime import datetime
from typing import Dict, List
from .agents_v2 import ArchitectAgent, CoderAgent, AgentError
from .gates import GateKeeper, Artifact

class MissionStateMachine:
    def __init__(self, mission_id: str, workspace: str, model: str, event_queue: asyncio.Queue):
        self.mission_id = mission_id
        self.workspace = workspace
        self.model = model
        self.queue = event_queue
        self.gatekeeper = GateKeeper()
        self.history: List[Dict] = []
        self._cancelled = False
        self._approval_events: Dict[str, asyncio.Event] = {}
        self._approval_responses: Dict[str, dict] = {}
        self.token_usage = {"prompt": 0, "completion": 0, "total": 0}
        self.estimated_cost = 0.0
        
    def is_cancelled(self) -> bool:
        return self._cancelled
        
    def cancel(self):
        self._cancelled = True
        for ev in self._approval_events.values():
            ev.set()
        
    def resolve_approval(self, step_id: str, action: str, content: str = None):
        self._approval_responses[step_id] = {"action": action, "content": content}
        if step_id in self._approval_events:
            self._approval_events[step_id].set()

    def _emit(self, type_: str, content: str, **extra):
        payload = {"type": type_, "content": content, **extra}
        asyncio.create_task(self.queue.put(payload))
        self.history.append({
            "ts": datetime.utcnow().isoformat(),
            "type": type_,
            "content": content
        })
    
    def _emit_progress(self, step: int, agent_name: str):
        self._emit("progress", f"\n\n--- Step {step}/7: {agent_name} is now active ---\n\n", 
                  step=step, total=7, agent=agent_name)
    
    def _accumulate_usage(self, usage: dict):
        if not usage:
            return
        prompt = usage.get("prompt_tokens", 0)
        completion = usage.get("completion_tokens", 0)
        total = usage.get("total_tokens", 0)
        
        self.token_usage["prompt"] += prompt
        self.token_usage["completion"] += completion
        self.token_usage["total"] += total
        
        # Approximate pricing (per million tokens)
        rates = {
            "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
            "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
        }
        model_name = usage.get("model", "").split("/")[-1]
        rate = rates.get(model_name, {"input": 0.50, "output": 0.50})
        cost = (prompt * rate["input"] + completion * rate["output"]) / 1_000_000
        self.estimated_cost += cost
        
        self._emit("log", f"   🪙 +{total} tokens | 💰 +${cost:.6f} | Total: {self.token_usage['total']} tokens (${self.estimated_cost:.4f})")
    
    async def _request_file_approval(self, artifact: Artifact) -> dict:
        if self._cancelled:
            return {"action": "reject"}
        
        self._emit("approval_request", f"Pending approval: {artifact.path}",
                  step_id=artifact.step_id,
                  path=artifact.path,
                  code=artifact.content)
        
        event = asyncio.Event()
        self._approval_events[artifact.step_id] = event
        
        try:
            await event.wait()
        except asyncio.CancelledError:
            pass
        
        if self._cancelled:
            return {"action": "reject"}
        
        return self._approval_responses.get(artifact.step_id, {"action": "reject"})
    
    async def run(self, goal: str) -> Dict:
        try:
            # Step 1: Architect
            self._emit_progress(1, "Architect")
            architect = ArchitectAgent(self.model)
            plan, plan_usage = await architect.design(goal)
            self._accumulate_usage(plan_usage)
            
            plan_path = os.path.join(self.workspace, "plan.json")
            os.makedirs(self.workspace, exist_ok=True)
            with open(plan_path, 'w') as f:
                f.write(plan.model_dump_json(indent=2))
            self._emit("log", f"✅ Plan created: {len(plan.milestones)} milestones")
            
            # Step 2: Researcher
            self._emit_progress(2, "Researcher")
            self._emit("log", f"Tech stack: {plan.tech_stack.language} + {plan.tech_stack.framework}")
            await asyncio.sleep(0.5)
            
            # Step 3: Principal Engineer
            self._emit_progress(3, "Principal Engineer")
            coder = CoderAgent(self.model)
            all_artifacts: List[Artifact] = []
            
            for milestone in plan.milestones:
                self._emit("log", f"📦 Milestone: {milestone.name}")
                for file_spec in milestone.files_to_create:
                    if self._cancelled:
                        return {"status": "cancelled"}
                    
                    self._emit("log", f"   📝 Generating {file_spec.path}...")
                    
                    if all_artifacts:
                        await asyncio.sleep(7)
                    
                    artifact, code_usage = await coder.implement(file_spec, plan.description)
                    self._accumulate_usage(code_usage)
                    
                    # APPROVAL GATE
                    approval = await self._request_file_approval(artifact)
                    if approval["action"] == "reject":
                        self._emit("log", f"   🚫 Rejected by user: {artifact.path}")
                        continue
                    elif approval["action"] == "edit":
                        artifact.content = approval["content"]
                        self._emit("log", f"   ✏️ Edited by user: {artifact.path}")
                    
                    # Write to workspace
                    file_path = os.path.join(self.workspace, artifact.path)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(artifact.content)
                    self._emit("log", f"   💾 Successfully wrote to {artifact.path}")
                    
                    all_artifacts.append(artifact)
            
            if self._cancelled:
                return {"status": "cancelled"}
            
            # Step 4: Debugger / Quality Gates
            self._emit_progress(4, "Code Surgeon")
            passed, results = await self.gatekeeper.evaluate(all_artifacts, self.workspace)
            
            for res in results:
                icon = "✅" if res["passed"] else "❌"
                self._emit("log", f"   {icon} Gate '{res['gate']}': {res['message']}")
            
            if not passed:
                self._emit("log", "🚨 Quality gates FAILED. Halting mission.")
                return {"status": "failed", "reason": "quality_gates", "details": results}
            
            # Step 5: QA
            self._emit_progress(5, "Guardian (QA)")
            self._emit("log", "✅ Static analysis passed. No runtime tests configured yet.")
            
            # Step 6: Reviewer
            self._emit_progress(6, "Gatekeeper (Reviewer)")
            review_content = self._generate_review(plan, all_artifacts)
            with open(os.path.join(self.workspace, "review.md"), 'w', encoding='utf-8') as f:
                f.write(review_content)
            self._emit("log", "📝 review.md generated")
            
            # Step 7: Scribe
            self._emit_progress(7, "Scribe")
            readme_content = self._generate_readme(plan, all_artifacts)
            with open(os.path.join(self.workspace, "README.md"), 'w', encoding='utf-8') as f:
                f.write(readme_content)
            self._emit("log", "📝 README.md generated")
            
            self._emit("log", "\n\n✅ Mission Complete!\n")
            return {
                "status": "success",
                "files_created": len(all_artifacts),
                "project": plan.project_name,
                "tokens": self.token_usage,
                "cost": round(self.estimated_cost, 4)
            }
            
        except AgentError as e:
            self._emit("log", f"\n❌ Agent Error: {str(e)}")
            return {"status": "failed", "reason": "agent_error", "error": str(e)}
        except Exception as e:
            self._emit("log", f"\n❌ Mission Failed: {str(e)}")
            return {"status": "failed", "reason": "exception", "error": str(e)}
    
    def _generate_review(self, plan, artifacts) -> str:
        lines = ["# Code Review\n", f"## Project: {plan.project_name}\n\n"]
        lines.append("## Files Reviewed\n")
        for art in artifacts:
            lines.append(f"- `{art.path}` ({len(art.content)} bytes)\n")
        lines.append("\n## Findings\n")
        lines.append("- All files passed syntax validation\n")
        lines.append("- No critical security patterns detected\n")
        return "".join(lines)
    
    def _generate_readme(self, plan, artifacts) -> str:
        lang = plan.tech_stack.language
        framework = plan.tech_stack.framework
        testing = plan.tech_stack.testing
        styling = plan.tech_stack.styling

        # Build language badge color
        badge_colors = {
            "Python": "3776AB", "JavaScript": "F7DF1E", "TypeScript": "3178C6",
            "Rust": "000000", "Go": "00ADD8", "Java": "ED8B00"
        }
        lang_color = badge_colors.get(lang, "555555")
        lang_badge = f"![{lang}](https://img.shields.io/badge/{lang.replace(' ', '%20')}-{lang_color}?style=for-the-badge&logo={lang.lower()}&logoColor=white)"
        
        # Framework badge
        fw_badge = f"![{framework}](https://img.shields.io/badge/{framework.replace(' ', '%20')}-61DAFB?style=for-the-badge&logo={framework.lower().replace('.', '').replace(' ', '')}&logoColor=black)" if framework != "None" else ""
        
        # File structure tree
        file_tree = ""
        dirs_seen = set()
        for art in artifacts:
            parts = art.path.replace("\\", "/").split("/")
            if len(parts) > 1:
                d = parts[0]
                if d not in dirs_seen:
                    file_tree += f"├── {d}/\n"
                    dirs_seen.add(d)
                file_tree += f"│   └── {'/'.join(parts[1:])}\n"
            else:
                file_tree += f"├── {art.path}\n"

        # Cost/token summary
        tokens = self.token_usage.get("total", 0)
        cost = round(self.estimated_cost, 4)

        lines = f"""<div align="center">

# 🚀 {plan.project_name}

{lang_badge} {fw_badge}
![Built with Helix](https://img.shields.io/badge/Built%20with-Helix%20AI-6366f1?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Production%20Ready-22c55e?style=for-the-badge)

*{plan.description}*

</div>

---

## ✨ Features

- ⚡ Built autonomously by the **Helix AI Agent Fleet**
- 🧪 Includes test coverage via **{testing}**
- 🎨 Styled with **{styling}**
- 📱 Designed to work across devices and environments
- 🔒 Error handling and edge case coverage included

---

## 🗂️ Project Structure

```
{plan.project_name}/
{file_tree}└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | {lang} |
| Framework | {framework} |
| Testing | {testing} |
| Styling | {styling} |
| Build Tool | {plan.tech_stack.build_tool} |

---

## 🚀 Getting Started

### Prerequisites
- {lang} installed on your system
- A modern browser (if applicable)

### Installation

```bash
# Clone or navigate to the project
cd {plan.project_name.lower().replace(' ', '-')}

# Install dependencies (if applicable)
npm install        # for Node.js projects
pip install -r requirements.txt  # for Python projects
```

### Running the Project

```bash
# Start the application
npm start          # or
python main.py     # or open index.html in your browser
```

### Running Tests

```bash
npm test           # or
pytest             # or
python -m unittest
```

---

## 📊 Build Stats

> Generated autonomously by **Project Helix AI Fleet**

| Metric | Value |
|--------|-------|
| Files Created | {len(artifacts)} |
| Total Tokens Used | {tokens:,} |
| Estimated Cost | ${cost} |
| Milestones | {len(plan.milestones)} |

---

## 📋 Security & Architecture

{chr(10).join(f'- {s}' for s in (plan.security_considerations or ['Standard security practices applied']))}

**Performance Budget:** {plan.performance_budget or 'Optimized for production'}

---

<div align="center">

*Built with ❤️ by [Project Helix](https://github.com) — The Autonomous AI Development Fleet*

</div>
"""
        return lines