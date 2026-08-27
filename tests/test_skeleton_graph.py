import pytest
from langchain_core.messages import HumanMessage

from oncall.graph.skeleton import build_skeleton_graph


@pytest.mark.anyio
async def test_skeleton_graph_echoes_input() -> None:
    graph = build_skeleton_graph()
    result = await graph.ainvoke({"messages": [HumanMessage(content="hello")]})
    assert result["messages"][-1].content == "Echo: hello"
