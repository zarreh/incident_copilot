# D-A5-6: Layer 1 canonical eval — oracle model, not a live LLM

## Context

Phase 4 added a pure-code guardrail (`oncall.guardrails.evidence_check`) that
downgrades a report to `insufficient_evidence` when its citations don't
resolve or when it makes an attack-like claim with no anomalous evidence.
`data/generate_logs.py` seeds two fixtures specifically to exercise this:
`FIX-ADV-001` (a benign traffic spike that looks like a DDoS) and
`FIX-HON-001` (a claimed security breach with no supporting logs). A
regression suite needs to prove the guardrail — not a well-behaved model —
is what keeps these fixtures from being reported as real incidents.

## Decision

`evals/` runs a Layer 1 canonical set (`clinical_care_navigator` /
`trade_sureillance_agent` naming convention) through the REAL compiled
graph — real `search_logs`/`lookup_known_issue` tools, real `LogStore`,
real `verify` node — with a scripted **oracle** chat model
(`evals/oracle.py`), not a live LLM:

1. The oracle reads ground truth directly from `LogStore.get_incident()` /
   `get_fixtures()` (deliberately never exposed to the graph itself — see
   `oncall/tools/log_tools.py`) to find each scenario's seeded `trace_id`,
   then scripts the same two-turn shape a real tool-calling model takes:
   one `search_logs(trace_id=...)` call, then a structured `IncidentReport`.
2. For the five real incidents, the oracle cites a genuine anomalous
   (`WARN`/`ERROR`/`FATAL`) log line and states the seeded root cause —
   this is the "well-behaved model" case, and the eval asserts the guardrail
   leaves it alone (`insufficient_evidence` stays `False`).
3. For the two fixtures, the oracle deliberately **overclaims** — it cites a
   real, resolvable log line (so citation coverage is 1.0) but one that is
   merely `INFO`-level, then asserts an attack/breach conclusion the
   evidence doesn't support. This is the adversarial case: if the guardrail
   regresses, this is exactly the shape of report it would let through.
4. `evals/canonical.py` builds a fresh `Settings`/`LogStore`/`VendorKB` in a
   temp dir per run (matching the test suite's `seeded_settings` fixture
   pattern) so the suite is hermetic and needs no `OPENAI_API_KEY`, no
   Docker sandbox, and no network access — it can run in CI unconditionally.
5. `evals/run.py` reuses the shared `zarreh_agentkit.evals.run_eval_cli`
   shell (HARVEST #14: the run/print/gate loop is shareable, the scenarios
   and pass/fail metric are not) and exits non-zero if any of the 7
   scenarios doesn't match its expected `insufficient_evidence` outcome.

## Consequences

- This suite tests the guardrail's decision boundary, not the reasoning
  quality of a live model — `clinical_care_navigator`'s evals intentionally
  drive the real model for that reason (no oracle can stand in for open-ended
  clinical reasoning); A5's oracle only needs to reproduce two shapes
  (well-supported vs. overclaiming), which a deterministic script can do
  faithfully.
- A regression here means the guardrail itself broke, not that a model
  had a bad day — failures are actionable and don't require live-API
  triage.
- This suite does not measure real-model tool-selection quality (e.g.
  whether `gpt-4o` picks `search_logs` over guessing) — that risk is
  accepted for A5 as a portfolio-scale project, same tradeoff
  `trade_sureillance_agent`'s oracle chains make.
