"""Layer 1 canonical regression set for the investigation copilot.

Runs each of the 7 seeded scenarios (5 real incidents + 2 adversarial/honesty
fixtures, `data/generate_logs.py`) through the REAL compiled graph -- real
tools, real log store, real Phase 4 guardrail -- with a scripted oracle model
(`evals/oracle.py`) standing in for a live LLM, so this suite needs no
`OPENAI_API_KEY` and no Docker sandbox. `evals/run.py` gates CI: non-zero
exit if the guardrail fails to flag a fixture, or over-flags a real incident.
"""

from __future__ import annotations

import asyncio
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from langchain_core.messages import HumanMessage
from zarreh_agentkit.evals import EvalOutcome

from data.generate_logs import build_artifacts
from evals.oracle import OracleChatModel
from evals.scenarios import SCENARIOS, Scenario
from oncall.graph.builder import build_investigation_graph
from oncall.retrieval.log_store import LogStore
from oncall.retrieval.vendor_kb import VendorKB
from oncall.schemas.models import IncidentReport
from oncall.settings import Settings


@dataclass(frozen=True)
class EvalResult:
    scenario_id: str
    expected_insufficient_evidence: bool
    actual_insufficient_evidence: bool
    evidence_count: int
    latency_seconds: float

    @property
    def passed(self) -> bool:
        return self.actual_insufficient_evidence == self.expected_insufficient_evidence


async def _run_scenario(
    scenario: Scenario, log_store: LogStore, vendor_kb: VendorKB, settings: Settings
) -> EvalResult:
    oracle = OracleChatModel(scenario.id, log_store, vendor_kb)
    graph = build_investigation_graph(
        settings=settings, llm=oracle, log_store=log_store, vendor_kb=vendor_kb
    )
    started = time.perf_counter()
    result = await graph.ainvoke(
        {
            "question": scenario.question,
            "messages": [HumanMessage(content=scenario.question)],
            "started_at": time.time(),
        }
    )
    latency_seconds = time.perf_counter() - started
    report = result["report"]
    assert isinstance(report, IncidentReport), f"{scenario.id}: no report was produced"
    return EvalResult(
        scenario_id=scenario.id,
        expected_insufficient_evidence=scenario.expect_insufficient_evidence,
        actual_insufficient_evidence=report.insufficient_evidence,
        evidence_count=len(report.evidence),
        latency_seconds=latency_seconds,
    )


async def _run_all() -> list[EvalResult]:
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(
            log_db_path=str(Path(tmp) / "logs.db"),
            vendor_kb_path=str(Path(tmp) / "kb.json"),
        )
        build_artifacts(settings=settings)
        log_store = LogStore(settings=settings)
        vendor_kb = VendorKB(settings=settings)
        return [await _run_scenario(s, log_store, vendor_kb, settings) for s in SCENARIOS]


def run_canonical_eval() -> list[EvalResult]:
    return asyncio.run(_run_all())


def outcomes(results: list[EvalResult]) -> list[EvalOutcome]:
    return [EvalOutcome(case_id=r.scenario_id, passed=r.passed) for r in results]


def print_report(results: list[EvalResult]) -> None:
    print(
        f"{'scenario':14}{'expect_insuff':16}{'actual_insuff':16}{'result':10}{'evidence':10}latency_s"
    )
    for r in results:
        status = "OK" if r.passed else "MISMATCH"
        print(
            f"{r.scenario_id:14}{str(r.expected_insufficient_evidence):16}"
            f"{str(r.actual_insufficient_evidence):16}{status:10}{r.evidence_count:<10}"
            f"{r.latency_seconds:.3f}"
        )
    n = len(results)
    passed = sum(1 for r in results if r.passed)
    print(f"\n{passed}/{n} canonical scenarios matched the expected honesty-guardrail outcome.")
