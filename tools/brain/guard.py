"""Write guard shared by the Javis plugin hook and the Claude Code hook.

It stops an AI from writing where only the owner, or only a brain command, may write:
protected folders (permanent notes, agent items), templates and logs, and adding or raising
an assignment label in Next Actions. Everything it needs comes from [assistant.guard].
"""
from __future__ import annotations

from pathlib import Path

from . import notes
from .assistant import label_re
from .config import Brain


def _label_counts(text: str, brain: Brain) -> dict[str, int]:
    counts: dict[str, int] = {}
    for m in label_re(brain).finditer(text or ""):
        counts[m.group(1) or ""] = counts.get(m.group(1) or "", 0) + 1
    return counts


def adds_label(old: str, new: str, brain: Brain) -> bool:
    """True when new text has more labels at some level than old text: a new or raised assignment."""
    before, after = _label_counts(old, brain), _label_counts(new, brain)
    return any(after[k] > before.get(k, 0) for k in after)


def block_reason(brain: Brain, tool: str, args: dict, cwd: str | Path | None = None) -> str | None:
    """Why this file write must be blocked, or None to let it through."""
    guard = brain.assistant["guard"]
    if str(tool or "").rsplit("__", 1)[-1] not in guard["write_tools"]:
        return None
    target = str(args.get("path") or args.get("file_path") or args.get("notebook_path") or "").strip()
    if not target:
        return None
    p = Path(target)
    if not p.is_absolute():
        p = Path(cwd or brain.root) / p
    p = p.resolve()
    vault = brain.vault.resolve()
    if not p.is_relative_to(vault):
        return None
    if p == brain.path(guard["label_file"]).resolve():
        if "content" in args:
            old, new = (notes.read(p) if p.is_file() else ""), str(args.get("content") or "")
        else:
            old, new = str(args.get("old_string") or ""), str(args.get("new_string") or "")
        if adds_label(old, new, brain):
            return (f"Only the brain's owner assigns tasks to {brain.assistant['name']}, with brain assign. "
                    f"An AI may not add or raise a {brain.assistant['label']} label. Suggest the assignment instead.")
        return None
    if p.is_relative_to(brain.path("permanent").resolve()) and "permanent" in guard["protected"]:
        return ("An AI does not write permanent notes for the owner. Offer a draft, questions and notes "
                "to link to; the owner writes the note.")
    if p.is_relative_to(brain.path("inbox_agent").resolve()) and "inbox_agent" in guard["protected"]:
        return "Agent items enter the Inbox through G1. Write the source record and submit it with brain submit."
    for key in guard["protected"]:
        if key not in ("permanent", "inbox_agent") and p.is_relative_to(brain.path(key).resolve()):
            return f"Writing to {brain.cfg['paths'][key]} is reserved for the owner and brain commands."
    prefix = brain.cfg["files"]["template_prefix"]
    if any(part.startswith(prefix) for part in p.relative_to(vault).parts):
        return (f"Templates and logs (names starting with '{prefix}') are not edited directly. "
                "Copy a template to a new name before filling it in; logs are written by brain commands.")
    return None
