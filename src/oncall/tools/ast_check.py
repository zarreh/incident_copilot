"""Static AST safety check for diagnostic scripts, run before any sandboxed
execution. Defense in depth: this catches obviously unsafe constructs fast,
before a script ever reaches the Docker sandbox in `oncall.tools.sandbox`.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

BLOCKED_IMPORTS = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "socket",
        "shutil",
        "ctypes",
        "multiprocessing",
        "threading",
        "importlib",
        "pty",
        "pickle",
        "marshal",
        "code",
        "pdb",
        "signal",
    }
)

BLOCKED_CALL_NAMES = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",
        "input",
        "exit",
        "quit",
        "globals",
        "locals",
        "vars",
        "getattr",
        "setattr",
        "delattr",
        "breakpoint",
    }
)


@dataclass(frozen=True)
class SandboxCheckResult:
    ok: bool
    violations: tuple[str, ...] = field(default_factory=tuple)


class _SafetyVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".")[0]
            if root in BLOCKED_IMPORTS:
                self.violations.append(f"blocked import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        root = (node.module or "").split(".")[0]
        if root in BLOCKED_IMPORTS:
            self.violations.append(f"blocked import: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in BLOCKED_CALL_NAMES:
            self.violations.append(f"blocked call: {node.func.id}")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("__") and node.attr.endswith("__"):
            self.violations.append(f"blocked dunder attribute access: {node.attr}")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id.startswith("__") and node.id.endswith("__"):
            self.violations.append(f"blocked dunder name: {node.id}")
        self.generic_visit(node)


def check_script(source: str) -> SandboxCheckResult:
    """Parse and statically vet `source`; never executes anything."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return SandboxCheckResult(ok=False, violations=(f"syntax error: {exc}",))
    visitor = _SafetyVisitor()
    visitor.visit(tree)
    return SandboxCheckResult(ok=not visitor.violations, violations=tuple(visitor.violations))
