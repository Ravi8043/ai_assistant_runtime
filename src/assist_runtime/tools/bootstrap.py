from assist_runtime.tools.filesystem.write_file import WriteFileTool
from assist_runtime.tools.registry import ToolRegistry

from assist_runtime.tools.filesystem.read_file import ReadFileTool
from assist_runtime.tools.filesystem.list_dir import ListDirTool
from assist_runtime.tools.filesystem.find_file import FindFileTool
from assist_runtime.tools.filesystem.grep_search import GrepSearchTool
from assist_runtime.tools.filesystem.run_command import RunCommandTool


def load_tools() -> ToolRegistry:
    registry = ToolRegistry()

    #filesysyem tools
    registry.register(ReadFileTool())
    registry.register(ListDirTool())
    registry.register(WriteFileTool())
    registry.register(FindFileTool())
    registry.register(GrepSearchTool())
    registry.register(RunCommandTool())

    return registry
