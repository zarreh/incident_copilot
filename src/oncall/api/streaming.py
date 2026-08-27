"""Bridges a persisted investigation run to Server-Sent Events."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from oncall.store.run_store import RunStore

_POLL_INTERVAL_SECONDS = 0.25


async def stream_investigation_events(run_store: RunStore, run_id: str) -> AsyncIterator[str]:
    """Replays every event already persisted for a run, then — while the run
    is still executing — tails newly-appended events until it reaches a
    terminal status. Works identically whether a client connects the instant
    a run starts or reconnects long after it finished.
    """
    last_sequence = -1
    while True:
        events = run_store.get_events(run_id, after_sequence=last_sequence)
        for event in events:
            yield json.dumps({"node": event.node, "output": json.loads(event.payload_json)})
            last_sequence = event.sequence

        run = run_store.get_run(run_id)
        if run is None or run.status != "running":
            break
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)

    status = run.status if run is not None else "not_found"
    report = json.loads(run.report_json) if run is not None and run.report_json else None
    yield json.dumps({"node": "__end__", "output": {"status": status, "report": report}})
