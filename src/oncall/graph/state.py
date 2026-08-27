"""Investigation graph state."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from oncall.schemas.models import IncidentReport


class InvestigationState(TypedDict, total=False):
    """`total=False`: `report` is present only once `summarize` has run."""

    question: str
    messages: Annotated[list[BaseMessage], add_messages]
    started_at: float
    report: IncidentReport
