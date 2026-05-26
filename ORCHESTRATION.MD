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
