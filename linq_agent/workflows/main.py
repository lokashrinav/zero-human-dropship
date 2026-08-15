"""Render Workflow bridge: orchestration only; validation remains Jac-owned."""

from __future__ import annotations

import jaclang  # noqa: F401 - installs the .jac import hook
from render_sdk import Retry, Workflows

from workflow_tasks import audit_catalog_for_workflow

app = Workflows(
    default_retry=Retry(max_retries=2, wait_duration_ms=1_000, backoff_scaling=2),
    default_timeout=60,
    default_plan="starter",
)


@app.task(name="audit_catalog", timeout_seconds=60, plan="starter")
def audit_catalog(catalog_json: str) -> dict[str, object]:
    """Reject unsafe catalog replacements before Person A publishes them."""

    return audit_catalog_for_workflow(catalog_json)


if __name__ == "__main__":
    app.start()
