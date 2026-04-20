import os
import subprocess
from crewai.tools import tool

@tool("Write File Tool")
def write_file_tool(filepath: str, content: str) -> str:
    """Writes content to a file at the given filepath inside the project workspace directory."""
    try:
        # Use PROJECT_WORKSPACE env var if set by api.py, else default to workspace/
        base = os.getenv("PROJECT_WORKSPACE", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace"))
        full_path = os.path.join(base, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {filepath}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

@tool("Read File Tool")
def read_file_tool(filepath: str) -> str:
    """Reads the content of a file from the project workspace directory."""
    try:
        base = os.getenv("PROJECT_WORKSPACE", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace"))
        full_path = os.path.join(base, filepath)
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool("Execute Command Tool")
def execute_command_tool(command: str) -> str:
    """Executes a shell command inside the project workspace directory and returns the output. 
    IMPORTANT: Do NOT run blocking commands like 'http.server' or interactive shells. 
    Commands will timeout after 30 seconds.
    """
    try:
        base = os.getenv("PROJECT_WORKSPACE", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace"))
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=30, cwd=base
        )
        output = result.stdout + result.stderr
        return output[:3000] if output else "Command executed with no output."
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds. If this was a server, it is running in background (but we cannot see output)."
    except Exception as e:
        return f"Error executing command: {str(e)}"

# Tavily search tool (only loaded if API key is available)
def get_tavily_tool():
    """Returns TavilySearchTool if API key is available, else None."""
    if os.getenv("TAVILY_API_KEY"):
        try:
            from crewai_tools import TavilySearchTool
            return TavilySearchTool()
        except ImportError:
            pass
    return None
