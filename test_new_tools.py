import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(r"c:\Users\racha\Desktop\assistant_runtime\src")))

from assist_runtime.tools.bootstrap import load_tools

def run_tests():
    registry = load_tools()
    
    # 1. Test find_file
    find_tool = registry.get_tool("find_file")
    res1 = find_tool.execute({"pattern": "builder.py", "path": "."})
    print("FIND_FILE:", res1)
    
    # 2. Test grep_search
    grep_tool = registry.get_tool("grep_search")
    res2 = grep_tool.execute({"query": "def create_planner_node", "path": "src"})
    print("GREP_SEARCH:", res2)
    
    # 3. Test run_command
    cmd_tool = registry.get_tool("run_command")
    res3 = cmd_tool.execute({"command": "echo Hello World", "cwd": "."})
    print("RUN_COMMAND:", res3)

if __name__ == "__main__":
    run_tests()
