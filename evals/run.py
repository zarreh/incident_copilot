"""Stub eval runner: no canonical cases yet, but the CLI shape is wired."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from zarreh_agentkit.evals.runner import EvalOutcome, run_eval_cli


@dataclass(frozen=True)
class Results:
    outcomes: Sequence[EvalOutcome]


def run_suite() -> Results:
    return Results(outcomes=[])


def print_report(results: Results) -> None:
    print(f"Ran {len(results.outcomes)} canonical scenarios.")


def main() -> int:
    return run_eval_cli(run_suite, print_report, lambda r: r.outcomes)


if __name__ == "__main__":
    raise SystemExit(main())
