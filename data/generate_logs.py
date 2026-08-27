"""Generate the synthetic log DB and curated vendor KB.

Phase 0: creates empty/readable schemas so the app can start. Phase 1 will
seed the five planted incidents, adversarial/honesty fixtures, and vendor KB.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from oncall.settings import get_settings

settings = get_settings()

SCHEMA = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    service TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    trace_id TEXT,
    span_id TEXT,
    metadata TEXT
);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_service ON logs(service);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_trace_id ON logs(trace_id);
"""


def ensure_dirs() -> None:
    Path(settings.log_db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.vendor_kb_path).parent.mkdir(parents=True, exist_ok=True)


def build_log_db() -> None:
    conn = sqlite3.connect(settings.log_db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def build_vendor_kb() -> None:
    kb = {
        "version": "0.1.0",
        "vendors": {},
        "known_issues": [],
    }
    Path(settings.vendor_kb_path).write_text(json.dumps(kb, indent=2))


def main() -> None:
    ensure_dirs()
    build_log_db()
    build_vendor_kb()
    print(f"Initialized {settings.log_db_path} and {settings.vendor_kb_path}")


if __name__ == "__main__":
    main()
