#!/usr/bin/env python3
"""Generate the tool-definition hash pin (SEC-022).

Run after any intentional change to a tool's name, description, or schema:

    PYTHONPATH=src python scripts/pin_tools.py

Then commit the updated ``audits/tool-pins/current.json`` together with a
CHANGELOG note (re-approval prompt) describing what changed and why.
"""

from __future__ import annotations

import json
import pathlib
import tomllib

from swiss_cultural_heritage_mcp._toolpins import compute_tool_pins
from swiss_cultural_heritage_mcp.server import mcp

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "audits" / "tool-pins" / "current.json"


def _declared_version() -> str:
    """Read the version from ``pyproject.toml``, not installed metadata.

    ``importlib.metadata.version()`` was used here and returned
    ``0.0.0+local`` whenever the package was not installed — the documented way
    to run this script is ``PYTHONPATH=src``, which is exactly that case. So the
    field either recorded a placeholder or silently lagged behind, depending on
    what happened to be installed in the caller's environment. Reading
    ``pyproject.toml`` makes the output deterministic and lets a test compare
    the field without being environment-dependent.
    """
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    return data["project"]["version"]


def main() -> None:
    pins = compute_tool_pins(mcp)
    payload = {"generated_for_version": _declared_version(), **pins}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(
        f"wrote {OUT.relative_to(OUT.parents[2])} — {pins['tool_count']} tools, "
        f"manifest {pins['manifest_sha256'][:12]}…"
    )


if __name__ == "__main__":
    main()
