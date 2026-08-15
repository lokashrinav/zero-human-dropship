"""Append an entry to the agent decision log (the judges' audit trail).
Usage: python log_decision.py <AgentName> "<message>"
"""
import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()

from tools.band_tools import post_message  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    asyncio.run(post_message(sys.argv[1], " ".join(sys.argv[2:])))
    print("logged")
