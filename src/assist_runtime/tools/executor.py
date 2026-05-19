from assist_runtime.tools.registry import ToolRegistry


class ToolExecutor:

    def __init__(
        self,
        registry: ToolRegistry
    ):
        self.registry = registry

    def execute(self, tool_name: str, input_data: dict):
        
        tool = self.registry.get_tool(tool_name)

        return tool.execute(input_data)
