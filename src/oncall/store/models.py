"""Operational records for the investigation run store (Phase 5)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunRecord:
    """The operational record of one investigation run.

    `status` is one of `running`, `completed`, or `failed`. `report_json`
    carries the final `IncidentReport` (as JSON) once the run completes.
    """

    id: str
    question: str
    status: str
    created_at: str
    updated_at: str
    report_json: str | None
    error: str | None


@dataclass(frozen=True)
class RunEvent:
    """One graph node boundary persisted during a run, so the SSE stream
    replays whether a client watches live or reconnects after it finished."""

    run_id: str
    sequence: int
    node: str
    payload_json: str
    created_at: str


@dataclass(frozen=True)
class CostEntry:
    """One attributed LLM call within a run."""

    node: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
