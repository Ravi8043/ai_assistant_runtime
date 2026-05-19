from pathlib import Path

from assist_runtime.tools.base import BaseTool


class ListDirTool(BaseTool):

    name = "list_dir"

    description = "Lists files in a directory"

    def execute(self, input_data: dict):

        path = Path(input_data["path"])

        return [str(p.name) for p in path.iterdir()]