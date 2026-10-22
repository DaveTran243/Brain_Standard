"""Reading and writing notes: files, frontmatter, titles, slugs, dates."""
from __future__ import annotations

import datetime as dt
import re
import unicodedata
from pathlib import Path

LINK_RE = re.compile(r"\[\[[^\]]+\]\]")
DATED_LINE_RE = re.compile(r"^- \[(\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))?\]")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def append(p: Path, line: str, header: str = "") -> None:
    """Append a line; create the file, its folder and its header first if needed."""
    p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists()
    with p.open("a", encoding="utf-8", newline="\n") as f:
        if new and header:
            f.write(header)
        f.write(line)


def _value(v: str) -> str:
    v = v.strip()
    if v[:1] in ('"', "'"):
        end = v.find(v[0], 1)
        if end != -1:
            return v[1:end]
    v = re.split(r"\s+#", v, maxsplit=1)[0].strip()
    return "" if v.startswith("#") else v


def split_frontmatter(text: str) -> tuple[list[str], list[str]] | None:
    """(frontmatter lines, body lines), or None when the text has no closed frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], lines[i + 1:]
    return None


def frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Read `key: value` frontmatter between two --- lines. Returns (fields, body)."""
    parts = split_frontmatter(text)
    if parts is None:
        return {}, text
    fm: dict[str, str] = {}
    for line in parts[0]:
        s = line.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        k, v = s.split(":", 1)
        fm[k.strip()] = _value(v)
    return fm, "\n".join(parts[1])


def add_frontmatter(text: str, fields: dict[str, str]) -> str:
    new = [f"{k}: {v}" for k, v in fields.items()]
    parts = split_frontmatter(text)
    if parts is None:
        return "\n".join(["---", *new, "---", *text.splitlines()]) + "\n"
    return "\n".join(["---", *parts[0], *new, "---", *parts[1]]) + "\n"


def title(body: str, fallback: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def slug(s: str, max_len: int = 60) -> str:
    s = unicodedata.normalize("NFKD", s.replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:max_len] or "item"


def expires_on(value: str) -> dt.date | None:
    """First day a value is out of date: YYYY-MM-DD expires the day after, YYYY-MM the month after."""
    value = (value or "").strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return dt.date.fromisoformat(value) + dt.timedelta(days=1)
        if re.fullmatch(r"\d{4}-\d{2}", value):
            year, month = map(int, value.split("-"))
            return dt.date(year + (month == 12), month % 12 + 1, 1)
    except ValueError:
        return None
    return None


def note_date(p: Path, fm: dict, date_keys: list[str]) -> dt.date:
    """A note's date: the first date key present, then a YYYYMMDD id or file name, then the file time."""
    for key in date_keys:
        try:
            return dt.date.fromisoformat(fm.get(key, "")[:10])
        except ValueError:
            pass
    m = re.match(r"(\d{4})(\d{2})(\d{2})", fm.get("id", "") or p.name)
    if m:
        try:
            return dt.date(*map(int, m.groups()))
        except ValueError:
            pass
    return dt.date.fromtimestamp(p.stat().st_mtime)


def list_notes(folder: Path, skip_prefix: str) -> list[Path]:
    """Every .md file under folder, skipping templates; empty when the folder is missing."""
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.rglob("*.md") if not p.name.startswith(skip_prefix))


def dated_lines(p: Path) -> list[tuple[dt.date, str]]:
    """Lines of the form `- [YYYY-MM-DD …] …` with their date."""
    if not p.is_file():
        return []
    out = []
    for line in read(p).splitlines():
        m = DATED_LINE_RE.match(line)
        if m:
            out.append((dt.date.fromisoformat(m.group(1)), line))
    return out
