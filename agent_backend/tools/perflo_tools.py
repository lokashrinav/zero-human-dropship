"""Perflo — the agents' money. Pay-per-use x402 services under a human-armed
spend cap. This is load-bearing for the creative pipeline: with no Replicate
key, the ONLY way Growth gets ad creatives/product images is by PAYING an
x402 vendor per call through the Perflo balance.

Human one-time setup (agents cannot do this by design):
    npx -y @perflo/cli onboard     # connect + install skill
    (fund a small balance + arm spend cap/allowlist in the Perflo dashboard)

CLI:  python -m tools.perflo_tools task "generate a studio product photo of ..."
      python -m tools.perflo_tools balance
Docs: https://docs.perflo.ai
"""
import json
import subprocess
import sys

CLI = ["npx", "-y", "@perflo/cli", "--json"]


class PerfloNotConnected(RuntimeError):
    pass


def _run(*args: str, timeout: int = 300) -> dict:
    proc = subprocess.run(
        CLI + list(args),
        capture_output=True, text=True, timeout=timeout, shell=(sys.platform == "win32"),
    )
    out = proc.stdout.strip() or proc.stderr.strip()
    try:
        data = json.loads(out.splitlines()[-1]) if out else {}
    except json.JSONDecodeError:
        data = {"ok": False, "raw": out[:800]}
    if isinstance(data, dict) and data.get("connected") is False:
        raise PerfloNotConnected("Perflo not connected — human must run: npx -y @perflo/cli onboard")
    return data


def status() -> dict:
    return _run("status")


def balance() -> dict:
    """Agent spending money + portfolio. Judges see the balance move per paid call."""
    return _run("balance")


def do_task(query: str, max_price_usd: float | None = None) -> dict:
    """Run a task through Perflo: backend picks the best-fit x402 vendor and PAYS
    for the call from the agent balance (inside the human-armed cap). The result
    exists only because the payment cleared — that is the point."""
    args = ["do-task", query]
    if max_price_usd is not None:
        args += ["--max-price", str(max_price_usd)]
    return _run(*args, timeout=600)


def get_result(result_id: str) -> dict:
    """Fetch a slow task's result by id."""
    return _run("get-result", result_id)


def find_vendor(capability: str) -> dict:
    """Ranked vendors for a capability (e.g. 'image generation'). No charge."""
    return _run("best-vendor", capability)


def check_contract(url: str) -> dict:
    """Exact pay contract for a service before paying. No charge."""
    return _run("check", url)


def buy_creative(product_name: str, style: str = "clean studio product photo, white background") -> dict:
    """Growth agent's creative pipeline: pay an x402 image vendor per creative."""
    return do_task(
        f"Generate a single square e-commerce product image: {style} of {product_name}. "
        "No text, no logos, no people. Return the image URL."
    )


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if cmd == "task" and len(sys.argv) > 2:
            print(json.dumps(do_task(" ".join(sys.argv[2:])), indent=2)[:4000])
        elif cmd == "balance":
            print(json.dumps(balance(), indent=2)[:2000])
        elif cmd == "status":
            print(json.dumps(status(), indent=2)[:2000])
        elif cmd == "vendor" and len(sys.argv) > 2:
            print(json.dumps(find_vendor(" ".join(sys.argv[2:])), indent=2)[:3000])
        else:
            print(__doc__)
            sys.exit(2)
    except PerfloNotConnected as exc:
        print(f"BLOCKED: {exc}")
        sys.exit(3)
