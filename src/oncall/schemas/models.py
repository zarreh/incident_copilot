"""Shared Pydantic models for the Incident Investigation Copilot."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
