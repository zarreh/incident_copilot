"""Evidence-citation and honesty guardrail for the investigation graph.

Post-flight, pure-code check (no model call): every citation in the final
`IncidentReport` must resolve to something the run actually retrieved via
`search_logs` or `lookup_known_issue` — never to a value the model invented.
A report whose citations don't hold up is downgraded to `insufficient_evidence`
rather than published as-is (docs/adr/d-a5-4-evidence-and-honesty-guardrail.md).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import BaseMessage, ToolMessage

from oncall.schemas.models import IncidentReport

SEVERITY_CLAIM_KEYWORDS = ("attack", "breach", "malicious", "ddos", "intrusion", "compromise")
ANOMALOUS_LEVELS = frozenset({"WARN", "ERROR", "FATAL"})


@dataclass(frozen=True)
class CitationCheckResult:
    coverage: float
    unresolved_references: tuple[str, ...] = field(default_factory=tuple)


def _parse_tool_payload(message: BaseMessage) -> list[dict[str, Any]]:
    if not isinstance(message, ToolMessage) or not isinstance(message.content, str):
        return []
    try:
        payload = json.loads(message.content)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def build_evidence_index(messages: Sequence[BaseMessage]) -> dict[str, dict[str, Any]]:
    """Map every trace_id / known-issue id seen in a tool result to that
    record, so citations and severity claims can both be checked against it."""
    index: dict[str, dict[str, Any]] = {}
    for message in messages:
        for item in _parse_tool_payload(message):
            for key in ("trace_id", "id"):
                value = item.get(key)
                if isinstance(value, str) and value:
                    index[value] = item
    return index


def check_citations(
    report: IncidentReport, evidence_index: dict[str, dict[str, Any]]
) -> CitationCheckResult:
    if not report.evidence:
        return CitationCheckResult(coverage=0.0, unresolved_references=())
    unresolved = tuple(e.reference for e in report.evidence if e.reference not in evidence_index)
    supported = len(report.evidence) - len(unresolved)
    return CitationCheckResult(
        coverage=supported / len(report.evidence), unresolved_references=unresolved
    )


def _makes_severity_claim(report: IncidentReport) -> bool:
    text = f"{report.title} {report.root_cause}".lower()
    return any(keyword in text for keyword in SEVERITY_CLAIM_KEYWORDS)


def _has_anomalous_support(
    report: IncidentReport, evidence_index: dict[str, dict[str, Any]]
) -> bool:
    for item in report.evidence:
        record = evidence_index.get(item.reference)
        if record is None:
            continue
        if record.get("level") in ANOMALOUS_LEVELS:
            return True
        if "vendor" in record:  # a known-issue match is inherently anomalous
            return True
    return False


def enforce_honesty(
    report: IncidentReport,
    evidence_index: dict[str, dict[str, Any]],
    citation_coverage_floor: float = 1.0,
) -> IncidentReport:
    """Downgrade — never fabricate — when the report's claims outrun its evidence."""
    if not report.evidence:
        return report.model_copy(update={"insufficient_evidence": True, "confidence": 0.0})

    citation = check_citations(report, evidence_index)
    if citation.coverage < citation_coverage_floor:
        note = (
            f"{report.root_cause} [unverifiable: citation coverage "
            f"{citation.coverage:.0%}; unresolved references: "
            f"{', '.join(citation.unresolved_references)}]"
        )
        return report.model_copy(
            update={
                "insufficient_evidence": True,
                "confidence": min(report.confidence, citation.coverage),
                "root_cause": note,
            }
        )

    if _makes_severity_claim(report) and not _has_anomalous_support(report, evidence_index):
        note = (
            f"{report.root_cause} [unverifiable: no anomalous log or "
            "known-issue evidence supports this severity claim]"
        )
        return report.model_copy(
            update={"insufficient_evidence": True, "confidence": 0.0, "root_cause": note}
        )

    return report


def verify_report(
    report: IncidentReport,
    messages: Sequence[BaseMessage],
    citation_coverage_floor: float = 1.0,
) -> IncidentReport:
    """The single entry point the graph's `verify` node calls."""
    evidence_index = build_evidence_index(messages)
    return enforce_honesty(report, evidence_index, citation_coverage_floor)
