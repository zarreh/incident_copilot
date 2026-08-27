from __future__ import annotations

from oncall.tools.ast_check import check_script


def test_allows_safe_script() -> None:
    result = check_script("total = sum(x for x in range(10))\nprint(total)")
    assert result.ok is True
    assert result.violations == ()


def test_blocks_os_import() -> None:
    result = check_script("import os\nos.system('ls')")
    assert result.ok is False
    assert any("os" in v for v in result.violations)


def test_blocks_from_import() -> None:
    result = check_script("from subprocess import run\nrun(['ls'])")
    assert result.ok is False
    assert any("subprocess" in v for v in result.violations)


def test_blocks_eval() -> None:
    result = check_script("eval('1 + 1')")
    assert result.ok is False
    assert any("eval" in v for v in result.violations)


def test_blocks_dunder_attribute_escape() -> None:
    result = check_script("().__class__.__bases__[0].__subclasses__()")
    assert result.ok is False
    assert result.violations


def test_blocks_dunder_builtins_name() -> None:
    result = check_script("print(__builtins__)")
    assert result.ok is False
    assert any("__builtins__" in v for v in result.violations)


def test_reports_syntax_error() -> None:
    result = check_script("def broken(:\n    pass")
    assert result.ok is False
    assert any("syntax error" in v for v in result.violations)
