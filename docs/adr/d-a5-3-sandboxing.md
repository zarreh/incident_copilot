# D-A5-3: Sandboxing

## Context

The copilot may run user-provided or LLM-generated diagnostic scripts.

## Decision

Two-stage sandbox:

1. AST static check to block unsafe constructs before execution.
2. Docker containerized execution with `--network=none --read-only`,
   CPU/memory caps, non-root user, and a timeout.

## Consequences

Defense in depth. The AST check gives fast feedback; the container limits blast
radius.
