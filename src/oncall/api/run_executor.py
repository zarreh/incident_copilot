"""Runs one investigation to completion as a background task, persisting
every node event, per-node LLM cost, and the final report to the RunStore as
it happens — so a run is replayable from the store whether a client is
watching live or reconnects later (Phase 5).
"""

from __future__ import annotations

import json
import time
from typing import Any

import structlog
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel
from zarreh_agentkit.cost import CostTrackingHandler
from zarreh_agentkit.observability import build_tracing_callbacks

from oncall.schemas.models import IncidentReport
from oncall.settings import Settings
from oncall.store.models import CostEntry
from oncall.store.run_store import RunStore

logger = structlog.get_logger(__name__)

# The graph's four node boundaries. astream_events also emits on_chain_end for
# internal LCEL sub-steps whose names can collide with a node's
# langgraph_node tag, so filtering on name alone is not enough.
_GRAPH_NODE_NAMES = frozenset({"agent", "tools", "summarize", "verify"})


def _json_default(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return str(value)


async def execute_investigation(
    run_id: str,
    question: str,
    graph: Any,
    run_store: RunStore,
    settings: Settings,
) -> None:
    structlog.contextvars.bind_contextvars(correlation_id=run_id)
    cost_handler = CostTrackingHandler()
    callbacks: list[BaseCallbackHandler] = [
        cost_handler,
        *build_tracing_callbacks(settings.langsmith_api_key, settings.langsmith_project),
    ]
    config: RunnableConfig = {
        "configurable": {"thread_id": run_id},
        "callbacks": callbacks,
        "metadata": {"correlation_id": run_id},
    }
    try:
        initial_state = {
            "question": question,
            "messages": [HumanMessage(content=question)],
            "started_at": time.time(),
        }
        final_state: dict[str, Any] = {}
        sequence = 0

        async for event in graph.astream_events(initial_state, version="v2", config=config):
            if event["event"] != "on_chain_end":
                continue
            metadata = event.get("metadata") or {}
            node_name = metadata.get("langgraph_node")
            if node_name not in _GRAPH_NODE_NAMES or event.get("name") != node_name:
                continue
            output = event.get("data", {}).get("output")
            if isinstance(output, dict):
                final_state.update(output)
            run_store.append_event(
                run_id, sequence, node_name, json.dumps(output, default=_json_default)
            )
            sequence += 1

        run_store.record_costs(
            run_id,
            [
                CostEntry(
                    node=e.node,
                    model=e.model,
                    prompt_tokens=e.prompt_tokens,
                    completion_tokens=e.completion_tokens,
                    cost_usd=e.cost_usd,
                )
                for e in cost_handler.entries
            ],
        )

        report = final_state.get("report")
        if isinstance(report, IncidentReport):
            run_store.complete_run(run_id, report.model_dump_json())
        else:
            run_store.fail_run(run_id, "graph completed without producing a report")
    except Exception as exc:  # noqa: BLE001 — any failure must mark the run failed
        logger.error("investigation_failed", run_id=run_id, error=str(exc))
        run_store.fail_run(run_id, str(exc))
    finally:
        structlog.contextvars.unbind_contextvars("correlation_id")
