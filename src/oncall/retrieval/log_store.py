"""Read-only access to the synthetic log database and incident/fixture metadata."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from oncall.settings import Settings, get_settings


@dataclass(frozen=True)
class LogRecord:
    id: int
    timestamp: str
    service: str
    level: str
    message: str
    trace_id: str
    span_id: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class Incident:
    incident_id: str
    title: str
    root_cause: str
    expected_findings: str
    severity: str
    start_time: str
    end_time: str
    trace_ids: list[str]


@dataclass(frozen=True)
class Fixture:
    fixture_id: str
    title: str
    fixture_type: str
    description: str
    expected_behavior: str
    start_time: str
    end_time: str
    trace_ids: list[str]


class LogStore:
    """Read-only SQLite log store with context-manager connection handling."""

    def __init__(self, db_path: str | Path | None = None, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db_path = Path(db_path) if db_path else Path(self._settings.log_db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM logs").fetchone()
            return int(row[0]) if row else 0

    def query(
        self,
        service: str | None = None,
        level: str | None = None,
        trace_id: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 100,
    ) -> list[LogRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if service:
            clauses.append("service = ?")
            params.append(service)
        if level:
            clauses.append("level = ?")
            params.append(level)
        if trace_id:
            clauses.append("trace_id = ?")
            params.append(trace_id)
        if since:
            clauses.append("timestamp >= ?")
            params.append(since)
        if until:
            clauses.append("timestamp <= ?")
            params.append(until)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM logs {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_incidents(self) -> list[Incident]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM incidents ORDER BY start_time").fetchall()
        return [self._row_to_incident(row) for row in rows]

    def get_incident(self, incident_id: str) -> Incident | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)
            ).fetchone()
        return self._row_to_incident(row) if row else None

    def get_fixtures(self) -> list[Fixture]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM fixtures ORDER BY start_time").fetchall()
        return [self._row_to_fixture(row) for row in rows]

    def _row_to_record(self, row: sqlite3.Row) -> LogRecord:
        return LogRecord(
            id=row["id"],
            timestamp=row["timestamp"],
            service=row["service"],
            level=row["level"],
            message=row["message"],
            trace_id=row["trace_id"],
            span_id=row["span_id"],
            metadata=json.loads(row["metadata"] or "{}"),
        )

    def _row_to_incident(self, row: sqlite3.Row) -> Incident:
        return Incident(
            incident_id=row["incident_id"],
            title=row["title"],
            root_cause=row["root_cause"],
            expected_findings=row["expected_findings"],
            severity=row["severity"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            trace_ids=row["trace_ids"].split(","),
        )

    def _row_to_fixture(self, row: sqlite3.Row) -> Fixture:
        return Fixture(
            fixture_id=row["fixture_id"],
            title=row["title"],
            fixture_type=row["fixture_type"],
            description=row["description"],
            expected_behavior=row["expected_behavior"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            trace_ids=row["trace_ids"].split(","),
        )
