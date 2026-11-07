"""The brain's tools for any agent platform: one definition, used by every integration.

Each tool maps to one `brain` command, run in a separate process with BRAIN_ACTOR=agent, so the CLI applies the same
rules to every platform: an agent cannot assign itself work, and a fact it brings in must pass gate G1. The MCP server
(integrations/mcp), the Javis OS plugin (integrations/javis) and any future adapter only translate these definitions
into their platform's format.

min_mode follows the assistant levels: "readonly" tools may run at level suggest (their only write is the CLI's own,
after its checks); "safe" tools write to the brain and need level auto or above.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PACKAGE_DIR = "tools"
TIMEOUT_SECONDS = 120
RECORD_FIELDS = ("source", "original_source", "author", "published", "retrieved", "valid_until", "archived", "hash",
                 "grade", "verification")
LEVEL = {"type": "string", "description": "the permission level of this run: suggest, auto or full"}


def _s(args: dict, key: str) -> str:
    return str((args or {}).get(key) or "").strip()


def _need(args: dict, *keys: str) -> str | None:
    missing = [k for k in keys if not _s(args, k)]
    return f"ERROR: {', '.join(repr(k) for k in missing)} required." if missing else None


def _level(args: dict) -> list[str]:
    return ["--level", _s(args, "max_level")] if _s(args, "max_level") else []


def record_text(args: dict) -> str | None:
    """The source record for brain submit: given whole as 'record', or built from 'claim' and the record fields."""
    if _s(args, "record"):
        return str(args["record"])
    if not _s(args, "claim"):
        return None
    head = "".join(f"{k}: \"{_s(args, k)}\"\n" for k in RECORD_FIELDS if _s(args, k))
    return f"---\n{head}---\n\n# {_s(args, 'claim')}\n"


def _recall(a):
    if (err := _need(a, "question")):
        return err
    return ["kg", "ask", _s(a, "question")] + (["--max", _s(a, "max_facts")] if _s(a, "max_facts") else [])


def _remember(a):
    if not (_s(a, "owner_said") or _s(a, "summary")):
        return "ERROR: give 'owner_said' (the owner's message, verbatim) and/or 'summary' (one line on what was done)."
    argv = ["kg", "remember"]
    for key, flag in (("owner_said", "--prompt"), ("summary", "--summary"), ("session", "--session")):
        if _s(a, key):
            argv += [flag, _s(a, key)]
    return argv


def _capture(a):
    if (err := _need(a, "text")):
        return err
    return ["capture", _s(a, "text")] + (["--channel", _s(a, "channel")] if _s(a, "channel") else [])


def _turn(a):
    if (err := _need(a, "type", "summary")):
        return err
    return ["turn", _s(a, "type"), _s(a, "summary")]


def _report(a):
    if (err := _need(a, "number", "result")):
        return err
    return ["report", _s(a, "number"), _s(a, "result")] + _level(a)


TOOLS = [
    {"name": "brain_recall", "min_mode": "readonly", "argv": _recall,
     "description": ("Read the brain's knowledge graph before answering: the facts it already holds about a question, "
                     "each with its source and trust (owner = the owner's own notes or words; a grade such as B2 = an "
                     "agent fact that passed G1; unverified and agent = leads to check). Call it first on every request."),
     "schema": {"type": "object", "properties": {"question": {"type": "string"},
                                                 "max_facts": {"type": "string", "description": "default 15"}},
                "required": ["question"]}},
    {"name": "brain_remember", "min_mode": "safe", "argv": _remember,
     "description": ("After answering, fold the conversation into the knowledge graph: the owner's message verbatim "
                     "and a one-line summary of what was done. Never pass your own claims as the owner's words; facts "
                     "you looked up go through brain_submit."),
     "schema": {"type": "object", "properties": {"owner_said": {"type": "string"}, "summary": {"type": "string"},
                                                 "session": {"type": "string", "description": "conversation id"}}}},
    {"name": "brain_capture", "min_mode": "safe", "argv": _capture,
     "description": ("Write the owner's words to the Inbox, verbatim (a chat message, voice, typing), for example "
                     "messages starting with 'capture:'. Not for facts you looked up: those go through brain_submit."),
     "schema": {"type": "object", "properties": {"text": {"type": "string", "description": "the owner's words"},
                                                 "channel": {"type": "string", "description": "telegram, voice, slack…"}},
                "required": ["text"]}},
    # Read-only on purpose: the record goes to a temporary folder outside the vault, and the only write to the brain
    # is the CLI's own, after G1, so runs at level suggest can submit what they found.
    {"name": "brain_submit", "min_mode": "readonly", "argv": None,
     "description": ("Submit one claim you looked up through gate G1, with its source record: 'claim' plus source, "
                     "retrieved (YYYY-MM-DD), archived, grade (source A–F + credibility 1–6, e.g. B2) and verification; "
                     "or the whole record as 'record' (vault/_templates/source-record.md), or 'file' when the record "
                     "is already in a file. One claim per call. Never invent a grade; if you could not check it, grade "
                     "it low."),
     "schema": {"type": "object", "properties": {"claim": {"type": "string"}, "record": {"type": "string"},
                                                 "name": {"type": "string", "description": "short name, e.g. printer-price"},
                                                 "file": {"type": "string"},
                                                 **{k: {"type": "string"} for k in RECORD_FIELDS}}}},
    {"name": "brain_check", "min_mode": "readonly", "argv": lambda a: ["check"],
     "description": "Check the vault against the brain's rules and trust gates (brain check).",
     "schema": {"type": "object", "properties": {}}},
    {"name": "brain_suggest", "min_mode": "readonly", "argv": lambda a: ["kg", "suggest"],
     "description": ("Gaps the knowledge graph sees: notes to link, notes worth writing, facts to verify. Suggestions "
                     "only; the owner decides (docs/design-suggestions.md)."),
     "schema": {"type": "object", "properties": {}}},
    {"name": "brain_turn", "min_mode": "safe", "argv": _turn,
     "description": "Close a turn. If the vault has errors the turn does not close: run brain_check, fix, retry.",
     "schema": {"type": "object", "properties": {"type": {"type": "string", "enum": ["task", "idea", "file", "drop"]},
                                                 "summary": {"type": "string"}},
                "required": ["type", "summary"]}},
    {"name": "brain_weekly", "min_mode": "readonly", "argv": lambda a: ["weekly"],
     "description": "Weekly Review metrics (not saved; the owner saves them with brain weekly --save).",
     "schema": {"type": "object", "properties": {}}},
    {"name": "brain_assigned", "min_mode": "readonly", "argv": lambda a: ["assigned"] + _level(a),
     "description": ("Next actions the owner assigned to the assistant (@agent:<level>), with their position and "
                     "level. Work only on tasks in this list, never above their level."),
     "schema": {"type": "object", "properties": {"max_level": LEVEL}}},
    # Read-only on purpose: the only write is the CLI's own bookkeeping, so runs at level suggest can report.
    {"name": "brain_report", "min_mode": "readonly", "argv": _report,
     "description": ("Report an assigned task done: it is checked off and the result goes to the Inbox for the owner "
                     "to clarify. 'number' is the position from brain_assigned, called with the same max_level. Facts "
                     "in the result must already be submitted with brain_submit."),
     "schema": {"type": "object", "properties": {"number": {"type": "string"}, "result": {"type": "string"},
                                                 "max_level": LEVEL},
                "required": ["number", "result"]}},
]
BY_NAME = {t["name"]: t for t in TOOLS}


def locate(start=None) -> tuple[Path, Path] | None:
    """(repository, brain) for a run. The brain is BRAIN_ROOT when set, else the first folder up from start holding
    brain.toml; the repository is the first folder up from the brain holding tools/brain."""
    chosen = os.environ.get("BRAIN_ROOT")
    if chosen and (Path(chosen) / "brain.toml").is_file():
        home = Path(chosen).resolve()
    elif start:
        here = Path(start).resolve()
        home = next((p for p in [here, *here.parents] if (p / "brain.toml").is_file()), None)
        if home is None:
            return None
    else:
        return None
    root = next((p for p in [home, *home.parents] if (p / PACKAGE_DIR / "brain").is_dir()), None)
    return (root, home) if root else None


def run(root: Path, argv: list[str], home: Path | None = None) -> str:
    """Run one brain command as an agent."""
    env = {**os.environ, "BRAIN_ACTOR": "agent", "PYTHONPATH": str(Path(root) / PACKAGE_DIR)}
    try:
        r = subprocess.run([sys.executable, "-m", "brain", "--root", str(home or root), *argv], cwd=str(root), env=env,
                           capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"ERROR: could not run brain: {type(e).__name__}: {e}"
    out = "\n".join(s for s in (r.stdout.strip(), r.stderr.strip()) if s)
    return f"[exit code {r.returncode}]\n{out}" if r.returncode else out


def call(root: Path, name: str, args: dict | None = None, home: Path | None = None) -> str:
    tool = BY_NAME.get(name)
    if tool is None:
        return f"ERROR: unknown tool {name}"
    args = args or {}
    if name == "brain_submit":
        text = record_text(args)
        if text is None and _s(args, "file"):
            f = Path(_s(args, "file"))
            return run(root, ["submit", str(f if f.is_absolute() else Path(home or root) / f)], home)
        if text is None:
            return "ERROR: give 'claim' with the record fields, the whole 'record', or a 'file'."
        slug = re.sub(r"[^\w-]+", "-", _s(args, "name") or _s(args, "claim") or "record").strip("-")[:60] or "record"
        with tempfile.TemporaryDirectory(prefix="brain-submit-") as tmp:   # outside the vault
            p = Path(tmp) / f"{slug}.md"
            p.write_text(text, encoding="utf-8", newline="\n")
            return run(root, ["submit", str(p)], home)
    argv = tool["argv"](args)
    return argv if isinstance(argv, str) else run(root, argv, home)


def allowed(tool: dict, mode: str) -> bool:
    """Is a tool allowed in a run at this mode (readonly < safe)?"""
    return mode != "readonly" or tool["min_mode"] == "readonly"
