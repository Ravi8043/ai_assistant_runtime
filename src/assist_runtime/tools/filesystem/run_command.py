import subprocess
from assist_runtime.tools.base import BaseTool

class RunCommandTool(BaseTool):
    name = "run_command"
    description = 'Executes a shell command on the host system. Required tool_input: {"command": "<shell_command>", "cwd": "<working_directory>"}'

    def execute(self, input_data: dict):
        command = input_data.get("command")
        cwd = input_data.get("cwd", ".")
        timeout = input_data.get("timeout", 60)
        
        if not command:
            return {"success": False, "error": "Missing 'command' in tool_input"}

        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Truncate outputs if they are too massive to prevent blowing up the LLM context
            stdout = result.stdout
            if len(stdout) > 5000:
                stdout = stdout[:5000] + "\n...[TRUNCATED]"
                
            stderr = result.stderr
            if len(stderr) > 5000:
                stderr = stderr[:5000] + "\n...[TRUNCATED]"

            return {
                "success": result.returncode == 0,
                "command": command,
                "cwd": cwd,
                "return_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {timeout} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution failed: {str(e)}"
            }
