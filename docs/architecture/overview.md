# Architecture overview

```mermaid
flowchart LR
    UI[Next.js frontend] -- "POST /investigations\nGET /investigations/{id}\nGET .../events (SSE)" --> API

    subgraph API[oncall.api]
        Routes[routes/investigations.py]
        Runner[run_executor.py]
        Store[(RunStore\nSQLite)]
    end

    Routes -- background task --> Runner
    Runner -- persists events/report/cost --> Store
    Routes -- poll / replay --> Store

    Runner --> Graph

    subgraph Graph[oncall.graph — investigation graph]
        Agent[agent node]
        Tools[tools node]
        Summarize[summarize node]
        Verify[verify node]
        Agent -- tool call --> Tools
        Tools --> Agent
        Agent -- done / budget hit --> Summarize
        Summarize --> Verify
    end

    Tools --> ToolLayer[oncall.tools\nsearch_logs / lookup_known_issue / run_diagnostic_script]
    Verify --> Guardrail[oncall.guardrails.evidence_check\ncitation + honesty check]

    ToolLayer --> Retrieval[oncall.retrieval\nLogStore + VendorKB]
    ToolLayer --> Sandbox[oncall.tools.sandbox\nAST check + Docker execution]
    Retrieval --> DB[(logs.db\nsynthetic, seeded)]
```

## Layers, and why the boundaries are enforced

The import-linter contract in `pyproject.toml` (checked by `make imports`)
fixes a strict layering:

```
api -> graph -> guardrails -> tools -> retrieval -> schemas
```

A higher layer may import a lower one, never the reverse, and a second
contract forbids `tools`, `guardrails`, and `retrieval` from importing
`graph` at all. Concretely, this means:

- **`oncall.tools`** only ever sees the read-only `logs` table (via
  `LogStore.query`) — it can never reach the `incidents`/`fixtures` ground
  truth tables that exist purely for evals.
- **`oncall.guardrails`** is pure code with no model call and no tool
  access; it only inspects the `IncidentReport` and the recorded message
  history after the fact.
- **`oncall.graph`** is the only layer allowed to wire an LLM, the tools,
  and the guardrail together — no other layer can silently reach into an
  LLM or invent evidence.
- **`oncall.store`** (the operational run/event/cost persistence layer) is
  deliberately *not* part of this contract — it's infrastructure the API
  layer owns directly, not part of the investigation's reasoning path.

See the [ADRs](../adr/d-a5-1-domain-and-repo.md) for the specific decisions
behind each layer, and [state and flow](state-and-flow.md) for what happens
inside the graph box above.
