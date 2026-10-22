#!/usr/bin/env python3
"""Claude Code PreToolUse hook: the same write guard as the Javis plugin (brain.guard).

Claude Code writes files with its own Write and Edit tools, which never pass through the Javis
MCP Hub, so the plugin hook cannot see them. This script reads the hook event as JSON on stdin;
exit code 2 with a reason on stderr stops Claude Code from writing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from brain import guard  # noqa: E402
from brain.config import BrainError, find_root, open_brain  # noqa: E402


def hook_args(tool_input: dict) -> dict:
    """Translate Claude Code tool input to the arguments the guard reads."""
    args = {"path": tool_input.get("file_path") or tool_input.get("notebook_path") or ""}
    if "content" in tool_input:
        args["content"] = tool_input["content"]
    else:
        edits = tool_input.get("edits") or [tool_input]
        args["old_string"] = "\n".join(str(e.get("old_string") or "") for e in edits)
        args["new_string"] = "\n".join(str(e.get("new_string") or "") for e in edits)
    return args


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    cwd = event.get("cwd") or "."
    try:
        brain = open_brain(find_root(Path(cwd)) or ROOT)
    except BrainError:
        return 0
    reason = guard.block_reason(brain, str(event.get("tool_name") or ""), hook_args(event.get("tool_input") or {}), cwd)
    if reason:
        print(f"Brain: {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
