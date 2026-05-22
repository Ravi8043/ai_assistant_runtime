from assist_runtime.tools.registry import ToolRegistry


class ToolExecutor:

    def __init__(
        self,
        registry: ToolRegistry
    ):
        self.registry = registry

    def execute(self, tool_name: str, input_data: dict) -> dict:
        
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return {
                "success" : False,
                "error": f"Tool not found: {tool_name}"
            }
        return tool.execute(input_data)
