# Render Workflow

This optional workflow is a real preflight gate for catalog replacements. Its Python function exists only because Render Workflows currently registers Python or TypeScript tasks. The task invokes `audit_catalog_for_workflow` from `workflow_tasks.jac`; all validation remains Jac-owned.

- Build command: `jac install`
- Start command: `.jac/venv/bin/python workflows/main.py`
- Registered task: `audit_catalog`
- Input: `{"catalog_json":"[...]"}` or a positional JSON string, depending on the Render trigger client
- Output: only validation status, product counts, and catalog hash; never product cost, payment URLs, or secrets

Render Blueprints do not currently provision Workflow services. Create the Workflow once in the Render dashboard from this same repository/service root and use the official `jaseci/jaclang:0.34.7` Docker image/Dockerfile.
