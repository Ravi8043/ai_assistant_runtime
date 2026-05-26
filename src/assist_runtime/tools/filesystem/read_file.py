from pathlib import Path

from assist_runtime.tools.base import BaseTool



class ReadFileTool(BaseTool):

    name = "read_file"

    description = 'Reads a file from disk. Required tool_input: {"path": "<file_path>"}'

    def execute(self, input_data: dict):
        
        path_str = input_data.get("path", ".") #default to current directory if no path provided

        path = Path(path_str).expanduser()

        if not path.exists():
            raise FileNotFoundError(path)

        return {
            "success": True,
            "content": path.read_text(encoding="utf-8")
            }


# read = ReadFileTool()

# print(read.execute({"path": "./list_dir.py"}))
