# D-A5-2: Web search default

## Context

The copilot may need vendor KB or known-issue lookup. Live search can be slow
and flaky in tests.

## Decision

Default to a local curated vendor/known-issue JSON KB. Live DuckDuckGo search
is opt-in via `ONCALL_WEB_SEARCH=live`.

## Consequences

Deterministic evals, reproducible offline runs, and one explicit flag to enable
live search.
