# D-A5-4: Evidence citation and honesty guardrail

## Context

The investigation graph asks an LLM to produce a structured `IncidentReport`
with a `root_cause`, `evidence`, and a `confidence`. LLMs can (and do)
fabricate plausible-looking citations, or state a confident root cause from
thin evidence. For an on-call tool, a wrong-but-confident answer is worse than
"I don't know" — it sends someone chasing the wrong fix during an incident.

## Decision

Add a pure-code, post-flight guardrail (`oncall.guardrails.evidence_check`)
that runs after the `summarize` node and before the graph ends:

1. **Citation coverage** — every `Evidence.reference` in the report must
   resolve to a `trace_id` or known-issue `id` that a tool call *actually*
   returned during the run (parsed back out of the recorded `ToolMessage`
   history). References that don't resolve are unsupported claims, not
   evidence.
2. **Honesty forcing** — a report with no evidence, or whose citation
   coverage falls below `settings.citation_coverage_floor` (default `1.0`),
   is rewritten with `insufficient_evidence=True` and a dampened
   `confidence`. The guardrail never invents evidence to raise coverage; it
   only downgrades.
3. **Severity-claim check** — a report that uses attack-like language
   ("attack", "breach", "ddos", "malicious", "intrusion", "compromise") must
   have at least one citation resolving to a `WARN`/`ERROR`/`FATAL` log line
   or a known-issue match. This directly targets the adversarial fixture
   (a benign traffic spike that must not be reported as an attack).

This lives in `oncall.guardrails`, sitting above `oncall.tools` in the
import-linter layering (`api -> graph -> guardrails -> tools -> retrieval ->
schemas`), and is invoked by a `verify` node in `oncall.graph` — the graph is
the only layer allowed to import both `guardrails` and the LLM-facing nodes.

## Consequences

- The guardrail is pure code with no model call, so it's cheap, deterministic,
  and directly unit-testable (`tests/test_evidence_check.py`) without mocking
  an LLM.
- A downgraded report is still returned to the caller — the guardrail
  degrades gracefully to "insufficient evidence" rather than raising, which
  keeps the graph's control flow simple (one linear edge from `summarize` to
  `verify` to `END`).
- The 1.0 coverage floor is strict by default; a future phase could relax it
  per-severity or expose it as a per-request override once evals
  (Phase 7) establish a baseline false-downgrade rate.
