from pathlib import Path
from assist_runtime.tools.base import BaseTool


class WriteFileTool(BaseTool):
    name = "write_file"
    description = 'Writes content to a file at the specified path. Required tool_input: {"file_path": "<file_path>", "content": "<file_content>"}'
    
    def execute(self, input_data: dict) -> str:
        """
        Expects input_data to have the following structure:
        {
            "file_path": "path/to/file.txt",
            "content": "The content to write to the file."
        }
        """
        file_path = input_data.get("file_path")
        content = input_data.get("content")

        if not file_path or not content:
            raise ValueError("Both 'file_path' and 'content' are required in input_data.")

        # Ensure the directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        # Write content to the file
        with open(file_path, 'w', encoding="utf-8") as f:
            f.write(content)

        return f"Content successfully written to {file_path}"