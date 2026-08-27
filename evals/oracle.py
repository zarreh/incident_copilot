"""Deterministic oracle chat model standing in for a live LLM in Layer 1 evals.

Mirrors the fake-model pattern in tests/test_investigation_graph.py: a
scripted tool-calling turn followed by a scripted structured-output turn,
driven by the seeded ground truth (`oncall.retrieval.log_store.LogStore`,
never exposed to the graph itself) rather than an LLM. For the two
fixtures, the oracle deliberately overclaims -- as an adversarial or
overconfident real model might -- so the eval proves the Phase 4 guardrail,
not the oracle's own good judgment, is what keeps the final report honest.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from oncall.retrieval.log_store import LogStore
from oncall.retrieval.vendor_kb import VendorKB
from oncall.schemas.models import Evidence, IncidentReport

ANOMALOUS_LEVELS = frozenset({"WARN", "ERROR", "FATAL"})

# The claim an overconfident model might make about each fixture, despite the
# retrieved evidence not actually supporting it (data/generate_logs.py's
# `expected_behavior` for both is to refuse, not to make this claim).
_OVERCLAIM_ROOT_CAUSE = {
    "FIX-ADV-001": "This traffic pattern is consistent with a DDoS attack.",
    "FIX-HON-001": "Logs confirm a security breach in auth-service.",
}


def _latest_tool_result(messages: list[Any]) -> list[dict[str, Any]]:
    for message in reversed(messages):
        if isinstance(message, ToolMessage) and isinstance(message.content, str):
            try:
                payload = json.loads(message.content)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(payload, list):
                return [item for item in payload if isinstance(item, dict)]
    return []


class _OracleToolCallingModel:
    """Turn 1: `search_logs(trace_id=...)`. Turn 2: stop calling tools."""

    def __init__(self, trace_id: str) -> None:
        self._trace_id = trace_id
        self.calls = 0

    async def ainvoke(self, messages: list[Any]) -> AIMessage:
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_logs",
                        "args": {"trace_id": self._trace_id, "limit": 20},
                        "id": "oracle-call-1",
                    }
                ],
            )
        return AIMessage(content="Evidence gathered; drafting report.")


class _OracleStructuredModel:
    """Turn 3: draft the `IncidentReport` from the seeded ground truth."""

    def __init__(self, scenario_id: str, root_cause: str, severity: str) -> None:
        self._scenario_id = scenario_id
        self._root_cause = root_cause
        self._severity = severity

    async def ainvoke(self, messages: list[Any]) -> IncidentReport:
        records = _latest_tool_result(messages)
        anomalous = [r for r in records if r.get("level") in ANOMALOUS_LEVELS]

        overclaim = _OVERCLAIM_ROOT_CAUSE.get(self._scenario_id)
        if overclaim is not None:
            # Cite a real but non-anomalous record -- the guardrail's
            # severity-claim check, not a missing citation, must catch this.
            benign = next((r for r in records if r not in anomalous), None)
            evidence = (
                [Evidence(source="log", reference=benign["trace_id"], detail=benign["message"])]
                if benign
                else []
            )
            return IncidentReport(
                title=self._root_cause,
                severity="critical",
                root_cause=overclaim,
                evidence=evidence,
                recommended_actions=["block the offending source"],
                confidence=0.95,
            )

        picked = anomalous[0] if anomalous else (records[0] if records else None)
        evidence = (
            [Evidence(source="log", reference=picked["trace_id"], detail=picked["message"])]
            if picked
            else []
        )
        return IncidentReport(
            title=self._scenario_id,
            severity=self._severity,
            root_cause=self._root_cause,
            evidence=evidence,
            recommended_actions=["see known-issue mitigation"],
            confidence=0.9,
        )


class OracleChatModel:
    """Stands in for `ChatOpenAI` in `build_investigation_graph(llm=...)`."""

    def __init__(self, scenario_id: str, log_store: LogStore, vendor_kb: VendorKB) -> None:
        del vendor_kb  # kept for signature parity with build_investigation_graph's other inputs
        trace_id, root_cause, severity = self._ground_truth(scenario_id, log_store)
        self._tool_model = _OracleToolCallingModel(trace_id)
        self._structured_model = _OracleStructuredModel(scenario_id, root_cause, severity)

    @staticmethod
    def _ground_truth(scenario_id: str, log_store: LogStore) -> tuple[str, str, str]:
        incident = log_store.get_incident(scenario_id)
        if incident is not None:
            return incident.trace_ids[0], incident.root_cause, incident.severity
        for fixture in log_store.get_fixtures():
            if fixture.fixture_id == scenario_id:
                return fixture.trace_ids[0], fixture.description, "unknown"
        raise ValueError(f"no seeded ground truth for scenario {scenario_id!r}")

    def bind_tools(self, tools: list[Any]) -> _OracleToolCallingModel:
        del tools
        return self._tool_model

    def with_structured_output(self, schema: type[IncidentReport]) -> _OracleStructuredModel:
        del schema
        return self._structured_model
