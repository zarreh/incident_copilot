"""Operational records for the investigation run store (Phase 5)."""

from __future__ import annotations

from dataclasses import dataclass

from zarreh_agentkit.cost import CostEntry
from zarreh_agentkit.runs import RunEvent


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


__all__ = ["CostEntry", "RunEvent", "RunRecord"]
