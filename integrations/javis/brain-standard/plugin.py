"""Javis OS plugin for a Brain_Standard 4.0 brain.

1. Exposes the brain commands as tools for every Javis engine, including API engines without a shell.
   Each tool runs the brain package of the repository (`python -m brain`), so the rules live in one place.
   Capture: brain_capture (the owner's words), brain_submit (facts through G1).
   Follow up: brain_assigned, brain_report. There is no tool for `brain assign`: only the owner assigns.
2. A pre_tool_call hook that applies the brain's write guard (brain.guard.block_reason).

Point the brain in Javis at the repository root (the folder that holds brain.toml). Standard library only.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CONFIG_FILE = "brain.toml"
PACKAGE_DIR = Path("tools")
ROOT_ENV = "BRAIN_ROOT"


def find_root(vault_root) -> Path | None:
    """The brain root: $BRAIN_ROOT, or the nearest folder above the Javis vault that holds brain.toml."""
    chosen = os.environ.get(ROOT_ENV)
    if chosen and (Path(chosen) / CONFIG_FILE).is_file():
        return Path(chosen).resolve()
    if not vault_root:
        return None
    here = Path(vault_root).resolve()
    for p in [here, *here.parents]:
        if (p / CONFIG_FILE).is_file() and (p / PACKAGE_DIR / "brain").is_dir():
            return p
    return None


def brain_package(root: Path):
    """Import the brain package of this repository.

    Javis is one long-running process that may serve several brains. When the package already imported
    comes from another repository, drop it and import this one, so each brain runs its own rules.
    """
    package = (root / PACKAGE_DIR).resolve()
    loaded = sys.modules.get("brain")
    if loaded is not None and Path(loaded.__file__).resolve().parent.parent != package:
        for name in [n for n in sys.modules if n == "brain" or n.startswith("brain.")]:
            del sys.modules[name]
    if str(package) not in sys.path:
        sys.path.insert(0, str(package))
    import brain
    import brain.config
    import brain.guard
    return brain


def load_brain(root: Path):
    """Open the brain at root with its own package."""
    return brain_package(root).config.open_brain(root)


def run(ctx, *args: str) -> str:
    root = find_root(getattr(ctx, "vault_root", None))
    if root is None:
        return (f"ERROR: the brain selected in Javis is not a Brain_Standard repository (no {CONFIG_FILE}). "
                f"Point the brain at the repository root, or set {ROOT_ENV}.")
    plugin_cfg = load_brain(root).assistant["plugin"]
    env = {**os.environ, "PYTHONPATH": str(root / PACKAGE_DIR)}
    try:
        r = subprocess.run([sys.executable, "-m", "brain", "--root", str(root), *args], cwd=str(root), env=env,
                           capture_output=True, text=True, encoding="utf-8", timeout=plugin_cfg["timeout_seconds"])
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"ERROR: could not run brain: {type(e).__name__}: {e}"
    out = "\n".join(s for s in (r.stdout.strip(), r.stderr.strip()) if s)
    return f"[exit code {r.returncode}]\n{out}" if r.returncode else out


def _level(ctx, args) -> list[str]:
    level = str((args or {}).get("max_level") or "").strip()
    root = find_root(getattr(ctx, "vault_root", None))
    levels = load_brain(root).assistant["levels"] if root else []
    return ["--level", level] if level in levels else []


# ---------------------------------------------------------------- tools

def tool_capture(args, ctx):
    args = args or {}
    text = str(args.get("text") or "").strip()
    if not text:
        return "ERROR: 'text' is required: the owner's words, verbatim."
    root = find_root(getattr(ctx, "vault_root", None))
    channel = str(args.get("channel") or "").strip()
    if not channel and root:
        channel = load_brain(root).assistant["plugin"]["default_channel"]
    return run(ctx, "capture", text, *(["--channel", channel] if channel else []))


def tool_submit(args, ctx):
    """Submit through G1, from 'record' (the source record as text) or 'file' (a path).

    With 'record' the plugin writes the record to a temporary folder OUTSIDE the vault and submits it,
    so a run at level suggest (no file writes) can still submit facts through G1.
    """
    args = args or {}
    record = str(args.get("record") or "")
    if record.strip():
        name = re.sub(r"[^\w-]+", "-", str(args.get("name") or "record")).strip("-")[:60] or "record"
        with tempfile.TemporaryDirectory(prefix="brain-submit-") as tmp:
            p = Path(tmp) / f"{name}.md"
            p.write_text(record, encoding="utf-8", newline="\n")
            return run(ctx, "submit", str(p))
    file = str(args.get("file") or "").strip()
    if not file:
        return "ERROR: give 'record' (the source record as text) or 'file' (path to a source record .md)."
    p = Path(file)
    if not p.is_absolute() and getattr(ctx, "vault_root", None):
        p = Path(ctx.vault_root) / p
    return run(ctx, "submit", str(p))


def tool_check(args, ctx):
    return run(ctx, "check")


def tool_turn(args, ctx):
    args = args or {}
    kind, summary = str(args.get("type") or "").strip(), str(args.get("summary") or "").strip()
    if not kind or not summary:
        return "ERROR: 'type' (task, idea, file, drop) and 'summary' are required."
    return run(ctx, "turn", kind, summary)


def tool_weekly(args, ctx):
    return run(ctx, "weekly")


def tool_assigned(args, ctx):
    return run(ctx, "assigned", *_level(ctx, args))


def tool_report(args, ctx):
    args = args or {}
    try:
        number = int(args.get("number"))
    except (TypeError, ValueError):
        return "ERROR: 'number' must be the position from brain_assigned."
    result = str(args.get("result") or "").strip()
    if not result:
        return "ERROR: 'result' is required: what was done and where the result is."
    return run(ctx, "report", str(number), result, *_level(ctx, args))


# ---------------------------------------------------------------- hook

def block_reason(tool_name: str, args: dict, vault_root) -> str | None:
    root = find_root(vault_root)
    if root is None:
        return None
    package = brain_package(root)
    return package.guard.block_reason(package.config.open_brain(root), tool_name, args or {}, vault_root)


def pre_tool_call(tool_name=None, args=None, vault_root=None, **kwargs):
    reason = block_reason(tool_name, args or {}, vault_root)
    return {"deny": f"Brain: {reason}"} if reason else None


# ---------------------------------------------------------------- registration

LEVEL_SCHEMA = {"type": "string", "description": "level of this run: suggest, auto or full"}


def register(ctx):
    ctx.register_tool(
        name="brain_capture",
        description=("Write the owner's words to the Inbox, verbatim (a Telegram message, voice, typing). Use it for "
                     "messages starting with 'capture:'. Not for facts you looked up: those go through brain_submit."),
        handler=tool_capture, min_mode="safe",
        schema={"type": "object",
                "properties": {"text": {"type": "string", "description": "The owner's words"},
                               "channel": {"type": "string", "description": "telegram, voice, zalo…"}},
                "required": ["text"]},
    )
    ctx.register_tool(
        name="brain_submit",
        description=("Submit one claim you looked up through gate G1. Pass 'record': the whole source record "
                     "(frontmatter source, retrieved, archived, grade A–F + 1–6, verification, following "
                     "vault/_templates/source-record.md), then a heading with the claim. One claim per call. "
                     "Never invent a grade. Pass 'file' instead when the record is already in a file."),
        # Read-only on purpose: the record goes to a temporary folder outside the vault, and the only write
        # to the brain is the CLI's own, after G1. Runs at level suggest need it to submit what they found.
        handler=tool_submit, min_mode="readonly",
        schema={"type": "object",
                "properties": {"record": {"type": "string", "description": "Source record: frontmatter, then the claim"},
                               "name": {"type": "string", "description": "Short name, for example printer-price"},
                               "file": {"type": "string", "description": "Path to an existing source record"}}},
    )
    ctx.register_tool(
        name="brain_check",
        description="Check the vault against the brain's rules and trust gates. Read-only.",
        handler=tool_check, min_mode="readonly",
        schema={"type": "object", "properties": {}},
    )
    ctx.register_tool(
        name="brain_turn",
        description="Close a turn. If the vault has errors the turn does not close: run brain_check, fix, retry.",
        handler=tool_turn, min_mode="safe",
        schema={"type": "object",
                "properties": {"type": {"type": "string", "description": "task, idea, file or drop ([turn] types)"},
                               "summary": {"type": "string", "description": "One-line summary"}},
                "required": ["type", "summary"]},
    )
    ctx.register_tool(
        name="brain_weekly",
        description="Weekly Review metrics. Read-only; the owner saves them with brain weekly --save.",
        handler=tool_weekly, min_mode="readonly",
        schema={"type": "object", "properties": {}},
    )
    ctx.register_tool(
        name="brain_assigned",
        description=("Next actions the owner assigned to you (@javis:<level>), with their position and level. "
                     "Work only on tasks in this list. max_level = the level of this run."),
        handler=tool_assigned, min_mode="readonly",
        schema={"type": "object", "properties": {"max_level": LEVEL_SCHEMA}},
    )
    ctx.register_tool(
        name="brain_report",
        description=("Report an assigned task done: it is checked off and the result goes to the Inbox for the owner "
                     "to clarify. 'number' is the position from brain_assigned, called with the same max_level. "
                     "Facts you looked up must already be submitted with brain_submit."),
        # Read-only on purpose: the only write is the CLI's own bookkeeping, so runs at level suggest can report.
        handler=tool_report, min_mode="readonly",
        schema={"type": "object",
                "properties": {"number": {"type": "integer"},
                               "result": {"type": "string", "description": "What was done, where the result is"},
                               "max_level": LEVEL_SCHEMA},
                "required": ["number", "result"]},
    )
    ctx.register_hook("pre_tool_call", pre_tool_call)
