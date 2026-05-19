from pathlib import Path

from assist_runtime.tools.base import BaseTool



class ReadFileTool(BaseTool):

    name = "read_file"

    description = "Reads a file from disk"

    def execute(self, input_data: dict):
        
        path = Path(input_data['path'])

        if not path.exists():
            raise FileNotFoundError(path)

        return path.read_text()