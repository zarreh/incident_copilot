"""Read-write repository over runs.db — the operational record of every
investigation, persisted so a run is replayable at any time, live or long
after it finished (Phase 5).

Unlike `LogStore`/`VendorKB`, this store creates its own schema on first use:
it holds operational state, not build-time synthetic data.
"""

from __future__ import annotations

from pathlib import Path

from zarreh_agentkit.runs import RunEventLog, utc_now

from oncall.store.models import RunRecord

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
"""


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


class RunStore(RunEventLog):
    """Persists investigation runs, their node-by-node events, and per-node
    LLM cost — the single source of truth `GET /investigations/{id}` and
    `GET /investigations/{id}/events` read from."""

    def __init__(self, db_path: Path) -> None:
        super().__init__(db_path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def create_run(self, run_id: str, question: str) -> None:
        now = utc_now()
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
            (utc_now(), report_json, run_id),
        )
        self._conn.commit()

    def fail_run(self, run_id: str, error: str) -> None:
        self._conn.execute(
            "UPDATE runs SET status = 'failed', updated_at = ?, error = ? WHERE id = ?",
            (utc_now(), error, run_id),
        )
        self._conn.commit()
