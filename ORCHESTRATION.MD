### the plan we are trying to build as of now is

       START
        ↓
       planner -----------------
         ↓                      |
    (tool_call?)                |
    ├── YES → tool_router       |
    │          ↓                |
    │      tool_executor        |
    │          ↓                |
    │      reflection           |
    │          ↓                |
    │   (need_more_tools?)      |
    │          ├── YES ----------
    │          └── NO
    │              |
    └── NO → responder
                ↓
                END


                input
session
messages
current_plan
selected_tool
tool_input
tool_output
final_response
next_node
is_complete
error