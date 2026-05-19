from assist_runtime.tools.registry import ToolRegistry

from assist_runtime.tools.filesystem.read_file import ReadFileTool
from assist_runtime.tools.filesystem.list_dir import ListDirTool


def load_tools() -> ToolRegistry:
    registry = ToolRegistry()

    #filesysyem tools
    registry.register(ReadFileTool())
    registry.register(ListDirTool())

    return registry
