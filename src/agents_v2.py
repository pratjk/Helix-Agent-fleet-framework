import os
import json
import re
import asyncio
from typing import Optional, List, Tuple
from litellm import completion
from litellm.exceptions import RateLimitError
from .plan_schema import ProjectPlan, FileSpec
from .gates import Artifact

class AgentError(Exception):
    pass

def _get_available_models(preferred: str) -> List[str]:
    models = []
    if preferred:
        models.append(preferred)
    if os.getenv("GROQ_API_KEY") and not any("groq" in m for m in models):
        models.append("groq/llama-3.3-70b-versatile")
        models.append("groq/llama-3.1-8b-instant")
    if os.getenv("OPENROUTER_API_KEY") and not any("openrouter" in m for m in models):
        models.append("openrouter/qwen/qwen-2.5-coder-32b-instruct")
    if os.getenv("OPENAI_API_KEY") and not any("openai" in m for m in models):
        models.append("openai/gpt-4o-mini")
    if os.getenv("ANTHROPIC_API_KEY") and not any("anthropic" in m for m in models):
        models.append("anthropic/claude-3-5-sonnet-20241022")
    seen = set()
    unique = []
    for m in models:
        if m not in seen:
            seen.add(m)
            unique.append(m)
    return unique

class ArchitectAgent:
    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv("MODEL", "groq/llama-3.3-70b-versatile")
    
    def _extract_usage(self, response, model: str) -> dict:
        if not response:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "model": model}
        usage = getattr(response, 'usage', None)
        if usage:
            return {
                "prompt_tokens": getattr(usage, 'prompt_tokens', 0) or 0,
                "completion_tokens": getattr(usage, 'completion_tokens', 0) or 0,
                "total_tokens": getattr(usage, 'total_tokens', 0) or 0,
                "model": model
            }
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "model": model}
    
    async def design(self, goal: str) -> Tuple[ProjectPlan, dict]:
        system_msg = """You are a principal software architect. 
Given a user goal, design a complete project plan.
You MUST respond with valid JSON matching the requested schema exactly. 
Do not include markdown formatting, explanations, or code blocks. Only raw JSON.
Ensure all string values use proper JSON escaping (no unescaped newlines inside strings)."""
        
        user_msg = f"""Design a production system for: {goal}

Respond with JSON matching this exact structure:
{{
  "project_name": "string",
  "description": "string",
  "tech_stack": {{
    "language": "string",
    "framework": "string", 
    "testing": "string",
    "styling": "string",
    "build_tool": "string"
  }},
  "milestones": [
    {{
      "name": "string",
      "description": "string",
      "files_to_create": [
        {{
          "path": "string",
          "purpose": "string",
          "dependencies": [],
          "test_strategy": "unit"
        }}
      ],
      "test_requirements": [],
      "approval_required": false
    }}
  ],
  "architecture_diagram": "mermaid syntax string",
  "security_considerations": [],
  "performance_budget": "string"
}}

Rules:
- All file paths must be relative (no leading /)
- No .. allowed in paths
- Keep files small and focused (max 200 lines per file)
- Use only double quotes for JSON strings
- test_strategy must be exactly one of: unit, integration, e2e, visual"""

        models_to_try = _get_available_models(self.model)
        if not models_to_try:
            raise AgentError("No API keys found. Set GROQ_API_KEY, OPENROUTER_API_KEY, OPENAI_API_KEY.")
        
        all_errors = []
        
        for model in models_to_try:
            provider = model.split("/")[0] if "/" in model else model
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ]
            
            for attempt in range(2):
                try:
                    response = completion(
                        model=model,
                        messages=messages,
                        temperature=0.2,
                        max_tokens=4000
                    )
                    content = response.choices[0].message.content
                    usage = self._extract_usage(response, model)
                    plan = self._parse_json(content)
                    
                    errors = plan.validate_plan()
                    if errors:
                        correction_msg = f"Your JSON had these validation errors: {errors}. Please fix them and return corrected JSON only."
                        messages.append({"role": "assistant", "content": content})
                        messages.append({"role": "user", "content": correction_msg})
                        all_errors.append(f"{provider} attempt {attempt+1}: Validation - {errors}")
                        continue
                    
                    return plan, usage
                    
                except json.JSONDecodeError as e:
                    correction_msg = f"Your response was not valid JSON. Error: {str(e)}. Please return ONLY valid JSON, no markdown, no explanations."
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": correction_msg})
                    all_errors.append(f"{provider} attempt {attempt+1}: JSON parse error")
                    continue
                    
                except Exception as e:
                    err_str = str(e)
                    if "auth" in err_str.lower() or "key" in err_str.lower() or "401" in err_str:
                        all_errors.append(f"{provider}: AUTH FAILED")
                    else:
                        all_errors.append(f"{provider}: {err_str[:120]}")
                    break
                
        error_report = "\n".join([f"  • {e}" for e in all_errors])
        raise AgentError(f"Failed to generate valid plan. Tried {len(models_to_try)} model(s):\n{error_report}")
    
    def _parse_json(self, text: str) -> ProjectPlan:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        return ProjectPlan.model_validate_json(text)


