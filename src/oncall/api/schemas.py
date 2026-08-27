"""Request/response models for the investigations API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from oncall.schemas.models import IncidentReport


class CreateInvestigationRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class CreateInvestigationResponse(BaseModel):
    id: str
    status: str


class CostSummaryEntry(BaseModel):
    node: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class InvestigationResponse(BaseModel):
    id: str
    question: str
    status: str
    created_at: str
    updated_at: str
    report: IncidentReport | None
    error: str | None
    total_cost_usd: float
    costs: list[CostSummaryEntry]
