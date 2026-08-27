from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from oncall.graph.builder import build_investigation_graph
from oncall.retrieval.log_store import LogStore
from oncall.retrieval.vendor_kb import VendorKB
from oncall.schemas.models import IncidentReport
from oncall.settings import Settings


class _FakeToolCallingModel:
    """Emits one `search_logs` tool call, then a plain closing message."""

    def __init__(self) -> None:
        self.calls = 0

    async def ainvoke(self, messages: list[Any]) -> AIMessage:
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_logs",
                        "args": {"service": "payment-service", "limit": 5},
                        "id": "call-1",
                    }
                ],
            )
        return AIMessage(content="Evidence gathered; drafting report.")


class _FakeStructuredModel:
    async def ainvoke(self, messages: list[Any]) -> IncidentReport:
        return IncidentReport(
            title="payment-service timeout cascade",
            severity="high",
            root_cause="payment-service upstream latency caused timeouts",
            evidence=[],
            recommended_actions=["add circuit breaker"],
            confidence=0.9,
        )


class _FakeChatModel:
    def __init__(self) -> None:
        self._tool_model = _FakeToolCallingModel()
        self._structured_model = _FakeStructuredModel()

    def bind_tools(self, tools: list[Any]) -> _FakeToolCallingModel:
        return self._tool_model

    def with_structured_output(self, schema: type[IncidentReport]) -> _FakeStructuredModel:
        return self._structured_model


@pytest.fixture
def seeded_settings(tmp_path: Path) -> Settings:
    settings = Settings(
        log_db_path=str(tmp_path / "logs.db"),
        vendor_kb_path=str(tmp_path / "kb.json"),
    )
    from data.generate_logs import build_artifacts

    build_artifacts(settings=settings)
    return settings


@pytest.mark.anyio
async def test_investigation_graph_gathers_evidence_and_summarizes(
    seeded_settings: Settings,
) -> None:
    log_store = LogStore(settings=seeded_settings)
    vendor_kb = VendorKB(settings=seeded_settings)
    graph = build_investigation_graph(
        settings=seeded_settings,
        llm=_FakeChatModel(),
        log_store=log_store,
        vendor_kb=vendor_kb,
    )

    result = await graph.ainvoke(
        {
            "question": "why did payments fail?",
            "messages": [HumanMessage(content="why did payments fail?")],
            "started_at": time.time(),
        }
    )

    report = result["report"]
    assert isinstance(report, IncidentReport)
    assert report.title
    assert not report.insufficient_evidence
    # one tool round-trip happened: ToolMessage was appended to history
    tool_messages = [m for m in result["messages"] if m.__class__.__name__ == "ToolMessage"]
    assert len(tool_messages) == 1


class _AlwaysCallingModel:
    """Never stops calling tools -- used to prove the budget guardrail ends the run."""

    async def ainvoke(self, messages: list[Any]) -> AIMessage:
        return AIMessage(
            content="",
            tool_calls=[
                {"name": "search_logs", "args": {"limit": 1}, "id": f"call-{time.time_ns()}"}
            ],
        )


class _AlwaysCallingChatModel:
    def __init__(self) -> None:
        self._tool_model = _AlwaysCallingModel()
        self._structured_model = _FakeStructuredModel()

    def bind_tools(self, tools: list[Any]) -> _AlwaysCallingModel:
        return self._tool_model

    def with_structured_output(self, schema: type[IncidentReport]) -> _FakeStructuredModel:
        return self._structured_model


@pytest.mark.anyio
async def test_investigation_graph_respects_tool_call_budget(seeded_settings: Settings) -> None:
    seeded_settings = seeded_settings.model_copy(update={"max_tool_calls": 2})
    log_store = LogStore(settings=seeded_settings)
    vendor_kb = VendorKB(settings=seeded_settings)
    graph = build_investigation_graph(
        settings=seeded_settings,
        llm=_AlwaysCallingChatModel(),
        log_store=log_store,
        vendor_kb=vendor_kb,
    )

    result = await graph.ainvoke(
        {
            "question": "why did payments fail?",
            "messages": [HumanMessage(content="why did payments fail?")],
            "started_at": time.time(),
        }
    )

    assert "report" in result
    tool_messages = [m for m in result["messages"] if m.__class__.__name__ == "ToolMessage"]
    assert len(tool_messages) <= 3