class CoderAgent:
    def __init__(self, model: Optional[str] = None):
        self.model = model or os.getenv("MODEL", "groq/llama-3.3-70b-versatile")
        self.models_to_try = _get_available_models(self.model)
    
    def _extract_usage(self, response, model: str) -> dict:
        if not response:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "model": model}
        usage = getattr(response, 'usage', None)
        if usage:
            return {
                "prompt_tokens": getattr(usage, 'prompt_tokens', 0) or 0,
                "completion_tokens": getattr(usage, 'completion_tokens', 0) or 0,
                "total_tokens": getattr(usage, 'total_tokens', 0) or 0,
                "model": model
            }
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "model": model}
    
    async def implement(self, file_spec: FileSpec, plan_context: str) -> Tuple[Artifact, dict]:
        deps = "\n".join([f"- {d}" for d in file_spec.dependencies]) if file_spec.dependencies else "None"
        
        json_prompt = f"""You are a 10x developer. Write clean, production-grade, fully implemented code.

Project Context: {plan_context}
File to create: {file_spec.path}
Purpose: {file_spec.purpose}
Dependencies: {deps}

Requirements:
- Write COMPLETE, runnable code
- Include error handling
- Follow best practices for {file_spec.path.split('.')[-1]} files
- Respond with JSON in this exact format:
{{"code": "the complete source code as a string", "notes": "brief implementation notes"}}

No markdown blocks. Raw JSON only."""
        md_prompt = f"""You are a 10x developer. Write clean, production-grade, fully implemented code.

Project Context: {plan_context}
File to create: {file_spec.path}
Purpose: {file_spec.purpose}
Dependencies: {deps}

Requirements:
- Write COMPLETE, runnable code
- Include error handling
- Follow best practices

Respond with ONLY a markdown code block like this:
```{file_spec.path.split('.')[-1]}
// your code here
```"""
        
        all_errors = []
        
        for model in self.models_to_try:
            provider = model.split("/")[0] if "/" in model else model
            
            messages_json = [
                {"role": "system", "content": "You write production code. Output valid JSON only."},
                {"role": "user", "content": json_prompt}
            ]
            
            for attempt in range(2):
                try:
                    response = completion(
                        model=model,
                        messages=messages_json,
                        temperature=0.1,
                        max_tokens=4000
                    )
                    content = response.choices[0].message.content
                    usage = self._extract_usage(response, model)
                    data = json.loads(self._extract_json(content))
                    return Artifact(
                        path=file_spec.path,
                        content=data["code"],
                        agent="CoderAgent",
                        step_id=file_spec.path
                    ), usage
                except (json.JSONDecodeError, KeyError) as e:
                    if attempt == 0:
                        correction = f"Invalid JSON: {str(e)}. Return ONLY valid JSON with 'code' and 'notes' fields."
                        messages_json.append({"role": "assistant", "content": content})
                        messages_json.append({"role": "user", "content": correction})
                        all_errors.append(f"{provider} JSON attempt 1 failed")
                        continue
                    else:
                        all_errors.append(f"{provider} JSON attempt 2 failed")
                        break
                except RateLimitError:
                    all_errors.append(f"{provider}: Rate limited. Waiting 20s...")
                    await asyncio.sleep(20)
                    continue
                except Exception as e:
                    err_str = str(e)
                    if "auth" in err_str.lower() or "key" in err_str.lower() or "401" in err_str:
                        all_errors.append(f"{provider}: AUTH FAILED")
                    elif "rate" in err_str.lower() or "429" in err_str:
                        all_errors.append(f"{provider}: Rate limited")
                        await asyncio.sleep(20)
                        continue
                    else:
                        all_errors.append(f"{provider}: {err_str[:100]}")
                    break
            
            try:
                await asyncio.sleep(2)
                response = completion(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You write production code. Output markdown code blocks only."},
                        {"role": "user", "content": md_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=4000
                )
                content = response.choices[0].message.content
                usage = self._extract_usage(response, model)
                code = self._extract_markdown_code(content, file_spec.path)
                if code:
                    return Artifact(
                        path=file_spec.path,
                        content=code,
                        agent="CoderAgent",
                        step_id=file_spec.path
                    ), usage
                all_errors.append(f"{provider}: Markdown fallback extracted empty code")
            except RateLimitError:
                all_errors.append(f"{provider}: Rate limited on markdown fallback")
                await asyncio.sleep(20)
            except Exception as e:
                all_errors.append(f"{provider}: Markdown fallback failed - {str(e)[:80]}")
        
        error_report = "\n".join([f"  • {e}" for e in all_errors])
        raise AgentError(f"Failed to generate code for {file_spec.path}. Tried {len(self.models_to_try)} model(s):\n{error_report}")

    def _extract_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = text[text.find("\n")+1:]
            if text.endswith("```"):
                text = text[:-3].strip()
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        return text

    def _extract_markdown_code(self, text: str, filepath: str) -> str:
        pattern = r'```(?:\w+)?\n(.*?)```'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()