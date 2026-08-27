# D-A5-3: Sandboxing

## Context

The copilot may run user-provided or LLM-generated diagnostic scripts.

## Decision

Two-stage sandbox:

1. AST static check (`oncall.tools.ast_check`) to block unsafe constructs
   before execution — blocked imports (`os`, `subprocess`, `socket`, ...),
   blocked calls (`eval`, `exec`, `open`, `__import__`, ...), and dunder
   attribute/name access used to escape sandboxes.
2. Docker containerized execution (`oncall.tools.sandbox`) with
   `--network=none --read-only`, CPU/memory caps, non-root user, and a
   timeout that kills the container on expiry.

Both checks live in `oncall.tools`, not `oncall.guardrails` — they are
intrinsic to the sandboxed tool's execution boundary, not a business-level
guardrail layered on top of it. This also respects the import-linter
layering contract (`guardrails` sits above `tools`).

## Consequences

Defense in depth. The AST check gives fast feedback; the container limits blast
radius.
