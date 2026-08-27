from __future__ import annotations

import json
from pathlib import Path

import pytest

from oncall.retrieval.vendor_kb import VendorKB
from oncall.settings import Settings


@pytest.fixture
def kb(tmp_path: Path) -> VendorKB:
    kb_path = tmp_path / "kb.json"
    kb_path.write_text(
        json.dumps(
            {
                "version": "0.1.0",
                "known_issues": [
                    {
                        "id": "KB-TEST-001",
                        "vendor": "postgresql",
                        "symptoms": ["too many clients"],
                        "cause": "connection pool exhausted",
                        "mitigation": "use pgbouncer",
                    }
                ],
            }
        )
    )
    settings = Settings(
        log_db_path=str(tmp_path / "logs.db"),
        vendor_kb_path=str(kb_path),
    )
    return VendorKB(settings=settings)


def test_load_issues(kb: VendorKB) -> None:
    issues = kb.issues()
    assert len(issues) == 1
    assert issues[0].vendor == "postgresql"


def test_find_by_vendor(kb: VendorKB) -> None:
    assert len(kb.find(vendor="postgresql")) == 1
    assert len(kb.find(vendor="redis")) == 0


def test_find_by_symptom(kb: VendorKB) -> None:
    assert len(kb.find(symptom="too many")) == 1
    assert len(kb.find(symptom="cache")) == 0
