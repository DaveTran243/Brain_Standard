#!/usr/bin/env python3
"""The brain as an MCP server (stdio), for every agent platform that speaks the Model Context Protocol.

Claude Desktop and Claude Code, Codex, Gemini CLI, Cursor, Windsurf, Kiro, Cline, Goose, OpenClaw, Hermes Agent,
Javis OS's MCP hub and others start this script as a subprocess and call its tools. The tools are the brain's shared
agent tools (tools/brain/agent_tools.py): recall from the knowledge graph, remember a turn, capture the owner's words,
submit facts through G1, take and report assigned work. Every call runs the brain CLI with BRAIN_ACTOR=agent, so the
rules are the same as everywhere else; there is no tool to assign work.

    python integrations/mcp/brain_mcp.py [--root <brain>] [--read-only]

--root      the brain folder holding brain.toml (default: BRAIN_ROOT, else the repository this script lives in)
--read-only list only the tools a level-suggest run may use (recall, submit, check, suggest, weekly, assigned,
            report)

Newline-delimited JSON-RPC 2.0 on stdin/stdout, as the MCP stdio transport specifies. Standard library only.
Logs go to stderr; stdout carries protocol messages only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

from brain import agent_tools  # noqa: E402
from brain.config import defaults  # noqa: E402

__version__ = defaults()["brain"]["version"]

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
INSTRUCTIONS = ("A second brain (Brain_Standard). Before answering, call brain_recall with the request to read what "
                "the brain already holds. The owner's words go in verbatim through brain_capture; facts you looked up "
                "go through brain_submit with a source record (gate G1). After answering, call brain_remember with the "
                "owner's message and a one-line summary, and close the turn with brain_turn. Only the owner assigns "
                "work: follow up only on tasks brain_assigned lists, never above their level.")


class Server:
    def __init__(self, root: Path, home: Path, read_only: bool = False):
        self.root, self.home = root, home
        self.mode = "readonly" if read_only else "safe"
        self.tools = [t for t in agent_tools.TOOLS if agent_tools.allowed(t, self.mode)]

    def handle(self, msg: dict) -> dict | None:
        """One JSON-RPC message in, one response out (None for a notification)."""
        method, mid = msg.get("method"), msg.get("id")
        if mid is None:   # notifications/initialized, notifications/cancelled…: nothing to answer
            return None
        try:
            result = self.dispatch(method, msg.get("params") or {})
        except KeyError as e:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Method not found: {e}"}}
        except (TypeError, ValueError) as e:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"Invalid params: {e}"}}
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def dispatch(self, method: str, params: dict) -> dict:
        if method == "initialize":
            asked = params.get("protocolVersion")
            return {"protocolVersion": asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "brain-standard", "version": __version__},
                    "instructions": INSTRUCTIONS}
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [{"name": t["name"], "description": t["description"], "inputSchema": t["schema"],
                               "annotations": {"readOnlyHint": t["min_mode"] == "readonly"}} for t in self.tools]}
        if method == "tools/call":
            name = params.get("name")
            if name not in {t["name"] for t in self.tools}:
                return {"content": [{"type": "text", "text": f"Unknown tool or not allowed here: {name}"}],
                        "isError": True}
            text = agent_tools.call(self.root, name, params.get("arguments") or {}, self.home)
            failed = text.startswith(("ERROR", "[exit code"))
            return {"content": [{"type": "text", "text": text}], "isError": failed}
        raise KeyError(method)

    def serve(self, stdin=sys.stdin, stdout=sys.stdout) -> None:
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
            else:
                batch = msg if isinstance(msg, list) else [msg]
                replies = [r for r in (self.handle(m) for m in batch if isinstance(m, dict)) if r]
                reply = replies if isinstance(msg, list) else (replies[0] if replies else None)
            if reply:
                stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
                stdout.flush()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="The brain as an MCP server (stdio).")
    p.add_argument("--root", help="the brain folder holding brain.toml (default: BRAIN_ROOT, else this repository)")
    p.add_argument("--read-only", action="store_true", help="only the tools a level-suggest run may use")
    a = p.parse_args(argv)
    if a.root:
        os.environ["BRAIN_ROOT"] = str(Path(a.root).resolve())
    found = agent_tools.locate(REPO)
    if found is None:
        print(f"brain_mcp: no brain.toml at {a.root or REPO}", file=sys.stderr)
        return 2
    for stream in (sys.stdin, sys.stdout):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    root, home = found
    print(f"brain_mcp: serving {home}" + (" (read-only)" if a.read_only else ""), file=sys.stderr)
    Server(root, home, a.read_only).serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
