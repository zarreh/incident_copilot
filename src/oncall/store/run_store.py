"""Read-write repository over runs.db — the operational record of every
investigation, persisted so a run is replayable at any time, live or long
after it finished (Phase 5).

Unlike `LogStore`/`VendorKB`, this store creates its own schema on first use:
it holds operational state, not build-time synthetic data.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from oncall.store.models import CostEntry, RunEvent, RunRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    report_json TEXT,
    error TEXT
);
CREATE TABLE IF NOT EXISTS run_events (
    run_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    node TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (run_id, sequence)
);
CREATE TABLE IF NOT EXISTS run_costs (
    run_id TEXT NOT NULL,
    node TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _run_from_row(row: tuple[object, ...]) -> RunRecord:
    return RunRecord(
        id=str(row[0]),
        question=str(row[1]),
        status=str(row[2]),
        created_at=str(row[3]),
        updated_at=str(row[4]),
        report_json=None if row[5] is None else str(row[5]),
        error=None if row[6] is None else str(row[6]),
    )


class RunStore:
    """Persists investigation runs, their node-by-node events, and per-node
    LLM cost — the single source of truth `GET /investigations/{id}` and
    `GET /investigations/{id}/events` read from."""

    def __init__(self, db_path: Path) -> None:
        # check_same_thread=False: FastAPI handles requests and the
        # background run executor from different tasks against one connection.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def create_run(self, run_id: str, question: str) -> None:
        now = _now()
        self._conn.execute(
            "INSERT INTO runs (id, question, status, created_at, updated_at) "
            "VALUES (?, ?, 'running', ?, ?)",
            (run_id, question, now, now),
        )
        self._conn.commit()

    def get_run(self, run_id: str) -> RunRecord | None:
        row = self._conn.execute(
            "SELECT id, question, status, created_at, updated_at, report_json, error "
            "FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        return _run_from_row(row) if row else None

    def complete_run(self, run_id: str, report_json: str) -> None:
        self._conn.execute(
            "UPDATE runs SET status = 'completed', updated_at = ?, report_json = ? WHERE id = ?",
            (_now(), report_json, run_id),
        )
        self._conn.commit()

    def fail_run(self, run_id: str, error: str) -> None:
        self._conn.execute(
            "UPDATE runs SET status = 'failed', updated_at = ?, error = ? WHERE id = ?",
            (_now(), error, run_id),
        )
        self._conn.commit()

    def append_event(self, run_id: str, sequence: int, node: str, payload_json: str) -> None:
        self._conn.execute(
            "INSERT INTO run_events (run_id, sequence, node, payload_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (run_id, sequence, node, payload_json, _now()),
        )
        self._conn.commit()

    def get_events(self, run_id: str, after_sequence: int = -1) -> list[RunEvent]:
        """Every event with `sequence > after_sequence`, in order — the same
        call replays a whole run from the start (default) or tails new
        events since the last one a client already saw."""
        rows = self._conn.execute(
            "SELECT run_id, sequence, node, payload_json, created_at FROM run_events "
            "WHERE run_id = ? AND sequence > ? ORDER BY sequence",
            (run_id, after_sequence),
        ).fetchall()
        return [
            RunEvent(
                run_id=str(row[0]),
                sequence=int(row[1]),
                node=str(row[2]),
                payload_json=str(row[3]),
                created_at=str(row[4]),
            )
            for row in rows
        ]

    def record_costs(self, run_id: str, entries: list[CostEntry]) -> None:
        if not entries:
            return
        self._conn.executemany(
            "INSERT INTO run_costs "
            "(run_id, node, model, prompt_tokens, completion_tokens, cost_usd) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (run_id, e.node, e.model, e.prompt_tokens, e.completion_tokens, e.cost_usd)
                for e in entries
            ],
        )
        self._conn.commit()

    def get_costs(self, run_id: str) -> list[CostEntry]:
        rows = self._conn.execute(
            "SELECT node, model, prompt_tokens, completion_tokens, cost_usd "
            "FROM run_costs WHERE run_id = ?",
            (run_id,),
        ).fetchall()
        return [
            CostEntry(
                node=str(row[0]),
                model=str(row[1]),
                prompt_tokens=int(row[2]),
                completion_tokens=int(row[3]),
                cost_usd=float(row[4]),
            )
            for row in rows
        ]
