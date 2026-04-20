import os
from crewai.tools import tool
from .sandbox import DockerSandbox

# Initialize sandbox once at module level
_workspace = os.getenv(
    "PROJECT_WORKSPACE",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace")
)
_sandbox = DockerSandbox(_workspace)

# --- Security Policy ---
BLOCKED_PATTERNS = [
    'rm -rf /', 'mkfs.', 'dd if=/dev/zero', '>:', 'curl', 'wget ',
    'nvidia-smi', 'shutdown', 'reboot', 'poweroff', 'mkfs.ext',
    'chmod 777 /', 'chmod -R 777 /'
]

def _check_security(command: str) -> tuple[bool, str]:
    for pattern in BLOCKED_PATTERNS:
        if pattern in command:
            return False, f"Security block: '{pattern}' is not allowed."
    return True, ""

@tool("Write File Tool")
def write_file_tool(filepath: str, content: str) -> str:
    """Writes content to a file at the given filepath inside the project workspace directory."""
    try:
        base = os.getenv(
            "PROJECT_WORKSPACE",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace")
        )
        full_path = os.path.join(base, filepath)
        abs_base = os.path.abspath(base)
        abs_target = os.path.abspath(full_path)
        
        # Prevent path traversal
        if not abs_target.startswith(abs_base):
            return "Error: Path traversal detected. Access denied."
            
        os.makedirs(os.path.dirname(abs_target), exist_ok=True)
        with open(abs_target, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

@tool("Read File Tool")
def read_file_tool(filepath: str) -> str:
    """Reads the content of a file from the project workspace directory."""
    try:
        base = os.getenv(
            "PROJECT_WORKSPACE",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace")
        )
        full_path = os.path.join(base, filepath)
        abs_base = os.path.abspath(base)
        abs_target = os.path.abspath(full_path)
        
        if not abs_target.startswith(abs_base):
            return "Error: Path traversal detected. Access denied."
            
        with open(abs_target, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool("Execute Command Tool")
def execute_command_tool(command: str) -> str:
    """Executes a shell command inside the Docker sandbox and returns the output."""
    safe, msg = _check_security(command)
    if not safe:
        return f"Error: {msg}"
    
    # Route through Docker instead of host subprocess
    return _sandbox.execute_command(command, timeout=30)