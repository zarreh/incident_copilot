"""Builds the compiled investigation graph."""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from zarreh_agentkit.guardrails.budget import Budget

from oncall.graph.nodes import build_agent_node, build_route_after_agent, build_summarize_node
from oncall.graph.state import InvestigationState
from oncall.retrieval.log_store import LogStore
from oncall.retrieval.vendor_kb import VendorKB
from oncall.schemas.models import IncidentReport
from oncall.settings import Settings, get_settings
from oncall.tools.registry import build_tools


def build_investigation_graph(
    settings: Settings | None = None,
    llm: Any | None = None,
    log_store: LogStore | None = None,
    vendor_kb: VendorKB | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> Any:
    """Compile the retrieve/plan/act/summarize investigation graph.

    `llm` is injectable so tests and evals can supply a fake chat model; the
    real graph builds a `ChatOpenAI` bound to `settings.reasoning_model`.
    """
    cfg = settings or get_settings()
    store = log_store or LogStore(settings=cfg)
    kb = vendor_kb or VendorKB(settings=cfg)
    tools = build_tools(store, kb, cfg)

    chat_model = llm
    if chat_model is None:
        from langchain_openai import ChatOpenAI
        from pydantic import SecretStr

        api_key = SecretStr(cfg.openai_api_key) if cfg.openai_api_key else None
        chat_model = ChatOpenAI(model=cfg.reasoning_model, api_key=api_key)

    llm_with_tools = chat_model.bind_tools(tools)
    structured_llm = chat_model.with_structured_output(IncidentReport)

    budget = Budget(max_tool_calls=cfg.max_tool_calls, max_wall_clock_seconds=cfg.max_run_seconds)

    builder = StateGraph(InvestigationState)
    builder.add_node("agent", build_agent_node(llm_with_tools))
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("summarize", build_summarize_node(structured_llm))

    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        build_route_after_agent(budget),
        {"tools": "tools", "summarize": "summarize"},
    )
    builder.add_edge("tools", "agent")
    builder.add_edge("summarize", END)

    return builder.compile(checkpointer=checkpointer)
