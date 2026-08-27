# D-A5-1: Domain and repo

## Context

A5 needs its own repository and package name under the portfolio.

## Decision

- Repository: `incident_copilot`
- Python package: `oncall`
- Env prefix: `ONCALL_`
- Target domain: `oncall.zarreh.ai`

## Consequences

Clear separation from A3/A4, and `oncall` is short enough for CLI and module paths.
