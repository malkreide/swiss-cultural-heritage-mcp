"""Tool-definition hash pinning (SEC-022).

Computes a deterministic SHA-256 over each registered tool's identity —
``name`` + ``description`` + ``inputSchema`` + ``outputSchema`` — plus a single
manifest hash over all of them. A committed snapshot (``audits/tool-pins/
current.json``) lets a test detect any silent change to a tool's name, prompt
text, or schema ("rug pull" / definition drift) and force a conscious update
with a CHANGELOG re-approval note.

The same function powers both ``scripts/pin_tools.py`` (writes the snapshot) and
the drift test, so they can never diverge.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


async def compute_tool_pins(mcp: Any) -> dict:
    """Return ``{"tool_count", "manifest_sha256", "tools": {name: sha256}}``.

    Deterministic across environments: tools are sorted by name and every nested
    structure is serialised with sorted keys, so the manifest hash depends only
    on the tool definitions themselves.
    """
    tools = await mcp.list_tools()
    pins: dict[str, str] = {}
    for tool in sorted(tools, key=lambda t: t.name):
        identity = _canonical({
            "name":         tool.name,
            "description":  tool.description or "",
            "inputSchema":  tool.inputSchema,
            "outputSchema": tool.outputSchema,
        })
        pins[tool.name] = hashlib.sha256(identity.encode("utf-8")).hexdigest()

    manifest = hashlib.sha256(_canonical(pins).encode("utf-8")).hexdigest()
    return {"tool_count": len(pins), "manifest_sha256": manifest, "tools": pins}
