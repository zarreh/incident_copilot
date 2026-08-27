# Incident Investigation Copilot

An on-call assistant that retrieves logs, runs sandboxed diagnostics, and
drafts incident reports.

## Status

All planned phases complete: synthetic data + vendor KB, AST-checked Docker
sandbox, the investigation graph (retrieve/plan/act/summarize), an
evidence-citation and honesty guardrail, a streaming investigation API with
a SQLite run store, a Next.js frontend, and an oracle-driven canonical eval
suite gating CI. See [how it works](how-it-works/in-plain-language.md) and
the [ADRs](adr/d-a5-1-domain-and-repo.md) for the reasoning behind each
piece.

## Quick start

```bash
make data
make check
make dev
```
