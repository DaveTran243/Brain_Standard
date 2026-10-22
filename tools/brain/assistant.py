"""The assistant loop: you assign next actions, the assistant follows up and reports back to the Inbox."""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

from . import notes
from .config import Brain, BrainError

TASK_RE = re.compile(r"^(\s*)- \[([ xX])\] (.*)$")
ASSIGNED_RE = re.compile(r"· assigned (\d{4}-\d{2}-\d{2})")
DONE_RE = re.compile(r"· done (\d{4}-\d{2}-\d{2})")


@dataclass
class Assignment:
    """A next action carrying the assignment label."""

    line: int                  # line index in the Next Actions file
    done: bool
    level: str                 # "" when the level is missing or unknown
    text: str
    assigned: dt.date | None
    done_on: dt.date | None


def label_re(brain: Brain) -> re.Pattern:
    return re.compile(re.escape(brain.assistant["label"]) + r"(?::([\w-]+))?(?![\w:-])")


def assignments(brain: Brain) -> list[Assignment]:
    p = brain.path("next_actions")
    if not p.is_file():
        return []
    label, levels = label_re(brain), brain.assistant["levels"]
    out = []
    for i, line in enumerate(notes.read(p).splitlines()):
        m = TASK_RE.match(line)
        if not m or not (lm := label.search(m.group(3))):
            continue
        a, d = ASSIGNED_RE.search(line), DONE_RE.search(line)
        level = lm.group(1) or ""
        out.append(Assignment(
            line=i, done=m.group(2) != " ", level=level if level in levels else "", text=m.group(3),
            assigned=dt.date.fromisoformat(a.group(1)) if a else None,
            done_on=dt.date.fromisoformat(d.group(1)) if d else None,
        ))
    return out


def open_up_to(brain: Brain, max_level: str | None) -> list[Assignment]:
    """Open assignments with a valid level no higher than max_level (all levels when None)."""
    levels = brain.assistant["levels"]
    ceiling = levels.index(max_level) if max_level else len(levels) - 1
    return [a for a in assignments(brain) if not a.done and a.level and levels.index(a.level) <= ceiling]


def is_stale(brain: Brain, a: Assignment) -> bool:
    return bool(a.assigned) and (brain.today - a.assigned).days > brain.assistant["stale_after_days"]


def plain_text(brain: Brain, text: str) -> str:
    """Task text without the label and dates, for result lines."""
    text = ASSIGNED_RE.sub("", DONE_RE.sub("", label_re(brain).sub("", text)))
    return " ".join(text.replace("· ·", "·").split()).strip(" ·")


def assign(brain: Brain, match: str, level: str) -> str:
    """Add the label and today's date to the one open next action containing match. Returns the task text."""
    if level not in brain.assistant["levels"]:
        raise BrainError(f"Level must be one of: {', '.join(brain.assistant['levels'])}.")
    p = brain.path("next_actions")
    match = " ".join(match.split())
    lines = notes.read(p).splitlines() if p.is_file() else []
    hits = [i for i, line in enumerate(lines)
            if (m := TASK_RE.match(line)) and m.group(2) == " " and match.lower() in m.group(3).lower()]
    if len(hits) != 1:
        raise BrainError(f"Need exactly 1 open next action containing '{match}', found {len(hits)}.")
    i = hits[0]
    if label_re(brain).search(lines[i]):
        raise BrainError(f"This task is already assigned to {brain.assistant['name']}. "
                         "Change its level by editing Next Actions if needed.")
    lines[i] = f"{lines[i].rstrip()} · {brain.assistant['label']}:{level} · assigned {brain.today:%Y-%m-%d}"
    notes.write(p, "\n".join(lines) + "\n")
    return TASK_RE.match(lines[i]).group(3)


def report(brain: Brain, number: int, result: str, max_level: str | None) -> str:
    """Mark the number-th open assignment done and write the result to the Inbox. Returns the task text."""
    result = " ".join(result.split())
    if not result:
        raise BrainError("A result sentence is required: what was done and where the result is.")
    open_ = open_up_to(brain, max_level)
    if not 1 <= number <= len(open_):
        raise BrainError(f"No task number {number}. Run brain assigned to see the list.")
    a = open_[number - 1]
    p = brain.path("next_actions")
    lines = notes.read(p).splitlines()
    lines[a.line] = lines[a.line].replace("- [ ]", "- [x]", 1).rstrip() + f" · done {brain.today:%Y-%m-%d}"
    notes.write(p, "\n".join(lines) + "\n")
    task = plain_text(brain, a.text)
    channel = brain.assistant["result_channel"]
    notes.append(brain.path("inbox"), f"- [{brain.stamp}] ({channel}) Result \"{task}\": {result}\n",
                 brain.cfg["files"]["inbox_header"])
    return task
