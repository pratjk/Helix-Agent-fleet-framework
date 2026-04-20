import subprocess
import ast
from typing import Tuple, List
from .plan_schema import ProjectPlan

class Artifact:
    def __init__(self, path: str, content: str, agent: str, step_id: str):
        self.path = path
        self.content = content
        self.agent = agent
        self.step_id = step_id

class QualityGate:
    name = "abstract_gate"
    async def check(self, artifacts: List[Artifact], workspace: str) -> Tuple[bool, str]:
        raise NotImplementedError

class SyntaxGate(QualityGate):
    name = "syntax_check"
    
    async def check(self, artifacts, workspace):
        for art in artifacts:
            if art.path.endswith('.py'):
                try:
                    ast.parse(art.content)
                except SyntaxError as e:
                    return False, f"Syntax error in {art.path}: {str(e)}"
        return True, "All Python files syntactically valid"

class SecurityGate(QualityGate):
    name = "security_scan"
    
    async def check(self, artifacts, workspace):
        issues = []
        for art in artifacts:
            if art.path.endswith('.py'):
                content = art.content
                dangerous = ['eval(', 'exec(', '__import__(', 'subprocess.call', 'os.system(']
                for d in dangerous:
                    if d in content:
                        issues.append(f"CRITICAL: {art.path} contains '{d}'")
        if issues:
            return False, "\n".join(issues)
        return True, "No critical security issues"

class GateKeeper:
    def __init__(self):
        self.gates = [SyntaxGate(), SecurityGate()]
    
    async def evaluate(self, artifacts, workspace) -> Tuple[bool, List[dict]]:
        results = []
        all_passed = True
        for gate in self.gates:
            passed, msg = await gate.check(artifacts, workspace)
            results.append({"gate": gate.name, "passed": passed, "message": msg})
            if not passed:
                all_passed = False
                break
        return all_passed, results