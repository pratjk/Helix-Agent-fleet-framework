from crewai.tools import tool
from .sandbox import DockerSandbox
import os

WORKSPACE_DIR = os.path.join(os.getcwd(), "workspace")
sandbox = DockerSandbox(WORKSPACE_DIR)

@tool("Execute Command in Sandbox")
def execute_command_tool(command: str) -> str:
    """
    Executes a shell command inside the secure Docker sandbox. 
    Use this to run scripts, tests, or install dependencies.
    The working directory is the project workspace.
    """
    return sandbox.execute_command(command)

@tool("Write File to Workspace")
def write_file_tool(file_path: str, content: str) -> str:
    """
    Writes content to a file in the project workspace.
    Provide the relative file_path (e.g., 'main.py' or 'src/utils.py') and the content.
    """
    return sandbox.write_file(file_path, content)

@tool("Read File from Workspace")
def read_file_tool(file_path: str) -> str:
    """
    Reads the content of a file from the project workspace.
    Provide the relative file_path.
    """
    return sandbox.read_file(file_path)
