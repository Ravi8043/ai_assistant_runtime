from pathlib import Path

from assist_runtime.tools.base import BaseTool


class ListDirTool(BaseTool):

    name = "list_dir"

    description = 'List files and folders in a directory. Required tool_input: {"path": "<directory_path>"}'

    def execute(
        self,
        input_data: dict
    ):

        try:

            path_str = input_data.get(
                "path",
                "."
            )

            path = Path(path_str).expanduser()

            if not path.exists():

                return {
                    "success": False,
                    "error": f"Path does not exist: {path}"
                }

            if not path.is_dir():

                return {
                    "success": False,
                    "error": f"Path is not a directory: {path}"
                }

            items = []

            for item in path.iterdir():

                items.append({
                    "name": item.name,
                    "type": (
                        "directory"
                        if item.is_dir()
                        else "file"
                    )
                })

            return {
                "success": True,
                "path": str(path.resolve()),
                "content": items
            }

        except Exception as error:

            return {
                "success": False,
                "error": str(error)
            }
# list = ListDirTool()

# print(list.execute({"path": "./"}))