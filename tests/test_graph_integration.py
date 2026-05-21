"""
Integration smoke tests for the LangGraph agent orchestration graph.

Run with:
    py -3.11 -m pytest tests/test_graph_integration.py -v

Or directly:
    py -3.11 tests/test_graph_integration.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Fix Windows console encoding
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from assist_runtime.graph.state import GraphState, ExecutionPlan
from assist_runtime.graph.builder import build_graph
from assist_runtime.llm.client import UnifiedLLMClient
from assist_runtime.llm.parsing.structured import StructuredOutputParser
from assist_runtime.tools.bootstrap import load_tools
from assist_runtime.tools.executor import ToolExecutor


def _make_mock_llm() -> UnifiedLLMClient:
    """Create a mock LLM client that returns controlled responses."""
    mock = MagicMock(spec=UnifiedLLMClient)
    mock.generate = AsyncMock()
    return mock


def _make_initial_state(input_text: str) -> dict:
    """Create a minimal valid initial state for the graph."""
    from assist_runtime.runtime.context import ExecutionContext

    return {
        "input_text": input_text,
        "context": ExecutionContext(),
        "messages": [],
        "current_plan": None,
        "current_step_index": 0,
        "selected_tool": None,
        "tool_input": None,
        "tool_output": None,
        "current_iteration": 0,
        "max_iterations": 10,
        "is_complete": False,
        "next_node": None,
        "error": None,
        "final_response": None,
    }


async def test_conversational_flow():
    """
    TEST 1: Conversational input (no tools needed).
    Flow: START → planner → responder → END
    """
    print("\n=== TEST 1: Conversational flow (no tools) ===")

    mock_llm = _make_mock_llm()
    tool_registry = load_tools()
    tool_executor = ToolExecutor(registry=tool_registry)

    # Planner response: no tools needed
    planner_response = json.dumps({
        "requires_tools": False,
        "objective": "Greet the user",
        "steps": [],
    })

    # Responder response: final answer
    responder_response = "Hello! I'm Jarvis, your AI assistant. How can I help you today?"

    # Set up mock to return different responses on successive calls
    mock_llm.generate = AsyncMock(
        side_effect=[planner_response, responder_response]
    )

    graph = build_graph(
        llm_client=mock_llm,
        tool_executor=tool_executor,
        tool_registry=tool_registry,
    )

    state = _make_initial_state("Hello!")
    result = await graph.ainvoke(state, config={"configurable": {"thread_id": "test"}})

    assert result["is_complete"] is True, f"Expected is_complete=True, got {result['is_complete']}"
    assert result["final_response"] is not None, "Expected final_response to be set"
    assert result["error"] is None, f"Unexpected error: {result['error']}"

    print(f"  ✓ is_complete = {result['is_complete']}")
    print(f"  ✓ final_response = {result['final_response'][:80]}...")
    print(f"  ✓ error = {result['error']}")
    print(f"  ✓ messages count = {len(result['messages'])}")
    print("  PASSED ✓")


async def test_tool_execution_flow():
    """
    TEST 2: Tool execution flow (list_dir).
    Flow: START → planner → tool_router → tool_executor → reflection → responder → END
    """
    print("\n=== TEST 2: Tool execution flow (list_dir) ===")

    mock_llm = _make_mock_llm()
    tool_registry = load_tools()
    tool_executor = ToolExecutor(registry=tool_registry)

    # 1. Planner: create a plan with one step
    planner_response_1 = json.dumps({
        "requires_tools": True,
        "objective": "List files in the current directory",
        "steps": [
            {
                "step_id": 0,
                "task": "List files in the current directory",
                "tool_suggested": "list_dir",
                "tool_input": {"path": "."},
            }
        ],
    })

    # 2. Tool router: generate input for list_dir
    tool_input_response = json.dumps({"path": "."})

    # 3. Reflection: objective met
    reflection_response = json.dumps({
        "is_objective_met": True,
        "step_succeeded": True,
        "should_revise_plan": False,
        "reasoning": "Directory listing complete. All requested information gathered.",
    })

    # 4. Responder: final answer
    responder_response = "Here are the files in the current directory: ..."

    mock_llm.generate = AsyncMock(
        side_effect=[
            planner_response_1,
            reflection_response,
            responder_response,
        ]
    )

    graph = build_graph(
        llm_client=mock_llm,
        tool_executor=tool_executor,
        tool_registry=tool_registry,
    )

    state = _make_initial_state("List files in the current directory")
    result = await graph.ainvoke(state, config={"configurable": {"thread_id": "test"}})

    assert result["is_complete"] is True, f"Expected is_complete=True, got {result['is_complete']}"
    assert result["final_response"] is not None, "Expected final_response to be set"
    assert result["error"] is None, f"Unexpected error: {result['error']}"
    assert result["tool_output"] is not None, "Expected tool_output to contain directory listing"
    assert result["selected_tool"] == "list_dir", f"Expected selected_tool=list_dir, got {result['selected_tool']}"

    print(f"  ✓ is_complete = {result['is_complete']}")
    print(f"  ✓ selected_tool = {result['selected_tool']}")
    print(f"  ✓ tool_output type = {type(result['tool_output']).__name__}")
    print(f"  ✓ final_response = {result['final_response'][:80]}...")
    print(f"  ✓ error = {result['error']}")
    print(f"  ✓ current_iteration = {result['current_iteration']}")
    print("  PASSED ✓")


async def test_max_iterations_guard():
    """
    TEST 3: Max iterations guard triggers error_handler.
    Flow: planner → tool_router → tool_executor → reflection (loops until max)
          → error_handler → END
    """
    print("\n=== TEST 3: Max iterations guard ===")

    mock_llm = _make_mock_llm()
    tool_registry = load_tools()
    tool_executor_instance = ToolExecutor(registry=tool_registry)

    # Set max_iterations to 2 for quick test
    max_iter = 2

    # Call sequence: planner(1) → router(no llm) → reflection(1) → planner(2) → router(no llm) → reflection(2, triggers guard)
    responses = [
        # 1st planner call
        json.dumps({
            "requires_tools": True,
            "objective": "Do something",
            "steps": [
                {"step_id": 0, "task": "List files step 1", "tool_suggested": "list_dir", "tool_input": {"path": "."}},
                {"step_id": 1, "task": "List files step 2", "tool_suggested": "list_dir", "tool_input": {"path": "."}},
            ],
        }),
        # 1st reflection call — not done yet
        json.dumps({
            "is_objective_met": False,
            "step_succeeded": True,
            "should_revise_plan": False,
            "reasoning": "Step 1 done but need step 2",
        }),
        # 2nd planner call — continue
        json.dumps({"action": "continue"}),
        # 2nd reflection — this should trigger max_iterations guard
        # (current_iteration will be 2 at this point, matching max_iter=2)
        json.dumps({
            "is_objective_met": False,
            "step_succeeded": True,
            "should_revise_plan": False,
            "reasoning": "Still not done",
        }),
    ]

    mock_llm.generate = AsyncMock(side_effect=responses)

    graph = build_graph(
        llm_client=mock_llm,
        tool_executor=tool_executor_instance,
        tool_registry=tool_registry,
        max_iterations=max_iter,
    )

    state = _make_initial_state("Do something that takes many steps")
    state["max_iterations"] = max_iter

    result = await graph.ainvoke(state, config={"configurable": {"thread_id": "test"}})

    assert result["is_complete"] is True, f"Expected is_complete=True, got {result['is_complete']}"
    assert result["final_response"] is not None, "Expected final_response from error_handler"
    assert "maximum iteration limit" in (result["final_response"] or "").lower() or \
           "error" in (result["final_response"] or "").lower(), \
        f"Expected error message in final_response, got: {result['final_response']}"

    print(f"  ✓ is_complete = {result['is_complete']}")
    print(f"  ✓ final_response contains error: {('error' in result['final_response'].lower())}")
    print(f"  ✓ current_iteration = {result['current_iteration']}")
    print("  PASSED ✓")


async def main():
    """Run all integration tests."""
    print("=" * 60)
    print("LangGraph Agent Orchestration — Integration Tests")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_fn in [
        test_conversational_flow,
        test_tool_execution_flow,
        test_max_iterations_guard,
    ]:
        try:
            await test_fn()
            passed += 1
        except Exception as e:
            print(f"\n  FAILED ✗ — {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
