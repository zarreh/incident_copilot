"""FastAPI dependency providers: process-shared singletons for the run store
and the real investigation graph (built lazily against the app's checkpointer).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import Request

from oncall.graph.builder import build_investigation_graph
from oncall.settings import get_settings
from oncall.store.run_store import RunStore


@lru_cache
def get_run_store() -> RunStore:
    """Durable investigation store (runs, events, per-node costs)."""
    settings = get_settings()
    Path(settings.run_store_path).parent.mkdir(parents=True, exist_ok=True)
    return RunStore(Path(settings.run_store_path))


def get_investigation_graph(request: Request) -> Any:
    """The real investigation graph, compiled once against the app's async
    SQLite checkpointer (opened in the lifespan) and cached on `app.state`.

    Built lazily on the first real request — never at import or app-startup
    time — so constructing the production `ChatOpenAI` model (which requires
    an API key) never happens during a test run or a plain `make check`.
    """
    state = request.app.state
    graph = getattr(state, "investigation_graph", None)
    if graph is None:
        graph = build_investigation_graph(get_settings(), checkpointer=state.checkpointer)
        state.investigation_graph = graph
    return graph
