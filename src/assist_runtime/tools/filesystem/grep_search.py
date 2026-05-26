import re
from pathlib import Path
from assist_runtime.tools.base import BaseTool

class GrepSearchTool(BaseTool):
    name = "grep_search"
    description = 'Searches for text or regex patterns inside files. Required tool_input: {"query": "<text_to_find>", "path": "<starting_dir>"}'

    def execute(self, input_data: dict) -> dict:
        path_str = input_data.get("path", ".")
        query = input_data.get("query")
        
        if not query:
            return {"success": False, "error": "Missing 'query' in tool_input"}

        start_path = Path(path_str).expanduser()
        if not start_path.exists():
            return {"success": False, "error": f"Path does not exist: {path_str}"}

        try:
            pattern = re.compile(query)
        except re.error as e:
            return {"success": False, "error": f"Invalid regex pattern: {e}"}

        ignored_dirs = {".git", "node_modules", "__pycache__", "env", "venv"}
        ignored_exts = {".exe", ".dll", ".so", ".jpg", ".png", ".pdf", ".zip", ".tar", ".gz", ".pyc"}
        
        matches = []
        
        def search_file(file_path: Path):
            if len(matches) > 100:
                return
            try:
                # Try to read as UTF-8, ignore files that fail decoding (likely binary)
                lines = file_path.read_text(encoding="utf-8", errors="strict").splitlines()
                for i, line in enumerate(lines, 1):
                    if pattern.search(line):
                        matches.append({"file": str(file_path), "line_number": i, "content": line.strip()})
                        if len(matches) > 100:
                            break
            except (UnicodeDecodeError, PermissionError):
                pass
                
        def search_dir(current_dir: Path):
            if len(matches) > 100:
                return
            try:
                for item in current_dir.iterdir():
                    if item.is_dir():
                        if item.name not in ignored_dirs:
                            search_dir(item)
                    else:
                        if item.suffix.lower() not in ignored_exts:
                            search_file(item)
            except PermissionError:
                pass
                
        if start_path.is_file():
            search_file(start_path)
        else:
            search_dir(start_path)
            
        return {
            "success": True,
            "query": query,
            "matches": matches,
            "count": len(matches),
            "note": "Output capped at 100 matches" if len(matches) > 100 else ""
        }
