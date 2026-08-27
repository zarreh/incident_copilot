"""CLI entry point for `make eval` (Phase 7).

Runs the Layer 1 canonical regression set and prints the pass/fail matrix.
The run/print/gate shell is `zarreh_agentkit.evals.run_eval_cli`; the
scenarios and oracle model stay local (evals/scenarios.py, evals/oracle.py).
No live model or Docker sandbox is required -- see evals/oracle.py.
"""

from __future__ import annotations

import sys

from zarreh_agentkit.evals import run_eval_cli

from evals.canonical import outcomes, print_report, run_canonical_eval


def main() -> int:
    return run_eval_cli(run_canonical_eval, print_report, outcomes)


if __name__ == "__main__":
    sys.exit(main())
