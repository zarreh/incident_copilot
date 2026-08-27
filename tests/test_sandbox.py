from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from oncall.tools.sandbox import docker_available, run_script


def test_rejects_blocked_import_without_docker() -> None:
    result = run_script("import os\nprint(os.getcwd())")
    assert result.ok is False
    assert result.rejected_reason is not None
    assert "os" in result.rejected_reason


def test_rejects_eval_without_docker() -> None:
    result = run_script("eval('1+1')")
    assert result.ok is False
    assert "eval" in (result.rejected_reason or "")


def test_runs_safe_script_with_mocked_docker() -> None:
    fake_proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="42\n", stderr="")
    with (
        patch("oncall.tools.sandbox.docker_available", return_value=True),
        patch("oncall.tools.sandbox.subprocess.run", return_value=fake_proc) as mock_run,
    ):
        result = run_script("print(21 * 2)")
    assert result.ok is True
    assert result.stdout == "42\n"
    mock_run.assert_called_once()


def test_nonzero_exit_is_reported_with_mocked_docker() -> None:
    fake_proc = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="Traceback...\n"
    )
    with (
        patch("oncall.tools.sandbox.docker_available", return_value=True),
        patch("oncall.tools.sandbox.subprocess.run", return_value=fake_proc),
    ):
        result = run_script("raise ValueError('boom')")
    assert result.ok is False
    assert result.exit_code == 1
    assert "Traceback" in result.stderr


def test_timeout_is_handled_with_mocked_docker() -> None:
    kill_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with (
        patch("oncall.tools.sandbox.docker_available", return_value=True),
        patch(
            "oncall.tools.sandbox.subprocess.run",
            side_effect=[subprocess.TimeoutExpired(cmd="docker", timeout=1.0), kill_result],
        ) as mock_run,
    ):
        result = run_script("while True:\n    pass")
    assert result.ok is False
    assert result.rejected_reason is not None
    assert "timeout" in result.rejected_reason
    assert mock_run.call_count == 2


def test_raises_when_docker_missing() -> None:
    with (
        patch("oncall.tools.sandbox.docker_available", return_value=False),
        pytest.raises(RuntimeError),
    ):
        run_script("print('hello')")


@pytest.mark.skipif(not docker_available(), reason="docker not installed on this host")
def test_real_docker_execution() -> None:
    result = run_script("print('hello from sandbox')")
    assert result.ok is True
    assert "hello from sandbox" in result.stdout
