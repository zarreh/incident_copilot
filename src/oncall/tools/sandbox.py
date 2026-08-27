"""Docker-containerized execution of AST-vetted diagnostic scripts.

Two-stage sandbox (docs/adr/d-a5-3-sandboxing.md): `oncall.tools.ast_check`
rejects unsafe constructs before a script ever reaches this module; this
module then runs the vetted script in a network-isolated, read-only,
resource-capped container so an unanticipated construct still can't escape.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from oncall.settings import Settings, get_settings
from oncall.tools.ast_check import check_script

DOCKER_IMAGE = "python:3.12-slim"


@dataclass(frozen=True)
class SandboxResult:
    ok: bool
    stdout: str
    stderr: str
    exit_code: int | None
    rejected_reason: str | None = None


def docker_available() -> bool:
    """True only if a `docker` binary is on PATH *and* its daemon responds —
    a stub binary that can't reach a daemon (e.g. Docker Desktop's WSL shim
    with no daemon running) must not be mistaken for a usable sandbox."""
    if shutil.which("docker") is None:
        return False
    try:
        proc = subprocess.run(["docker", "info"], capture_output=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def run_script(source: str, settings: Settings | None = None) -> SandboxResult:
    """AST-vet `source`, then execute it in an isolated Docker container.

    Never raises for ordinary script failures (non-zero exit, timeout) —
    only for infrastructure errors (docker missing on this host).
    """
    cfg = settings or get_settings()

    check = check_script(source)
    if not check.ok:
        return SandboxResult(
            ok=False,
            stdout="",
            stderr="",
            exit_code=None,
            rejected_reason="; ".join(check.violations),
        )

    if not docker_available():
        raise RuntimeError("docker is not available on this host")

    container_name = f"oncall-sandbox-{uuid.uuid4().hex[:12]}"
    with tempfile.TemporaryDirectory() as tmp_dir:
        script_path = Path(tmp_dir) / "script.py"
        script_path.write_text(source, encoding="utf-8")

        cmd = [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "--network=none",
            "--read-only",
            "--user",
            "1000:1000",
            "--memory",
            f"{cfg.sandbox_memory_limit_mb}m",
            "--cpu-period",
            str(cfg.sandbox_cpu_period_us),
            "--cpu-quota",
            str(cfg.sandbox_cpu_quota_us),
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=16m",
            "-v",
            f"{script_path}:/sandbox/script.py:ro",
            DOCKER_IMAGE,
            "python",
            "/sandbox/script.py",
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=cfg.sandbox_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", container_name], capture_output=True, check=False)
            return SandboxResult(
                ok=False,
                stdout="",
                stderr="",
                exit_code=None,
                rejected_reason=f"execution exceeded {cfg.sandbox_timeout_seconds}s timeout",
            )

    return SandboxResult(
        ok=proc.returncode == 0,
        stdout=proc.stdout,
        stderr=proc.stderr,
        exit_code=proc.returncode,
    )
