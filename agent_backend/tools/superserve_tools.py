"""Superserve sandboxes — run agent workloads in an isolated, pausable microVM.

The CEO delegates heavy/risky work (sourcing runs, fulfillment scripts) into a
long-lived sandbox that pauses between cycles (full VM checkpoint, compute
billing stops) and resumes with processes and filesystem intact.

CLI:  python -m tools.superserve_tools "python -m agents.sourcing 'phone stand'"
Docs: https://docs.superserve.ai/quickstart
"""
import json
import os
import sys
from pathlib import Path

SANDBOX_STATE = Path(__file__).resolve().parent.parent / ".superserve_sandbox.json"
BACKEND_DIR = Path(__file__).resolve().parent.parent
REMOTE_DIR = "/app"
TEMPLATE = "superserve/python-3.11"

UPLOAD_GLOBS = ["*.py", "requirements.txt", "agents/*.py", "tools/*.py"]
AGENT_ENV_KEYS = [
    "STRIPE_SECRET_KEY", "CJ_API_KEY", "CJ_EMAIL", "PIONEER_API_KEY",
    "PIONEER_BASE_URL", "REPLICATE_API_TOKEN", "TERAC_API_KEY", "BACKEND_URL",
]


def _require_sdk():
    if not os.getenv("SUPERSERVE_API_KEY"):
        raise RuntimeError("SUPERSERVE_API_KEY is not configured")
    from superserve import Sandbox
    return Sandbox


def get_or_create_sandbox():
    """Reuse the business sandbox if it exists (auto-resumes on connect), else create."""
    Sandbox = _require_sdk()

    if SANDBOX_STATE.exists():
        sandbox_id = json.loads(SANDBOX_STATE.read_text())["id"]
        try:
            return Sandbox.connect(sandbox_id), False
        except Exception:
            pass  # deleted or expired; create fresh

    env_vars = {k: os.getenv(k, "") for k in AGENT_ENV_KEYS if os.getenv(k)}
    sandbox = Sandbox.create(
        name="dropship-agents",
        from_template=TEMPLATE,
        env_vars=env_vars,
        timeout_seconds=3600,
        auto_delete_seconds=86400,
    )
    SANDBOX_STATE.write_text(json.dumps({"id": sandbox.id}))
    _sync_code(sandbox)
    result = sandbox.commands.run(
        f"pip install -r {REMOTE_DIR}/requirements.txt", timeout_seconds=600
    )
    if result.exit_code != 0:
        raise RuntimeError(f"sandbox pip install failed: {result.stderr[:500]}")
    return sandbox, True


def _sync_code(sandbox):
    for pattern in UPLOAD_GLOBS:
        for path in BACKEND_DIR.glob(pattern):
            if path.is_file():
                rel = path.relative_to(BACKEND_DIR).as_posix()
                sandbox.files.write(f"{REMOTE_DIR}/{rel}", path.read_text(encoding="utf-8"))


def run_agent_task(command: str, timeout_seconds: int = 300, pause_after: bool = True) -> dict:
    """Run one agent command inside the sandbox, then pause it (stops compute billing)."""
    sandbox, created = get_or_create_sandbox()
    if not created:
        _sync_code(sandbox)  # pick up local code changes on reuse
    result = sandbox.commands.run(
        command, working_dir=REMOTE_DIR, timeout_seconds=timeout_seconds
    )
    if pause_after:
        try:
            sandbox.pause()
        except Exception:
            pass
    return {
        "sandbox_id": sandbox.id,
        "sandbox_created": created,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    out = run_agent_task(" ".join(sys.argv[1:]))
    print(json.dumps({k: v for k, v in out.items() if k != "stdout"}, indent=2))
    print(out["stdout"])
    sys.exit(out["exit_code"])
