"""brain dashboard: a read-only page on 127.0.0.1 that shows how the brain is running, at a glance.

The page is a read side over the vault: it has no state of its own and no route that writes. Every change still goes
through the `brain` commands and the trust gates, so the page shows the command to copy (docs/dashboard.md).

Layout, from research on dashboards (docs/dashboard.md, "Why it looks like this"):
- the brain's four golden signals on top, as in Google's SRE book (symptoms first): traffic, latency, errors,
  saturation;
- below them the causes: the rules broken with the command that fixes each, projects, activity per day, knowledge,
  the timeline of turns.
No score, no target, no streak: a measure turned into a target stops measuring (Goodhart, Campbell), and people who
track themselves stop and come back (lived informatics), so quiet days are blank, not red.

Sources, all read-only: the dated lines of the Inbox, the turn log and the rejected log; the next actions; the notes'
front matter; `checks.check`; the knowledge graph and the platform map when they exist.

`collect(brain)` returns the JSON contract `schema: 1`, a presentation-neutral shape (each signal is a list of
labelled rows), so the page needs no field names of its own and another brain can fill it from other sources.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import assistant, checks, notes
from .config import Brain, defaults, open_brain

SCHEMA = 1
PAGE_FILE = Path(__file__).with_name("dashboard.html")
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
CODE_RE = re.compile(r"^([A-Z]+\d*-\d+) · (.*)$")
TURN_RE = re.compile(r"^- \[(\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))?\] (\w+) · (.*)$")
DONE_RE = re.compile(r"^\s*- \[[xX]\] .*· done (\d{4}-\d{2}-\d{2})")
WEEK_RE = re.compile(r"^(\d{4})-W(\d{2})$")
# The command that fixes a rule, by code prefix. A rule not listed points at `brain check`.
COMMANDS = {"KG-01": "brain kg build", "AS-01": "brain assigned", "AS-02": "brain assigned"}


def settings(brain: Brain) -> dict:
    return {**defaults().get("dashboard", {}), **(brain.cfg.get("dashboard") or {})}


def _level(*pairs) -> str:
    """'warn' when any (value, limit) pair is over its limit, else 'ok'."""
    return "warn" if any(v is not None and lim is not None and v > lim for v, lim in pairs) else "ok"


def _row(label: str, value, limit=None, unit: str = "") -> dict:
    over = value is not None and limit is not None and value > limit
    return {"label": label, "value": value, "limit": limit, "unit": unit, "level": "warn" if over else "ok"}


def _notes(brain: Brain, key: str):
    prefix = brain.cfg["files"]["template_prefix"]
    for p in notes.list_notes(brain.path(key), prefix):
        yield p, notes.frontmatter(notes.read(p))[0]


def _last_weekly(brain: Brain) -> dt.date | None:
    """The Sunday of the newest saved Weekly Review (weekly/YYYY-Www.md)."""
    folder = brain.path("weekly")
    weeks = []
    if folder.is_dir():
        for p in folder.glob("*.md"):
            m = WEEK_RE.match(p.stem)
            if m:
                try:
                    weeks.append(dt.date.fromisocalendar(int(m.group(1)), int(m.group(2)), 7))
                except ValueError:
                    pass
    return max(weeks, default=None)


def _turns(brain: Brain) -> list[dict]:
    p = brain.path("turn_log")
    out = []
    if p.is_file():
        for line in notes.read(p).splitlines():
            m = TURN_RE.match(line)
            if m:
                out.append({"date": dt.date.fromisoformat(m.group(1)), "time": m.group(2) or "",
                            "type": m.group(3), "summary": m.group(4).strip()})
    return out


def _daily(dates: list[dt.date], days: list[dt.date]) -> list[int]:
    index = {d: i for i, d in enumerate(days)}
    out = [0] * len(days)
    for d in dates:
        if d in index:
            out[index[d]] += 1
    return out


def _rules(errors: list[str], warnings: list[str]) -> list[dict]:
    rules: dict[str, dict] = {}
    for level, items in (("error", errors), ("warning", warnings)):
        for msg in items:
            m = CODE_RE.match(msg)
            code, text = (m.group(1), m.group(2)) if m else ("OTHER", msg)
            r = rules.setdefault(code, {"code": code, "level": level, "count": 0, "examples": [],
                                        "command": COMMANDS.get(code, "brain check")})
            r["count"] += 1
            if level == "error":
                r["level"] = "error"
            if len(r["examples"]) < 3:
                r["examples"].append(text)
    return sorted(rules.values(), key=lambda r: (r["level"] != "error", r["code"]))


def collect(brain: Brain, slug: str = "main", days: int | None = None) -> dict:
    """Everything the page shows (contract schema 1). Each source is read on its own: if one fails, its part is empty
    and the reason is in errors_reading, and the rest of the page still works."""
    cfg = settings(brain)
    n_days = int(days or cfg["days"])
    today = brain.today
    week_ago = today - dt.timedelta(days=7)
    errors_reading: list[dict] = []

    def read(name, fn, default):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - a broken source must not take the page down
            errors_reading.append({"source": name, "error": f"{type(e).__name__}: {str(e)[:200]}"})
            return default

    inbox = read("inbox", lambda: notes.dated_lines(brain.path("inbox")), [])
    agent = read("inbox_agent", lambda: [notes.note_date(p, fm, brain.cfg["notes"]["date_keys"])
                                         for p, fm in _notes(brain, "inbox_agent")], [])
    inbox_dates = [d for d, _ in inbox] + agent
    turns = read("turn_log", lambda: _turns(brain), [])
    rejected = read("rejected_log", lambda: [d for d, _ in notes.dated_lines(brain.path("rejected_log"))], [])
    next_text = read("next_actions", lambda: notes.read(brain.path("next_actions"))
                     if brain.path("next_actions").is_file() else "", "")
    done_dates = [dt.date.fromisoformat(m.group(1)) for m in
                  (DONE_RE.match(line) for line in next_text.splitlines()) if m]
    errs, warns = read("check", lambda: checks.check(brain), ([], []))
    date_keys = brain.cfg["notes"]["date_keys"]
    fleeting = read("fleeting", lambda: [notes.note_date(p, fm, date_keys) for p, fm in _notes(brain, "fleeting")], [])
    literature = read("literature", lambda: sum(1 for _ in _notes(brain, "literature")), 0)
    permanent = read("permanent", lambda: [notes.note_date(p, fm, date_keys)
                                           for p, fm in _notes(brain, "permanent")], [])
    tasks = read("assignments", lambda: assistant.assignments(brain), [])
    kgs = read("kg", lambda: _kg_stats(brain), None)
    drs = read("drive", lambda: _drive_stats(brain), None)
    weekly = read("weekly", lambda: _last_weekly(brain), None)

    inbox_oldest = max(((today - d).days for d in inbox_dates), default=0)
    fleeting_oldest = max(((today - d).days for d in fleeting), default=0)
    weekly_days = (today - weekly).days if weekly else None
    turns_7d = [t for t in turns if t["date"] > week_ago]
    lim_inbox, lim_fleeting = cfg["inbox_max_age_days"], brain.cfg["clarify"]["fleeting_max_days"]
    lim_weekly = cfg["weekly_max_gap_days"]
    kg_stale, kg_limit = (kgs or {}).get("stale"), brain.cfg["kg"]["max_stale_documents"]
    stale_tasks = read("assignments_stale", lambda: sum(1 for a in tasks if not a.done and assistant.is_stale(brain, a)), 0)

    day_list = [today - dt.timedelta(days=n_days - 1 - i) for i in range(n_days)]
    turn_types = brain.cfg["turn"]["types"]
    series_rows = [{"key": "inbox", "label": "captured, still in the Inbox", "tone": "accent",
                    "values": _daily(inbox_dates, day_list)},
                   *({"key": t, "label": f"turns: {t}", "tone": "accent",
                      "values": _daily([x["date"] for x in turns if x["type"] == t], day_list)} for t in turn_types),
                   {"key": "done", "label": "next actions done", "tone": "ok", "values": _daily(done_dates, day_list)}]

    signals = {
        "traffic": {
            "level": "ok",   # never coloured: a quiet week is not a fault
            "headline": f"{sum(1 for d in inbox_dates if d > week_ago)} · {len(turns_7d)}",
            "caption": "in (captured) · turns, last 7 days",
            "rows": [_row(f"turns: {t}", sum(1 for x in turns_7d if x["type"] == t)) for t in turn_types]
                    + [_row("next actions done", sum(1 for d in done_dates if d > week_ago))],
            "sparks": [{"label": "in", "tone": "accent", "values": _daily(inbox_dates, day_list)},
                       {"label": "turns", "tone": "ok", "values": _daily([x["date"] for x in turns], day_list)}],
        },
        "latency": {
            "level": _level((inbox_oldest, lim_inbox), (fleeting_oldest, lim_fleeting), (weekly_days, lim_weekly)),
            "headline": "", "caption": "days · the limit in brackets",
            "rows": [_row("oldest Inbox item", inbox_oldest, lim_inbox, "d"),
                     _row("oldest fleeting note", fleeting_oldest, lim_fleeting, "d"),
                     _row("last Weekly Review", weekly_days, lim_weekly, "d")],
            "sparks": [],
        },
        "errors": {
            "level": "fail" if errs else ("warn" if warns else "ok"),
            "headline": f"{len(errs)} · {len(warns)}", "caption": "rules broken (errors · warnings)",
            "rows": [_row("rejected at G1, last 7 days", sum(1 for d in rejected if d > week_ago))],
            "sparks": [],
        },
        "saturation": {
            "level": _level((inbox_oldest, lim_inbox), (kg_stale, kg_limit)),
            "headline": "", "caption": "what is piling up",
            "rows": [_row("Inbox", len(inbox_dates)), _row("fleeting notes", len(fleeting)),
                     _row(f"assigned to {brain.assistant['name']}, stale", stale_tasks),
                     # no graph yet: rule KG-01 says so below; the row stays neutral
                     _row("documents the graph has not read", kg_stale if kgs else "no graph",
                          kg_limit if kgs else None)],
            "sparks": [],
        },
    }

    pc = brain.cfg["project"]
    projects = []
    for p, fm in read("projects", lambda: list(_notes(brain, "projects")), []):
        if fm.get("status") != pc["active_status"]:
            continue
        end = notes.expires_on(fm.get("due", ""))
        projects.append({"slug": p.stem, "title": fm.get("title") or p.stem,
                         "next": len(re.findall(r"^\s*- \[ \] .*\[\[" + re.escape(p.stem) + r"\]\]", next_text,
                                                flags=re.M)),
                         "board": bool(fm.get("board")), "due": fm.get("due", ""),
                         "past_due": bool(end and today >= end)})

    knowledge = [{"label": "literature notes", "value": literature},
                 {"label": "permanent notes (new in 7 days)",
                  "value": f"{len(permanent)} ({sum(1 for d in permanent if d > week_ago)})"},
                 {"label": "next actions open",
                  "value": len(re.findall(r"^\s*- \[ \]", next_text, flags=re.M))}]
    if kgs:
        trust = kgs.get("by_trust") or {}
        knowledge += [{"label": "knowledge graph", "value": f"{kgs['triples']} triples · built {kgs.get('built') or '–'}"},
                      {"label": "trust", "value": " · ".join(f"{k} {v}" for k, v in trust.items()) or "–"}]
    if drs:
        knowledge.append({"label": "platform map",
                          "value": f"{drs['folders']} folders · {drs['files']} files · scanned {drs.get('built') or '–'}"})

    timeline = [{"ts": f"{t['date']} {t['time']}".strip(), "type": t["type"],
                 "text": t["summary"] if len(t["summary"]) <= 90 else t["summary"][:89] + "…"}
                for t in reversed(turns[-int(cfg["timeline_n"]):])]

    return {
        "schema": SCHEMA,
        "version": brain.cfg["brain"]["version"],
        "brain": slug,
        "label": str(cfg.get("name") or slug),
        "at": brain.now.isoformat(),
        "days": n_days,
        "signals": signals,
        "series": {"days": [d.isoformat() for d in day_list], "rows": series_rows},
        "rules": _rules(errs, warns),
        "projects": projects,
        "knowledge": knowledge,
        "timeline": timeline,
        "errors_reading": errors_reading,
    }


def _kg_stats(brain: Brain):
    if not brain.cfg["kg"]["enabled"] or not brain.path("kg_triples").is_file():
        return None
    from . import kg
    s = kg.stats(brain)
    return {k: s.get(k) for k in ("triples", "entities", "by_trust", "built", "stale")}


def _drive_stats(brain: Brain):
    from . import drive
    if not drive.enabled(brain) or not brain.path("drive_graph").is_file():
        return None
    s = drive.stats(brain)
    return {k: s.get(k) for k in ("root", "built", "folders", "files", "datasets", "repositories")}


def brains(brain: Brain) -> dict[str, Path]:
    """The brains the page can show: this one, then each folder named in [dashboard] brains that holds brain.toml."""
    found = {"main": brain.root}
    for entry in settings(brain).get("brains") or []:
        p = Path(entry)
        p = p if p.is_absolute() else brain.root / p
        if (p / "brain.toml").is_file():
            found.setdefault(p.name, p.resolve())
    return found


class State:
    """The brains a server shows, and a short cache so a page refreshing every 30 seconds never reads twice."""

    def __init__(self, brain: Brain):
        self.brain = brain
        self.cfg = settings(brain)
        self.homes = brains(brain)
        self.lock = threading.Lock()
        self.cache: dict[str, tuple[float, dict]] = {}

    def _open(self, slug: str) -> Brain:
        home = self.homes[slug]
        return self.brain if home == self.brain.root else open_brain(home)

    def list(self) -> list[dict]:
        out = []
        for slug in self.homes:
            name = settings(self._open(slug)).get("name")
            out.append({"slug": slug, "label": str(name or slug)})
        return out

    def get(self, slug: str | None) -> dict | None:
        slug = slug or "main"
        if slug not in self.homes:
            return None
        with self.lock:
            hit = self.cache.get(slug)
            if hit and time.monotonic() - hit[0] < float(self.cfg["cache_s"]):
                return hit[1]
            data = collect(self._open(slug), slug)
            self.cache[slug] = (time.monotonic(), data)
            return data


def page(state: State) -> bytes:
    boot = json.dumps({"brains": state.list(), "refresh_s": int(state.cfg["refresh_s"])}, ensure_ascii=False)
    return PAGE_FILE.read_text(encoding="utf-8").replace("__BOOT__", boot.replace("</", "<\\/")).encode("utf-8")


def make_handler(state: State):
    class Handler(BaseHTTPRequestHandler):
        server_version = "brain-dashboard"

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, data) -> None:
            self._send(code, json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"),
                       "application/json; charset=utf-8")

        def do_GET(self):  # noqa: N802 - http.server API
            url = urlparse(self.path)
            if url.path == "/":
                self._send(200, page(state), "text/html; charset=utf-8")
            elif url.path == "/api/state":
                slug = (parse_qs(url.query).get("brain") or [None])[0]
                data = state.get(slug)
                if data is None:
                    self._json(404, {"error": f"no brain {slug}", "brains": list(state.homes)})
                else:
                    self._json(200, data)
            elif url.path == "/api/brains":
                self._json(200, state.list())
            elif url.path == "/healthz":
                self._json(200, {"ok": True})
            else:
                self._json(404, {"error": "not found"})

        def _read_only(self):
            self._json(405, {"error": "the dashboard is read-only: change the brain with the brain command"})

        do_POST = do_PUT = do_PATCH = do_DELETE = _read_only  # noqa: N815

        def log_message(self, fmt, *args):  # one line per request is noise in a terminal
            return

    return Handler


def make_server(brain: Brain, host: str = "127.0.0.1", port: int | None = None) -> ThreadingHTTPServer:
    state = State(brain)
    return ThreadingHTTPServer((host, int(port if port is not None else state.cfg["port"])), make_handler(state))


def warn_host(host: str) -> str | None:
    if host in LOCAL_HOSTS:
        return None
    return (f"Warning: listening on {host} opens the dashboard to other machines on this network. It is read-only "
            "and shows no note content, but it does show task and project titles. Use 127.0.0.1 unless you mean it.")


def serve(brain: Brain, host: str = "127.0.0.1", port: int | None = None, open_browser: bool = False) -> None:
    srv = make_server(brain, host, port)
    url = f"http://{'127.0.0.1' if host in ('0.0.0.0', '::') else host}:{srv.server_address[1]}/"
    if (msg := warn_host(host)):
        print(msg, file=sys.stderr)
    print(f"Brain dashboard on {url} (read-only). Ctrl+C to stop.")
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
