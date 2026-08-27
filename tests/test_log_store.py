from __future__ import annotations

from pathlib import Path

import pytest

from oncall.retrieval.log_store import LogStore
from oncall.settings import Settings


@pytest.fixture
def populated_store(tmp_path: Path) -> LogStore:
    settings = Settings(
        log_db_path=str(tmp_path / "logs.db"),
        vendor_kb_path=str(tmp_path / "kb.json"),
    )
    from data.generate_logs import build_artifacts

    build_artifacts(settings=settings)
    return LogStore(settings=settings)


def test_count_is_positive(populated_store: LogStore) -> None:
    assert populated_store.count() > 0


def test_query_by_service(populated_store: LogStore) -> None:
    rows = populated_store.query(service="payment-service", limit=10)
    assert all(r.service == "payment-service" for r in rows)


def test_query_by_trace_id(populated_store: LogStore) -> None:
    incidents = populated_store.get_incidents()
    assert incidents
    trace_id = incidents[0].trace_ids[0]
    rows = populated_store.query(trace_id=trace_id, limit=100)
    assert all(r.trace_id == trace_id for r in rows)


def test_incidents_seeded(populated_store: LogStore) -> None:
    incidents = populated_store.get_incidents()
    assert len(incidents) == 5
    assert {i.incident_id for i in incidents} == {
        "INC-001",
        "INC-002",
        "INC-003",
        "INC-004",
        "INC-005",
    }


def test_fixtures_seeded(populated_store: LogStore) -> None:
    fixtures = populated_store.get_fixtures()
    assert len(fixtures) == 2
    types = {f.fixture_type for f in fixtures}
    assert types == {"adversarial", "honesty"}
