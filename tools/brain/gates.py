"""Trust gates: read an Admiralty grade and decide how far a fact may travel."""
from __future__ import annotations

import re

MALFORMED = "malformed"
REJECT = "reject"
FLEETING = "fleeting"
LITERATURE = "literature"
CARD = "card"


def grade_pattern(gates: dict) -> re.Pattern:
    sources = re.escape("".join(gates["sources"]))
    credibility = "".join(str(c) for c in gates["credibility"])
    return re.compile(f"^([{sources}])([{credibility}])$")


def parse_grade(grade: str, gates: dict) -> tuple[str, int] | None:
    m = grade_pattern(gates).match((grade or "").strip().upper())
    return (m.group(1), int(m.group(2))) if m else None


def reach(grade: str, gates: dict) -> str:
    """G1: card, literature, fleeting, reject or malformed."""
    parsed = parse_grade(grade, gates)
    if parsed is None:
        return MALFORMED
    source, credibility = parsed
    if source in gates["reject_sources"] or credibility in gates["reject_credibility"]:
        return REJECT
    if source in gates["fleeting_only_sources"]:
        return FLEETING
    if source in gates["literature_sources"] and credibility in gates["card_credibility"]:
        return CARD
    return LITERATURE


def missing_fields(fm: dict, gates: dict) -> list[str]:
    return [k for k in gates["required_fields"] if not fm.get(k)]


def grade_format(gates: dict) -> str:
    """Human description of a valid grade, for messages."""
    s, c = gates["sources"], gates["credibility"]
    return f"source {s[0]}–{s[-1]} + credibility {c[0]}–{c[-1]}, for example B2"


def span(values: list) -> str:
    return f"{values[0]}–{values[-1]}" if len(values) > 1 else str(values[0])
