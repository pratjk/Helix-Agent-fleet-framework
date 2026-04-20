import docker
import os
import threading

class DockerSandbox:
    def __init__(self, workspace_dir: str, image: str = "python:3.11-slim"):
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.image = image
        self.client = docker.from_env()
        self._ensure_workspace()
        self._pull_image()

    def _ensure_workspace(self):
        os.makedirs(self.workspace_dir, exist_ok=True)

    def _pull_image(self):
        try:
            self.client.images.get(self.image)
        except docker.errors.ImageNotFound:
            print(f"Pulling Docker image {self.image}...")
            self.client.images.pull(self.image)

    def execute_command(self, command: str, timeout: int = 30) -> str:
        """Executes a command inside the Docker sandbox with a hard timeout."""
        print(f"\n[Sandbox] Executing: {command}")
        container = None
        try:
            container = self.client.containers.run(
                self.image,
                command=["sh", "-c", command],
                volumes={self.workspace_dir: {'bind': '/workspace', 'mode': 'rw'}},
                working_dir='/workspace',
                detach=True,
                remove=False,
                network_mode='none',
                mem_limit='512m',
                cpu_quota=100000
            )
            
            # Hard timeout using threading timer
            kill_timer = threading.Timer(timeout, lambda: container.kill(signal=9))
            kill_timer.start()
            
            result = container.wait()
            kill_timer.cancel()
            
            logs = container.logs().decode('utf-8', errors='replace')
            container.remove(force=True)
            
            output = logs[:4000]  # Prevent memory bloat from huge logs
            print(f"[Sandbox] Output:\n{output}")
            return output if output else "Command executed successfully (no output)."
            
        except docker.errors.ContainerError as e:
            return f"Error executing command:\n{e.stderr.decode('utf-8', errors='replace')}"
        except Exception as e:
            if container:
                try:
                    container.kill(signal=9)
                    container.remove(force=True)
                except Exception:
                    pass
            return f"Sandbox Error: {str(e)}"

    def write_file(self, file_path: str, content: str) -> str:
        """Writes a file to the workspace directory."""
        full_path = os.path.join(self.workspace_dir, file_path)
        if not os.path.abspath(full_path).startswith(self.workspace_dir):
            return "Error: Cannot write outside of the workspace directory."
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[Sandbox] Wrote file: {file_path}")
            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

    def read_file(self, file_path: str) -> str:
        """Reads a file from the workspace directory."""
        full_path = os.path.join(self.workspace_dir, file_path)
        if not os.path.abspath(full_path).startswith(self.workspace_dir):
            return "Error: Cannot read outside of the workspace directory."
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: File {file_path} not found."
        except Exception as e:
            return f"Error reading file: {str(e)}"