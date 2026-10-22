"""brain weekly: measures for the Weekly Review. Measures only, never blocks."""
from __future__ import annotations

import datetime as dt
import re

from . import assistant, gates, notes
from .config import Brain


def measure(brain: Brain) -> dict:
    today = brain.today
    week_ago = today - dt.timedelta(days=7)
    prefix = brain.cfg["files"]["template_prefix"]
    date_keys = brain.cfg["notes"]["date_keys"]
    pc = brain.cfg["project"]

    def fms(key):
        return [(p, notes.frontmatter(notes.read(p))[0]) for p in notes.list_notes(brain.path(key), prefix)]

    projects = [fm for _, fm in fms("projects")]
    by_status = {s: sum(1 for fm in projects if fm.get("status") == s) for s in pc["statuses"]}
    na = brain.path("next_actions")
    next_text = notes.read(na) if na.is_file() else ""
    inbox = notes.dated_lines(brain.path("inbox"))
    agent = fms("inbox_agent")
    incomplete = sum(1 for _, fm in agent if gates.missing_fields(fm, brain.gates))
    turn_types = brain.cfg["turn"]["types"]
    turns = [line for day, line in notes.dated_lines(brain.path("turn_log")) if day > week_ago]
    expired = sum(
        1 for key in ("literature", "permanent", "inbox_agent") for _, fm in fms(key)
        if (end := notes.expires_on(fm.get("valid_until", ""))) and today >= end
    )
    tasks = assistant.assignments(brain)
    iso = today.isocalendar()
    return {
        "week": f"{iso.year}-W{iso.week:02d}",
        "projects_active": by_status.get(pc["active_status"], 0),
        "projects_done": by_status.get(pc["done_status"], 0),
        "projects_stopped": by_status.get(pc["stopped_status"], 0),
        "projects_overdue": sum(
            1 for fm in projects
            if fm.get("status") == pc["active_status"] and (e := notes.expires_on(fm.get("due", ""))) and today >= e
        ),
        "next_open": len(re.findall(r"^\s*- \[ \]", next_text, flags=re.M)),
        "next_done": len(re.findall(r"^\s*- \[[xX]\]", next_text, flags=re.M)),
        "inbox": len(inbox),
        "inbox_oldest_days": max(((today - day).days for day, _ in inbox), default=0),
        "fleeting_old": sum(
            1 for p, fm in fms("fleeting")
            if (today - notes.note_date(p, fm, date_keys)).days > brain.cfg["clarify"]["fleeting_max_days"]
        ),
        "permanent_new": sum(1 for p, fm in fms("permanent") if notes.note_date(p, fm, date_keys) > week_ago),
        "turns": len(turns),
        "turns_by_type": {t: sum(1 for line in turns if f"] {t} ·" in line) for t in turn_types},
        "rejected": sum(1 for day, _ in notes.dated_lines(brain.path("rejected_log")) if day > week_ago),
        "incomplete_records_pct": round(100 * incomplete / len(agent)) if agent else 0,
        "past_valid_until": expired,
        "assigned_open": sum(1 for a in tasks if not a.done),
        "assigned_done": sum(1 for a in tasks if a.done and a.done_on and a.done_on > week_ago),
        "assigned_stale": sum(1 for a in tasks if not a.done and assistant.is_stale(brain, a)),
    }


def render(brain: Brain, m: dict) -> str:
    by_type = ", ".join(f"{k} {v}" for k, v in m["turns_by_type"].items())
    name = brain.assistant["name"]
    return "\n".join([
        f"## Metrics · {m['week']}",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Active projects | {m['projects_active']} |",
        f"| Projects done · stopped | {m['projects_done']} · {m['projects_stopped']} |",
        f"| Projects past due | {m['projects_overdue']} |",
        f"| Next actions open · done | {m['next_open']} · {m['next_done']} |",
        f"| Inbox items · oldest (days) | {m['inbox']} · {m['inbox_oldest_days']} |",
        f"| Fleeting older than {brain.cfg['clarify']['fleeting_max_days']} days | {m['fleeting_old']} |",
        f"| New permanent notes in 7 days | {m['permanent_new']} |",
        f"| Turns in 7 days | {m['turns']} ({by_type}) |",
        f"| Rejected at G1 in 7 days | {m['rejected']} |",
        f"| Agent items with an incomplete source record | {m['incomplete_records_pct']}% |",
        f"| Items past valid_until | {m['past_valid_until']} |",
        f"| Assigned to {name}: open · done in 7 days · stale | {m['assigned_open']} · {m['assigned_done']} · {m['assigned_stale']} |",
        "",
        "Measures only, never blocks. There is no limit on projects or next actions.",
        "",
    ])
