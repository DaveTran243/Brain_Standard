"""brain check: every rule, with its code. Returns (errors, warnings)."""
from __future__ import annotations

from . import assistant, gates, notes
from .config import Brain


def _notes(brain: Brain, key: str):
    for p in notes.list_notes(brain.path(key), brain.cfg["files"]["template_prefix"]):
        fm, body = notes.frontmatter(notes.read(p))
        yield p, fm, body


def check(brain: Brain) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    g = brain.gates
    today = brain.today
    rel = brain.rel

    # G1 · agent items already in the Inbox
    for p, fm, _ in _notes(brain, "inbox_agent"):
        if missing := gates.missing_fields(fm, g):
            errors.append(f"G1-01 · {rel(p)}: agent item is missing {', '.join(missing)}")
            continue
        r = gates.reach(fm.get("grade", ""), g)
        if r == gates.MALFORMED:
            errors.append(f"G1-02 · {rel(p)}: grade '{fm.get('grade')}' is malformed")
        elif r == gates.REJECT:
            errors.append(f"G1-03 · {rel(p)}: grade {fm.get('grade')} should have been rejected but is in the Inbox")

    # G2 · literature with a grade
    for p, fm, _ in _notes(brain, "literature"):
        grade = fm.get("grade", "").upper()
        if not grade:
            continue
        parsed = gates.parse_grade(grade, g)
        if parsed is None:
            errors.append(f"G2-01 · {rel(p)}: grade '{grade}' is malformed")
        elif parsed[0] not in g["literature_sources"]:
            errors.append(f"G2-02 · {rel(p)}: literature needs source {gates.span(g['literature_sources'])}, has {grade}")
        if not fm.get("archived"):
            errors.append(f"G2-03 · {rel(p)}: no archived copy (archived)")

    # G3 and permanent-note rules
    link_keys = brain.cfg["notes"]["link_keys"]
    for p, fm, body in _notes(brain, "permanent"):
        if not notes.LINK_RE.search(body) and not any(notes.LINK_RE.search(fm.get(k, "")) for k in link_keys):
            errors.append(f"KN-01 · {rel(p)}: permanent note links to no other note")
        grade = fm.get("grade", "").upper()
        if grade:
            parsed = gates.parse_grade(grade, g)
            if parsed is None:
                errors.append(f"G3-01 · {rel(p)}: grade '{grade}' is malformed")
            elif parsed[1] not in g["permanent_credibility"]:
                errors.append(f"G3-02 · {rel(p)}: permanent needs credibility {gates.span(g['permanent_credibility'])}, has {grade}")
        if not fm.get("id"):
            warnings.append(f"KN-02 · {rel(p)}: permanent note has no id")

    # KN-03 · old fleeting notes
    max_days = brain.cfg["clarify"]["fleeting_max_days"]
    date_keys = brain.cfg["notes"]["date_keys"]
    for p, fm, _ in _notes(brain, "fleeting"):
        age = (today - notes.note_date(p, fm, date_keys)).days
        if age > max_days:
            warnings.append(f"KN-03 · {rel(p)}: fleeting note is {age} days old; move it to literature or delete it")

    # VD-01 · past valid_until
    for key in ("literature", "permanent", "inbox_agent"):
        for p, fm, _ in _notes(brain, key):
            end = notes.expires_on(fm.get("valid_until", ""))
            if end and today >= end:
                warnings.append(f"VD-01 · {rel(p)}: past its valid_until date ({fm.get('valid_until')})")

    # AC and EX · projects (no limit on the number of projects or next actions)
    na = brain.path("next_actions")
    next_actions = notes.read(na) if na.is_file() else ""
    pc, ex = brain.cfg["project"], brain.cfg["execution"]
    for p, fm, _ in _notes(brain, "projects"):
        status = fm.get("status", "")
        if status not in pc["statuses"]:
            errors.append(f"AC-01 · {rel(p)}: status must be one of {', '.join(pc['statuses'])}")
            continue
        if status == pc["active_status"]:
            for k in pc["required_when_active"]:
                if not fm.get(k):
                    errors.append(f"AC-02 · {rel(p)}: missing {k}; set it when the project is created")
            has_board = bool(fm.get("board"))
            if ex["warn_milestone_without_board"] and fm.get("milestone") and not has_board:
                warnings.append(f"EX-01 · {rel(p)}: has a milestone but no board")
            if ex["warn_project_without_task"] and not has_board and f"[[{p.stem}]]" not in next_actions:
                warnings.append(f"EX-02 · {rel(p)}: active project has no task in Next Actions or on a board")
            end = notes.expires_on(fm.get("due", ""))
            if end and today >= end:
                warnings.append(f"EX-03 · {rel(p)}: past its due date {fm.get('due')}")
        if status == pc["stopped_status"] and not fm.get("stop_reason"):
            warnings.append(f"AC-03 · {rel(p)}: stopped project should record a stop_reason")

    # AS · assignments
    levels = brain.assistant["levels"]
    for a in assistant.assignments(brain):
        if a.done:
            continue
        if not a.level:
            errors.append(f"AS-01 · next action line {a.line + 1}: {brain.assistant['label']} needs a level "
                          f"({', '.join(levels)})")
        elif assistant.is_stale(brain, a):
            warnings.append(f"AS-02 · next action line {a.line + 1}: assigned {(today - a.assigned).days} days ago "
                            "and still open")
    return errors, warnings
