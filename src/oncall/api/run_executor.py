"""Runs one investigation to completion as a background task, persisting
every node event, per-node LLM cost, and the final report to the RunStore as
it happens — so a run is replayable from the store whether a client is
watching live or reconnects later (Phase 5).
"""

from __future__ import annotations

import time
from typing import Any

from langchain_core.messages import HumanMessage
from zarreh_agentkit.observability import build_tracing_callbacks
from zarreh_agentkit.runs import execute_run

from oncall.schemas.models import IncidentReport
from oncall.settings import Settings
from oncall.store.run_store import RunStore

# The graph's four node boundaries (execute_run also requires
# name == langgraph_node, which drops LCEL sub-steps sharing the tag).
_GRAPH_NODE_NAMES = frozenset({"agent", "tools", "summarize", "verify"})


async def execute_investigation(
    run_id: str,
    question: str,
    graph: Any,
    run_store: RunStore,
    settings: Settings,
) -> None:
    def finalize(final_state: dict[str, Any]) -> None:
        report = final_state.get("report")
        if isinstance(report, IncidentReport):
            run_store.complete_run(run_id, report.model_dump_json())
        else:
            run_store.fail_run(run_id, "graph completed without producing a report")

    await execute_run(
        run_id=run_id,
        graph=graph,
        graph_input={
            "question": question,
            "messages": [HumanMessage(content=question)],
            "started_at": time.time(),
        },
        store=run_store,
        finalize=finalize,
        callbacks=build_tracing_callbacks(settings.langsmith_api_key, settings.langsmith_project),
        node_names=_GRAPH_NODE_NAMES,
        configurable={"thread_id": run_id},
    )
