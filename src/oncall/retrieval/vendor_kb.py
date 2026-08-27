"""Read-only access to the curated vendor/known-issue KB."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from oncall.settings import Settings, get_settings


@dataclass(frozen=True)
class KnownIssue:
    id: str
    vendor: str
    symptoms: tuple[str, ...]
    cause: str
    mitigation: str


class VendorKB:
    """In-memory curated vendor KB loaded from JSON."""

    def __init__(self, kb_path: str | Path | None = None, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._kb_path = Path(kb_path) if kb_path else Path(self._settings.vendor_kb_path)
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        raw = Path(self._kb_path).read_text(encoding="utf-8")
        return cast(dict[str, Any], json.loads(raw))

    def issues(self) -> list[KnownIssue]:
        return [
            KnownIssue(
                id=item["id"],
                vendor=item["vendor"],
                symptoms=tuple(item["symptoms"]),
                cause=item["cause"],
                mitigation=item["mitigation"],
            )
            for item in self._data.get("known_issues", [])
        ]

    def find(self, vendor: str | None = None, symptom: str | None = None) -> list[KnownIssue]:
        results = self.issues()
        if vendor:
            results = [i for i in results if i.vendor == vendor]
        if symptom:
            symptom_lower = symptom.lower()
            results = [
                i
                for i in results
                if any(symptom_lower in s.lower() for s in i.symptoms)
                or symptom_lower in i.cause.lower()
            ]
        return results
