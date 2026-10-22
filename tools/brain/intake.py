"""Getting things in: your words go straight to the Inbox; facts from an agent go through G1."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import gates, notes
from .config import Brain, BrainError


def capture(brain: Brain, text: str, channel: str | None = None) -> str:
    text = " ".join(text.split())
    if not text:
        raise BrainError("Nothing to capture.")
    channel = channel or brain.cfg["capture"]["default_channel"]
    notes.append(brain.path("inbox"), f"- [{brain.stamp}] ({channel}) {text}\n", brain.cfg["files"]["inbox_header"])
    return text


@dataclass
class Submission:
    outcome: str        # card, literature, fleeting, reject
    title: str
    grade: str
    saved_as: Path | None = None
    warning: str = ""


def submit(brain: Brain, file: Path) -> Submission:
    """Run G1 on a file with a source record. Raises BrainError when the record is returned."""
    if not file.is_file():
        raise BrainError(f"File not found: {file}")
    g = brain.gates
    text = notes.read(file)
    fm, body = notes.frontmatter(text)
    warning = ""
    if missing := gates.missing_fields(fm, g):
        warning = f"G1 returned {file.name}: missing {', '.join(missing)}."
        if g["strict"]:
            raise BrainError(warning + " Complete the source record and submit again.")
    grade = fm.get("grade", "").strip().upper()
    outcome = gates.reach(grade, g)
    if outcome == gates.MALFORMED:
        raise BrainError(f"G1 returned {file.name}: grade '{grade}' must be {gates.grade_format(g)}.")
    title = notes.title(body, file.stem)
    if outcome == gates.REJECT:
        notes.append(brain.path("rejected_log"),
                     f"- [{brain.stamp}] rejected · {grade} · {file.name} · {fm.get('source', '')}\n",
                     brain.cfg["files"]["rejected_log_header"])
        return Submission(outcome, title, grade, warning=warning)
    added = {"max_reach": outcome, "submitted": f"{brain.today:%Y-%m-%d}"}
    if outcome == gates.FLEETING:
        added["label"] = g["unverified_label"]
    name = f"{brain.now:%Y%m%d-%H%M%S}-{notes.slug(file.stem)}.md"
    target = brain.path("inbox_agent") / name
    notes.write(target, notes.add_frontmatter(text, added))
    reach_name = g["reach_names"][outcome]
    agent_dir = brain.cfg["paths"]["inbox_agent"].rsplit("/", 1)[-1]
    notes.append(brain.path("inbox"),
                 f"- [{brain.stamp}] (agent) {title} · {grade} · up to {reach_name} → {agent_dir}/{name}\n",
                 brain.cfg["files"]["inbox_header"])
    return Submission(outcome, title, grade, target, warning)
