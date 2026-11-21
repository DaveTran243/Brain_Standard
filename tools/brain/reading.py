"""brain read and brain cite-check: an agent reads a note safely, and every path:line it cites can be checked.

Reading (BR-05, BR-06). A path is relative to the vault. It is refused, whatever an agent was told to ask for, when
it is absolute, names a drive, climbs out of the vault (../brain.toml), reaches out through a link, or is not a
Markdown note. The decision is made here in code, never left to the agent's judgement. Lines come back numbered, so
the agent can cite them as path:line.

Citations (BR-09, metric M4). brain cite-check reads an answer and checks each citation in it: the note exists in the
vault, the line exists, and a quote given next to it ("…" after path:line) really is there, within a few lines.
Folded text is compared (textnorm), so a quote typed without diacritics still counts. Gao et al. 2023 (ALCE) found
even the best models leave about half their answers without full citation support; this catches the broken ones
before they reach the vault.
"""
from __future__ import annotations

import re
from pathlib import Path, PurePosixPath, PureWindowsPath

from . import notes
from .config import Brain, BrainError
from .textnorm import fold

QUOTE = r"""(?:\s*[-—:]?\s*["“«]([^"”»\n]{3,}?)["”»])?"""
CITE_TICK = re.compile(r"`([^`\n]+?\.md):(\d+)(?:-(\d+))?`" + QUOTE)
CITE_BARE = re.compile(r"(?<![\w/.`\\-])((?:[\w.()\-]+/)*[\w.()\-]+\.md):(\d+)(?:-(\d+))?" + QUOTE)


def settings(brain: Brain) -> dict:
    return brain.cfg["read"]


class Refused(BrainError):
    """A path an agent may not read. Exit code 4, so a refusal is never mistaken for a missing note."""

    def __init__(self, message: str):
        super().__init__(message, code=4)


def safe_path(brain: Brain, rel: str) -> Path:
    """The note a vault-relative path names, or Refused. Checks the words of the path, then where it really leads."""
    raw = str(rel or "").strip().replace("\\", "/")
    if not raw or "\x00" in raw:
        raise Refused("Give a note's path relative to the vault, e.g. 30-Knowledge/permanent/note.md.")
    if PurePosixPath(raw).is_absolute() or PureWindowsPath(raw).drive or raw.startswith("~"):
        raise Refused(f"Refused: {rel} is not inside the vault. Paths are relative to the vault.")
    if ".." in PurePosixPath(raw).parts:
        raise Refused(f"Refused: {rel} climbs out of its folder. Only notes inside the vault can be read.")
    if not raw.lower().endswith(".md"):
        raise Refused(f"Refused: {rel} is not a Markdown note. Only .md notes in the vault can be read.")
    vault = brain.vault.resolve()
    p = (brain.vault / raw).resolve()
    if not p.is_relative_to(vault):
        raise Refused(f"Refused: {rel} leads outside the vault through a link.")
    if not p.is_file():
        raise BrainError(f"No note at {raw}. Find it first with brain search.", code=1)
    return p


def read_note(brain: Brain, rel: str, start: int = 1, count: int | None = None) -> dict:
    """Numbered lines of a note, from start, at most count (default [read] max_lines)."""
    p = safe_path(brain, rel)
    lines = notes.read(p).splitlines()
    start = max(1, int(start or 1))
    count = max(1, min(int(count or settings(brain)["max_lines"]), int(settings(brain)["max_lines"])))
    part = lines[start - 1: start - 1 + count]
    return {"path": brain.rel(p), "from": start, "to": start + len(part) - 1, "total": len(lines),
            "lines": [f"{start + i:>5}  {line}" for i, line in enumerate(part)]}


# ---------------------------------------------------------------- citations
def citations(text: str) -> list[dict]:
    """Every path:line (or path:a-b) in a text, with the quote written next to it if any, in order."""
    found, seen = [], set()
    for rx in (CITE_TICK, CITE_BARE):
        for m in rx.finditer(text or ""):
            if any(a <= m.start() < b for a, b in seen):
                continue
            seen.add((m.start(), m.end()))
            line = int(m.group(2))
            found.append({"at": m.start(), "path": m.group(1).strip(), "line": line,
                          "end": int(m.group(3)) if m.group(3) else line, "quote": (m.group(4) or "").strip()})
    return sorted(found, key=lambda c: c["at"])


def check_citation(brain: Brain, c: dict) -> dict:
    """ok, or why not: refused (outside the vault), missing (no such note), bad_line, quote_not_found."""
    out = {k: c[k] for k in ("path", "line", "end", "quote")}
    try:
        p = safe_path(brain, c["path"])
    except Refused as e:
        return {**out, "status": "refused", "why": str(e)}
    except BrainError:
        return {**out, "status": "missing", "why": f"no note at {c['path']}"}
    lines = notes.read(p).splitlines()
    if not 1 <= c["line"] <= c["end"] <= len(lines):
        return {**out, "status": "bad_line", "why": f"{c['path']} has {len(lines)} lines"}
    if c["quote"]:
        w = int(settings(brain)["quote_window"])
        near = fold(" ".join(lines[max(0, c["line"] - 1 - w): c["end"] + w]))
        if " ".join(fold(c["quote"]).split()) not in " ".join(near.split()):
            return {**out, "status": "quote_not_found",
                    "why": f"the quote is not within {w} lines of {c['path']}:{c['line']}"}
    return {**out, "status": "ok", "why": ""}


def cite_check(brain: Brain, text: str) -> dict:
    rows = [check_citation(brain, c) for c in citations(text)]
    ok = sum(r["status"] == "ok" for r in rows)
    return {"citations": len(rows), "ok": ok, "broken": len(rows) - ok, "rows": rows,
            "share_ok": round(ok / len(rows), 3) if rows else None}
