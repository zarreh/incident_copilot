"""Shared Pydantic models for the Incident Investigation Copilot."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class Evidence(BaseModel):
    """One piece of evidence backing (or contradicting) a root cause claim."""

    source: str = Field(description="Where this came from, e.g. 'log' or 'known_issue'")
    reference: str = Field(description="A trace_id, timestamp, or known-issue id")
    detail: str = Field(description="The specific fact this reference supports")


class IncidentReport(BaseModel):
    """The investigation copilot's structured output for one investigation run."""

    title: str
    severity: str = Field(description="e.g. low, medium, high, critical")
    root_cause: str
    evidence: list[Evidence] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    insufficient_evidence: bool = Field(
        default=False,
        description="True when the gathered evidence does not support a confident root cause",
    )
