"""Investigation endpoints: create, poll, and stream via SSE."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from oncall.api.deps import get_investigation_graph, get_run_store
from oncall.api.rate_limit import DEFAULT_RATE_LIMIT, limiter
from oncall.api.run_executor import execute_investigation
from oncall.api.schemas import (
    CostSummaryEntry,
    CreateInvestigationRequest,
    CreateInvestigationResponse,
    InvestigationResponse,
)
from oncall.api.streaming import stream_investigation_events
from oncall.schemas.models import IncidentReport
from oncall.settings import Settings, get_settings
from oncall.store.run_store import RunStore

router = APIRouter(prefix="/investigations", tags=["investigations"])

GraphDep = Annotated[Any, Depends(get_investigation_graph)]
RunStoreDep = Annotated[RunStore, Depends(get_run_store)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post("", status_code=202)
@limiter.limit(DEFAULT_RATE_LIMIT)
async def create_investigation(
    request: Request,
    body: CreateInvestigationRequest,
    background_tasks: BackgroundTasks,
    graph: GraphDep,
    run_store: RunStoreDep,
    settings: SettingsDep,
) -> CreateInvestigationResponse:
    """Starts one investigation as a background task and returns immediately
    — poll `GET /{id}` or stream `GET /{id}/events` for progress."""
    run_id = str(uuid4())
    run_store.create_run(run_id, body.question)
    background_tasks.add_task(
        execute_investigation, run_id, body.question, graph, run_store, settings
    )
    return CreateInvestigationResponse(id=run_id, status="running")


@router.get("/{run_id}")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def get_investigation(
    request: Request, run_id: str, run_store: RunStoreDep
) -> InvestigationResponse:
    run = run_store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    report = IncidentReport.model_validate_json(run.report_json) if run.report_json else None
    costs = [
        CostSummaryEntry(
            node=c.node,
            model=c.model,
            prompt_tokens=c.prompt_tokens,
            completion_tokens=c.completion_tokens,
            cost_usd=c.cost_usd,
        )
        for c in run_store.get_costs(run_id)
    ]
    return InvestigationResponse(
        id=run.id,
        question=run.question,
        status=run.status,
        created_at=run.created_at,
        updated_at=run.updated_at,
        report=report,
        error=run.error,
        total_cost_usd=sum(c.cost_usd for c in costs),
        costs=costs,
    )


@router.get("/{run_id}/events")
@limiter.limit(DEFAULT_RATE_LIMIT)
async def investigation_events(
    request: Request, run_id: str, run_store: RunStoreDep
) -> EventSourceResponse:
    if run_store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return EventSourceResponse(stream_investigation_events(run_store, run_id))
