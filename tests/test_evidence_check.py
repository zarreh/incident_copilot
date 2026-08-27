from __future__ import annotations

import json

from langchain_core.messages import ToolMessage

from oncall.guardrails.evidence_check import (
    build_evidence_index,
    check_citations,
    enforce_honesty,
    verify_report,
)
from oncall.schemas.models import Evidence, IncidentReport


def _tool_message(payload: list[dict[str, object]]) -> ToolMessage:
    return ToolMessage(content=json.dumps(payload), tool_call_id="call-1")


def test_build_evidence_index_collects_trace_ids_and_known_issue_ids() -> None:
    messages = [
        _tool_message([{"trace_id": "abc-1", "service": "payment-service", "level": "ERROR"}]),
        _tool_message([{"id": "KI-001", "vendor": "postgresql"}]),
    ]

    index = build_evidence_index(messages)

    assert index["abc-1"]["level"] == "ERROR"
    assert index["KI-001"]["vendor"] == "postgresql"


def test_check_citations_full_coverage() -> None:
    index = {"abc-1": {"level": "ERROR"}}
    report = IncidentReport(
        title="t",
        severity="high",
        root_cause="rc",
        evidence=[Evidence(source="log", reference="abc-1", detail="d")],
        confidence=0.8,
    )

    result = check_citations(report, index)

    assert result.coverage == 1.0
    assert result.unresolved_references == ()


def test_check_citations_flags_unresolved_reference() -> None:
    index: dict[str, dict[str, object]] = {}
    report = IncidentReport(
        title="t",
        severity="high",
        root_cause="rc",
        evidence=[Evidence(source="log", reference="made-up", detail="d")],
        confidence=0.8,
    )

    result = check_citations(report, index)

    assert result.coverage == 0.0
    assert result.unresolved_references == ("made-up",)


def test_enforce_honesty_forces_insufficient_when_no_evidence() -> None:
    report = IncidentReport(title="t", severity="low", root_cause="rc", confidence=0.9)

    verified = enforce_honesty(report, {})

    assert verified.insufficient_evidence is True
    assert verified.confidence == 0.0


def test_enforce_honesty_downgrades_low_citation_coverage() -> None:
    index = {"real-1": {"level": "ERROR"}}
    report = IncidentReport(
        title="t",
        severity="high",
        root_cause="db pool exhaustion",
        evidence=[Evidence(source="log", reference="fabricated", detail="d")],
        confidence=0.9,
    )

    verified = enforce_honesty(report, index)

    assert verified.insufficient_evidence is True
    assert "unverifiable" in verified.root_cause
    assert verified.confidence == 0.0


def test_enforce_honesty_flags_severity_claim_without_anomalous_support() -> None:
    index = {"info-1": {"level": "INFO"}}
    report = IncidentReport(
        title="Suspected DDoS attack",
        severity="critical",
        root_cause="traffic spike looks like an attack",
        evidence=[Evidence(source="log", reference="info-1", detail="benign traffic spike")],
        confidence=0.95,
    )

    verified = enforce_honesty(report, index)

    assert verified.insufficient_evidence is True
    assert verified.confidence == 0.0


def test_enforce_honesty_allows_severity_claim_with_error_evidence() -> None:
    index = {"err-1": {"level": "ERROR"}}
    report = IncidentReport(
        title="Compromised auth-service",
        severity="critical",
        root_cause="malicious login attempts caused a breach",
        evidence=[Evidence(source="log", reference="err-1", detail="repeated 401s")],
        confidence=0.9,
    )

    verified = enforce_honesty(report, index)

    assert verified.insufficient_evidence is False
    assert verified.confidence == 0.9


def test_verify_report_end_to_end() -> None:
    messages = [_tool_message([{"trace_id": "abc-1", "level": "ERROR"}])]
    report = IncidentReport(
        title="t",
        severity="high",
        root_cause="rc",
        evidence=[Evidence(source="log", reference="abc-1", detail="d")],
        confidence=0.8,
    )

    verified = verify_report(report, messages)

    assert verified.insufficient_evidence is False
