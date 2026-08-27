"""LangChain tool wrapping the AST + Docker sandbox for ad-hoc diagnostic scripts."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from oncall.settings import Settings
from oncall.tools.sandbox import run_script


class RunDiagnosticArgs(BaseModel):
    code: str = Field(description="Python source to run in the sandbox; use print() for output")


def build_run_diagnostic_tool(settings: Settings) -> StructuredTool:
    def _run(code: str) -> str:
        result = run_script(code, settings=settings)
        if result.rejected_reason:
            return f"REJECTED: {result.rejected_reason}"
        if not result.ok:
            return f"FAILED (exit {result.exit_code}): {result.stderr}"
        return result.stdout

    return StructuredTool.from_function(
        func=_run,
        name="run_diagnostic_script",
        description=(
            "Run a short, side-effect-free Python script in a sandboxed, "
            "network-isolated container to compute statistics over data you "
            "already retrieved (e.g. counts, rates). The script cannot import "
            "os/sys/subprocess/socket or use eval/exec/open."
        ),
        args_schema=RunDiagnosticArgs,
    )
