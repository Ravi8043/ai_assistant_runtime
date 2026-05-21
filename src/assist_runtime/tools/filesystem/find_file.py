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

        start_path = Path(path_str)
        if not start_path.exists() or not start_path.is_dir():
            return {"success": False, "error": f"Path is not a valid directory: {path_str}"}
        
        ignored_dirs = {".git", "node_modules", "__pycache__", "env", "venv"}
        matches = []
        
        # We'll use a manual walk to efficiently skip ignored directories
        def search_dir(current_dir: Path):
            if len(matches) > 100:  # Cap at 100 matches to prevent massive outputs
                return
            
            try:
                for item in current_dir.iterdir():
                    if item.is_dir():
                        if item.name not in ignored_dirs:
                            search_dir(item)
                    elif item.match(pattern):
                        matches.append(str(item.resolve()))
            except PermissionError:
                pass
                
        search_dir(start_path)
        
        return {
            "success": True,
            "pattern": pattern,
            "matches": matches,
            "count": len(matches),
            "note": "Output capped at 100 matches" if len(matches) > 100 else ""
        }
