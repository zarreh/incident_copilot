"""Bridges a persisted investigation run to Server-Sent Events."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from functools import partial
from typing import Any

from zarreh_agentkit.runs import replay_and_tail

from oncall.store.run_store import RunStore


def stream_investigation_events(run_store: RunStore, run_id: str) -> AsyncIterator[str]:
    """Replays every event already persisted for a run, then — while the run
    is still executing — tails newly-appended events until it reaches a
    terminal status. Works identically whether a client connects the instant
    a run starts or reconnects long after it finished.
    """

    def poll_end() -> dict[str, Any] | None:
        run = run_store.get_run(run_id)
        if run is not None and run.status == "running":
            return None
        status = run.status if run is not None else "not_found"
        report = json.loads(run.report_json) if run is not None and run.report_json else None
        return {"status": status, "report": report}

    return replay_and_tail(partial(run_store.get_events, run_id), poll_end)
