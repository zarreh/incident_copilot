"""LangGraph nodes for the investigation graph."""

from __future__ import annotations

import time
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from zarreh_agentkit.guardrails.budget import Budget, budget_breach_reason, count_tool_calls

from oncall.graph.state import InvestigationState
from oncall.guardrails.evidence_check import verify_report

SYSTEM_PROMPT = (
    "You are an on-call incident investigation copilot. Use the search_logs and "
    "lookup_known_issue tools to gather evidence before drawing conclusions. "
    "Never state a root cause that isn't directly supported by retrieved log "
    "lines or a known-issue match -- if the evidence is insufficient, say so "
    "plainly rather than guessing."
)

SUMMARY_PROMPT = (
    "Based on the investigation so far, draft a structured incident report. "
    "Cite the specific log lines or known issues that support your root cause. "
    "If the evidence does not support a confident root cause, set "
    "`insufficient_evidence` to true and explain what is missing rather than "
    "guessing."
)


def build_agent_node(llm_with_tools: Any) -> Any:
    """The investigator: one LLM turn, optionally emitting tool calls."""

    async def agent_node(state: InvestigationState) -> dict[str, Any]:
        messages = list(state.get("messages", []))
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    return agent_node


def build_route_after_agent(budget: Budget) -> Any:
    """Routes to `tools` while under budget and the agent requested a call,
    otherwise to `summarize` — including when the budget itself is breached."""

    def route_after_agent(state: InvestigationState) -> str:
        messages = state.get("messages", [])
        tool_call_count = count_tool_calls(messages)
        started_at = state.get("started_at", time.time())
        if budget_breach_reason(tool_call_count, started_at, budget):
            return "summarize"
        last = messages[-1] if messages else None
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return "summarize"

    return route_after_agent


def build_summarize_node(structured_llm: Any) -> Any:
    """Drafts the final `IncidentReport` from the accumulated message history."""

    async def summarize_node(state: InvestigationState) -> dict[str, Any]:
        messages = [*state.get("messages", []), SystemMessage(content=SUMMARY_PROMPT)]
        report = await structured_llm.ainvoke(messages)
        return {"report": report}

    return summarize_node


def build_verify_node(citation_coverage_floor: float) -> Any:
    """Post-flight, pure-code guardrail: downgrades any report whose citations
    don't resolve to actually-retrieved evidence, rather than publishing it."""

    def verify_node(state: InvestigationState) -> dict[str, Any]:
        report = state["report"]
        messages = state.get("messages", [])
        verified = verify_report(report, list(messages), citation_coverage_floor)
        return {"report": verified}

    return verify_node
