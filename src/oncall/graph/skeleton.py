"""Phase 0 walking-skeleton graph: a minimal LangGraph that echoes a greeting.

This graph exists only to prove the build toolchain, streaming, and
persistence wiring end-to-end. It is replaced by the real investigation
graph in Phase 3.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph


async def _echo_node(state: MessagesState) -> dict[str, Any]:
    last = state["messages"][-1]
    content = last.content if isinstance(last.content, str) else str(last.content)
    return {"messages": [HumanMessage(content=f"Echo: {content}")]}


def build_skeleton_graph(
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> Any:
    """Compile a trivial two-node graph for toolchain validation."""
    builder = StateGraph(MessagesState)
    builder.add_node("echo", _echo_node)
    builder.add_edge(START, "echo")
    builder.add_edge("echo", END)
    return builder.compile(checkpointer=checkpointer)
