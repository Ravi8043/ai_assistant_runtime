#a centralized manager that stores, retrieves
#and lists _tools(private variable) that inherit from BaseTool


from typing import Dict

from assist_runtime.tools.base import BaseTool

class ToolRegistry:
    #constructor
    def __init__(self):

        #dict
        self._tools: Dict[str, BaseTool] = {}
    
    #Register _tools
    def register(self,
                tool: BaseTool
    ) -> None:

        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name} already exists")

        self._tools[tool.name] = tool
    
    #retrieve _tools
    def get_tool(self,
                name: str
    ) -> BaseTool | None:

        return self._tools.get(name)


    #unregister _tools
    def unregister(self, 
                    name: str
    ) -> None:

        if name not in self._tools:
            raise ValueError(f"Tool {name} does not exist")

        del self._tools[name]    
    
    #return all _tools
    def get_all_tools(self):

        return self._tools
    
    #clear all _tools
    def clear(self):

        self._tools.clear()