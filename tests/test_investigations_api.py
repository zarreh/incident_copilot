from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from data.generate_logs import build_artifacts
from oncall.api.deps import get_investigation_graph, get_run_store
from oncall.api.main import app
from oncall.graph.builder import build_investigation_graph
from oncall.retrieval.log_store import LogStore
from oncall.retrieval.vendor_kb import VendorKB
from oncall.schemas.models import IncidentReport
from oncall.settings import Settings
from oncall.store.run_store import RunStore


class _FakeToolCallingModel:
    def __init__(self) -> None:
        self.calls = 0

    async def ainvoke(self, messages: list[Any]) -> Any:
        from langchain_core.messages import AIMessage

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
        return AIMessage(content="done")


class _FakeStructuredModel:
    async def ainvoke(self, messages: list[Any]) -> IncidentReport:
        from langchain_core.messages import ToolMessage

        trace_id = None
        for message in messages:
            if isinstance(message, ToolMessage) and isinstance(message.content, str):
                try:
                    payload = json.loads(message.content)
                except (json.JSONDecodeError, TypeError):
                    continue
                if isinstance(payload, list):
                    for item in payload:
                        if isinstance(item, dict) and item.get("trace_id"):
                            trace_id = item["trace_id"]
        evidence = (
            [{"source": "log", "reference": trace_id, "detail": "payment timeout"}]
            if trace_id
            else []
        )
        return IncidentReport(
            title="payment-service timeout cascade",
            severity="high",
            root_cause="payment-service upstream latency caused timeouts",
            evidence=evidence,  # type: ignore[arg-type]
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
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        log_db_path=str(tmp_path / "logs.db"),
        vendor_kb_path=str(tmp_path / "kb.json"),
    )
    build_artifacts(settings=settings)
    log_store = LogStore(settings=settings)
    vendor_kb = VendorKB(settings=settings)
    fake_graph = build_investigation_graph(
        settings=settings, llm=_FakeChatModel(), log_store=log_store, vendor_kb=vendor_kb
    )
    fake_run_store = RunStore(tmp_path / "runs.db")

    app.dependency_overrides[get_investigation_graph] = lambda: fake_graph
    app.dependency_overrides[get_run_store] = lambda: fake_run_store
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _wait_for_completion(client: TestClient, run_id: str) -> dict[str, Any]:
    for _ in range(20):
        response = client.get(f"/investigations/{run_id}")
        body: dict[str, Any] = response.json()
        if body["status"] != "running":
            return body
        time.sleep(0.05)
    raise AssertionError("investigation did not complete in time")


def test_create_and_fetch_investigation(client: TestClient) -> None:
    create_response = client.post("/investigations", json={"question": "why did payments fail?"})
    assert create_response.status_code == 202
    run_id = create_response.json()["id"]

    body = _wait_for_completion(client, run_id)
    assert body["status"] == "completed"
    assert body["report"]["title"]
    assert body["report"]["insufficient_evidence"] is False


def test_investigation_events_replays_every_node(client: TestClient) -> None:
    create_response = client.post("/investigations", json={"question": "why did payments fail?"})
    run_id = create_response.json()["id"]
    _wait_for_completion(client, run_id)

    with client.stream("GET", f"/investigations/{run_id}/events") as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert '"node": "agent"' in body
    assert '"node": "verify"' in body
    assert '"__end__"' in body


def test_get_unknown_investigation_returns_404(client: TestClient) -> None:
    response = client.get("/investigations/does-not-exist")
    assert response.status_code == 404


def test_create_investigation_rejects_oversized_body(client: TestClient) -> None:
    huge_question = "A" * 100_000
    response = client.post("/investigations", json={"question": huge_question})
    assert response.status_code == 413
