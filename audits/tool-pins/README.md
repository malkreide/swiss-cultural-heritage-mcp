# Tool-Definition Pins (SEC-022)

This directory holds a hash snapshot of the server's **tool definitions** — each
tool's `name`, `description` (the prompt the LLM sees), and `input`/`output`
schema. It is a guard against a **"rug pull"**: a silently changed tool
description or schema that could re-task the LLM without the operator noticing.

## Files

- **`current.json`** — the canonical snapshot for the current `main`. Contains a
  per-tool SHA-256 and a single `manifest_sha256` over all of them.

## How it works

`tests/test_server.py::TestToolPins` recomputes the live tool hashes on every CI
run and compares them to `current.json`. **Any** change to a tool's name,
description, or schema flips a hash and fails the test — so drift cannot land
silently.

## When a tool legitimately changes

1. Make the change to the tool (name / docstring / `*Input` model / return type).
2. Regenerate the snapshot:

   ```sh
   PYTHONPATH=src python scripts/pin_tools.py
   ```

3. Commit the updated `current.json` **together with a CHANGELOG entry** that
   flags the tool change and, for a description/behaviour change, notes that
   downstream clients should **re-approve** the tool (an MCP client may have
   pinned/approved the previous description).
4. At release time, copy `current.json` to `audits/tool-pins/<version>.json` to
   keep a per-release history.

## Namespacing (deferred)

SEC-022 also suggests a `<server>__<tool>` server-identity prefix instead of the
current `heritage_` prefix. That rename is **breaking** (every tool id changes →
major version bump) and is deliberately deferred; see `docs/security.md`
("Tool-definition pinning & namespacing").
