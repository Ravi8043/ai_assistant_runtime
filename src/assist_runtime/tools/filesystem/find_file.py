import os
import fnmatch
from pathlib import Path
from assist_runtime.tools.base import BaseTool

class FindFileTool(BaseTool):
    name = "find_file"
    description = 'Recursively searches for files matching a pattern. Required tool_input: {"pattern": "<glob_pattern>", "path": "<starting_dir>"}'

    def execute(self, input_data: dict) -> dict:
        path_str = input_data.get("path", ".")
        pattern = input_data.get("pattern")
        
        if not pattern:
            return {"success": False, "error": "Missing 'pattern' in tool_input"}

        start_path = Path(path_str).expanduser()
        if not start_path.exists() or not start_path.is_dir():
            return {"success": False, "error": f"Path is not a valid directory: {path_str}"}
        
        ignored_dirs = {".git", "node_modules", "__pycache__", "env", "venv"}
        matches = []
        
        for root, dirs, files in os.walk(start_path):
            if len(matches) >= 100:
                break
                
            # In-place modify dirs to skip ignored directories efficiently
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            
            for file_name in files:
                if fnmatch.fnmatch(file_name, pattern):
                    matches.append(os.path.join(root, file_name))
                    if len(matches) >= 100:
                        break
                        
        return {
            "success": True,
            "pattern": pattern,
            "matches": matches,
            "count": len(matches),
            "note": "Output capped at 100 matches" if len(matches) >= 100 else ""
        }
