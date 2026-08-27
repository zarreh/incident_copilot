# A5 — Incident Investigation Copilot

An on-call assistant that retrieves logs, runs sandboxed diagnostics, and
drafts incident reports.

> Status: all planned phases complete (data, sandboxed tools, investigation
> graph, evidence/honesty guardrail, run store + streaming API, frontend,
> canonical evals, CI/docs).

## Quick start

```bash
cp .env.example .env        # fill in OPENAI_API_KEY, LANGSMITH_API_KEY, etc.
make data                   # generate synthetic logs + vendor KB
make check                  # ruff + mypy + import-linter + pytest
make dev                    # uvicorn on http://localhost:8000
```

## Repo map

```
src/oncall/
  api/           FastAPI app, middleware, routes
  graph/         LangGraph investigation graph
  tools/         sandboxed diagnostic tools
  retrieval/     log + vendor-KB retrieval
  guardrails/    safety + budget guardrails
  schemas/       shared Pydantic models
data/            generated synthetic logs and KB (not committed)
docs/            MkDocs + ADRs
evals/           canonical eval suite
frontend/        Next.js UI
reference/       source notebooks (local only)
```

## License

MIT
