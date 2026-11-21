"""brain search and brain eval: find the right note by keyword, and measure whether search finds it.

Search ranks sections of notes (a note split at its headings) with BM25 (Robertson & Zaragoza 2009), written in the
standard library (ADR-08). Every comparison goes through textnorm.fold, so a query typed with diacritics, without them
or in NFD form finds the same notes. Johnny Decimal numbers such as 51.03 are searchable as one word.

The index is derived data in .brain/search-index.json beside brain.toml: never committed, rebuilt from the vault at any
time, and brought up to date before every search by reading again only the files whose size or time changed. When it
cannot be written (a read-only mount), search still works from memory.

What is indexed: every .md file in the vault except the Inbox (not clarified yet, as for the knowledge graph), every
file or folder starting with the template prefix "_" (templates, logs, the graph, the eval questions), and the
[search] exclude list. Each result says where it is (path:line), its lane, its grade, and whether it is unverified or
past its valid_until date; nothing is hidden for being less trusted (BR-02).

brain eval reads the owner's questions (vault/_eval/questions.md, written by the owner, never an AI) and reports
recall@k and MRR (BR-03), and how often search said "not found" to a question the brain has no answer to.
"""
from __future__ import annotations

import fnmatch
import json
import math
import re
from collections import Counter
from pathlib import Path

from . import kg, kgcore, notes
from .config import Brain
from .textnorm import fold, words

INDEX_VERSION = 2
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
JD_RE = re.compile(r"(?<![\d.])(\d\d\.\d\d)(?![\d.])")
EVAL_LINE_RE = re.compile(r"^\s*[-*]\s+(.+?)\s*(?:→|->)\s*(.+?)\s*$")
STOP = {fold(w) for w in (*kgcore._STOP_EN, *kgcore._STOP_VI)}


def settings(brain: Brain) -> dict:
    return brain.cfg["search"]


def index_path(brain: Brain) -> Path:
    return brain.root / settings(brain)["index"]


# ---------------------------------------------------------------- what is indexed
def _lanes(brain: Brain) -> list[tuple[str, str]]:
    p = brain.cfg["paths"]
    pairs = [(p["permanent"], "permanent"), (p["literature"], "literature"), (p["fleeting"], "fleeting"),
             (p["projects"], "project"), (p["next_actions"], "action"), (p["waiting_for"], "action"),
             (p["someday"], "action"), (p["areas"], "area"), (p["maps"], "map"), (p["code"], "code"),
             (p["archive"], "archive"), (p["weekly"], "weekly")]
    return sorted(((v.rstrip("/"), lane) for v, lane in pairs), key=lambda x: -len(x[0]))


def lane_of(brain: Brain, rel: str) -> str:
    for prefix, lane in _lanes(brain):
        if rel == prefix or rel.startswith(prefix + "/"):
            return lane
    return "other"


def skipped(brain: Brain, rel: str) -> bool:
    prefix = brain.cfg["files"]["template_prefix"]
    if any(part.startswith(prefix) for part in rel.split("/")):
        return True
    inbox_top = Path(brain.cfg["paths"]["inbox"]).parts[0]
    if rel.split("/")[0] == inbox_top:
        return True
    for pat in settings(brain).get("exclude", []):
        pat = pat.strip().rstrip("/")
        if pat and (fnmatch.fnmatch(rel, pat) or rel.startswith(pat + "/")):
            return True
    return False


def sources(brain: Brain) -> list[Path]:
    if not brain.vault.is_dir():
        return []
    return sorted(p for p in brain.vault.rglob("*.md") if p.is_file() and not skipped(brain, brain.rel(p)))


# ---------------------------------------------------------------- reading a note into sections
def terms(text: str) -> list[str]:
    """The words BM25 counts: folded words (textnorm) plus Johnny Decimal numbers kept whole (51.03)."""
    return words(text, min_len=1) + JD_RE.findall(text or "")


def sections(brain: Brain, p: Path) -> list[dict]:
    """A note split at its headings: one entry per section, with the line it starts on in the file."""
    text = notes.read(p)
    fm, body = notes.frontmatter(text)
    parts = notes.split_frontmatter(text)
    offset = len(parts[0]) + 2 if parts else 0
    rel = brain.rel(p)
    title = fm.get("title") or notes.title(body, p.stem)
    trust, grade = kg._trust(brain, fm)
    links = kg._links(body) + [l for k in brain.cfg["notes"]["link_keys"] for l in kg._links(fm.get(k, ""))]
    meta = {"path": rel, "title": title, "lane": lane_of(brain, rel), "grade": grade,
            "unverified": trust == "unverified", "valid_until": fm.get("valid_until", ""),
            "date": notes.note_date(p, fm, brain.cfg["notes"]["date_keys"]).isoformat(),
            "links": sorted(set(links))}
    header = " ".join([title, p.stem.replace("-", " "), fm.get("tags", ""), fm.get("aliases", "")])
    out, cur, fenced = [], {"line": offset + 1, "heading": "", "lines": []}, False
    for i, line in enumerate(body.splitlines()):
        if FENCE_RE.match(line):
            fenced = not fenced
        m = None if fenced else HEADING_RE.match(line)
        if m and cur["lines"]:
            out.append(cur)
            cur = {"line": offset + i + 1, "heading": m.group(2), "lines": [line]}
            continue
        if m:
            cur["heading"] = m.group(2)
        cur["lines"].append(line)
    out.append(cur)
    chunks = []
    for s in out:
        body_text = "\n".join(s["lines"]).strip()
        if not body_text and s is not out[0]:
            continue
        tf = Counter(terms(f"{header} {s['heading']} {body_text}"))
        if not tf:
            continue
        chunks.append({**meta, "line": s["line"], "heading": s["heading"], "tf": dict(tf),
                       "len": sum(tf.values()), "snippet": _snippet(body_text)})
    return chunks


def _snippet(text: str, limit: int = 320) -> str:
    lines = [l for l in text.splitlines() if l.strip() and not HEADING_RE.match(l)]
    s = re.sub(r"\s+", " ", " ".join(lines)).strip()
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


# ---------------------------------------------------------------- the index
def update(brain: Brain, rebuild: bool = False) -> dict:
    """Bring the index up to date: re-read only files whose size or time changed. Returns the index with counts."""
    f = index_path(brain)
    old = {}
    if not rebuild and f.is_file():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("version") == INDEX_VERSION and data.get("vault") == str(brain.vault):
                old = data.get("files", {})
        except (OSError, ValueError):
            old = {}
    files, read = {}, 0
    for p in sources(brain):
        st = p.stat()
        rel, stamp = brain.rel(p), [st.st_size, st.st_mtime_ns]
        if rel in old and old[rel].get("stamp") == stamp:
            files[rel] = old[rel]
            continue
        try:
            files[rel] = {"stamp": stamp, "chunks": sections(brain, p)}
        except (OSError, UnicodeDecodeError):
            continue
        read += 1
    removed = len(set(old) - set(files))
    data = {"version": INDEX_VERSION, "vault": str(brain.vault), "files": files}
    saved = True
    if read or removed or not f.is_file():
        try:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except OSError:
            saved = False
    chunks = [c for v in files.values() for c in v["chunks"]]
    return {"chunks": chunks, "files": len(files), "sections": len(chunks), "read": read, "removed": removed,
            "saved": saved, "path": f}


# ---------------------------------------------------------------- ranking
def search(brain: Brain, query: str, k: int | None = None, index: dict | None = None) -> dict:
    """The k best sections for a query, best first. found is False when nothing covers enough of the query."""
    cfg = settings(brain)
    k = int(k or cfg["k"])
    idx = index or update(brain)
    chunks = idx["chunks"]
    q = list(dict.fromkeys(terms(query)))
    content = [t for t in q if t not in STOP] or q
    if not q or not chunks:
        return {"query": query, "found": False, "results": [], "sections": len(chunks)}
    n = len(chunks)
    avg = sum(c["len"] for c in chunks) / n
    df = {t: sum(1 for c in chunks if t in c["tf"]) for t in q}
    k1, b = float(cfg["k1"]), float(cfg["b"])
    need = float(cfg["min_coverage"])
    scored = []
    for c in chunks:
        tf = c["tf"]
        hit = [t for t in content if t in tf]
        if not hit or len(hit) / len(content) < need:
            continue
        s = 0.0
        for t in q:
            f = tf.get(t)
            if f:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * c["len"] / avg))
        scored.append((s, c))
    today = brain.today
    if float(cfg.get("recency_weight", 0)) > 0:
        scored = _recency(scored, today, float(cfg["recency_weight"]), float(cfg["recency_half_life_days"]))
    if float(cfg.get("graph_weight", 0)) > 0 and scored:
        scored = _graph(chunks, scored, float(cfg["graph_weight"]), float(cfg["graph_damping"]))
    scored.sort(key=lambda x: (-x[0], x[1]["path"], x[1]["line"]))
    results = []
    for s, c in scored[:k]:
        end = notes.expires_on(c.get("valid_until", ""))
        results.append({"path": c["path"], "line": c["line"], "title": c["title"], "heading": c["heading"],
                        "lane": c["lane"], "grade": c["grade"], "unverified": c["unverified"],
                        "expired": bool(end and end <= today), "score": round(s, 3), "snippet": c["snippet"]})
    return {"query": query, "found": bool(results), "results": results, "sections": n}


def _recency(scored: list, today, weight: float, half_life: float) -> list:
    """BR-10, off unless [search] recency_weight > 0: newer notes rise, as in Park et al. 2023's memory stream.
    A note half_life days old gets half the boost of one written today."""
    import datetime as dt
    out = []
    for s, c in scored:
        try:
            age = max(0, (today - dt.date.fromisoformat(c.get("date", ""))).days)
        except ValueError:
            age = 10 ** 6
        out.append((s * (1 + weight * 0.5 ** (age / half_life)), c))
    return out


def _graph(chunks: list, scored: list, weight: float, damping: float, iterations: int = 30) -> list:
    """BR-11, off unless [search] graph_weight > 0: Personalized PageRank over the [[links]] between notes, started
    from the notes BM25 found (HippoRAG, Gutiérrez et al. 2024). A note linked from several hits gains even when it
    shares no word with the query; such a note is added through its first section."""
    first, names = {}, {}
    for c in chunks:
        first.setdefault(c["path"], c)
        stem = c["path"].rsplit("/", 1)[-1][:-3]
        names.setdefault(fold(stem), c["path"])
        names.setdefault(fold(c["title"]), c["path"])
    edges = {p: set() for p in first}
    for p, c in first.items():
        for l in c.get("links", []):
            q = names.get(fold(l))
            if q and q != p:
                edges[p].add(q)
                edges[q].add(p)
    seed = {}
    for s, c in scored:
        seed[c["path"]] = max(seed.get(c["path"], 0.0), s)
    total = sum(seed.values()) or 1.0
    restart = {p: v / total for p, v in seed.items()}
    rank = dict(restart)
    for _ in range(iterations):
        nxt = {p: (1 - damping) * restart.get(p, 0.0) for p in edges}
        for p, r in rank.items():
            if edges.get(p):
                share = damping * r / len(edges[p])
                for q in edges[p]:
                    nxt[q] += share
            else:
                nxt[p] = nxt.get(p, 0.0) + damping * r
        rank = nxt
    top = max(s for s, _ in scored)
    peak = max(rank.values()) or 1.0
    out = [(s + weight * top * rank.get(c["path"], 0.0) / peak, c) for s, c in scored]
    hit = {c["path"] for _, c in scored}
    for p, r in rank.items():
        if p not in hit and r > 0:
            out.append((weight * top * r / peak, first[p]))
    return out


def edges_first(results: list) -> list:
    """Best result first and second best last, the rest between (Liu et al. 2024, "Lost in the Middle")."""
    if len(results) < 3:
        return list(results)
    return [results[0], *results[2:], results[1]]


def flags(r: dict) -> str:
    out = [r["lane"]]
    if r["grade"]:
        out.append(r["grade"])
    if r["unverified"]:
        out.append("UNVERIFIED")
    if r["expired"]:
        out.append("EXPIRED")
    return " · ".join(out)


def for_agent(brain: Brain, res: dict) -> str:
    """Search results for an agent: at most k sections, best first and second best last, within max_chars."""
    if not res["found"]:
        return (f"Not found: no note in the brain covers \"{res['query']}\". Say the brain has no answer; do not "
                "guess one from these words.")
    budget = int(settings(brain)["max_chars"])
    out = [f"{len(res['results'])} notes for \"{res['query']}\" (best first, second best last). Cite them as path:line."]
    for r in edges_first(res["results"]):
        head = f"- {r['path']}:{r['line']} · {flags(r)} · {r['title']}" + (f" › {r['heading']}" if r["heading"] else "")
        line = f"{head}\n  {r['snippet']}"
        if sum(len(x) + 1 for x in out) + len(line) > budget:
            line = head
        if sum(len(x) + 1 for x in out) + len(line) > budget:
            break
        out.append(line)
    return "\n".join(out)


# ---------------------------------------------------------------- brain eval
def questions(brain: Brain) -> list[dict]:
    f = brain.vault / settings(brain)["questions"]
    if not f.is_file():
        return []
    out, section = [], ""
    for n, line in enumerate(notes.read(f).splitlines(), 1):
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        m = EVAL_LINE_RE.match(line)
        if not m or m.group(1).strip("`").startswith("<"):
            continue
        want = [w.strip().strip("`") for w in m.group(2).split(";") if w.strip()]
        none = [w.lower() for w in want] == ["none"]
        out.append({"line": n, "section": section, "question": m.group(1), "want": [] if none else want})
    return out


VARIANTS = {"bm25": {}, "recency": {"recency_weight": 0.3}, "graph": {"graph_weight": 0.5},
            "recency+graph": {"recency_weight": 0.3, "graph_weight": 0.5}}


def compare(brain: Brain, k: int | None = None) -> list[dict]:
    """BR-10 and BR-11 are kept only if they do not lower recall@k: the same questions under each ranking."""
    base = dict(brain.cfg["search"])
    out = []
    try:
        for name, extra in VARIANTS.items():
            brain.cfg["search"] = {**base, "recency_weight": 0, "graph_weight": 0, **extra}
            r = evaluate(brain, k)
            out.append({"variant": name, "settings": extra, "recall": r["recall"], "mrr": r["mrr"],
                        "said_not_found": r["said_not_found"], "unanswerable": r["unanswerable"]})
    finally:
        brain.cfg["search"] = base
    return out


def evaluate(brain: Brain, k: int | None = None) -> dict:
    """recall@k and MRR over the owner's questions; the same vault gives the same numbers on every run."""
    k = int(k or settings(brain)["k"])
    idx = update(brain)
    rows, hits, rr, answerable, refused, unanswerable = [], 0, 0.0, 0, 0, 0
    for q in questions(brain):
        res = search(brain, q["question"], k, idx)
        paths = list(dict.fromkeys(r["path"] for r in res["results"]))
        if not q["want"]:
            unanswerable += 1
            ok = not res["found"]
            refused += ok
            rows.append({**q, "rank": None, "ok": ok, "got": paths[:3]})
            continue
        answerable += 1
        want = {w.lstrip("/") for w in q["want"]}
        rank = next((i for i, p in enumerate(paths, 1) if p in want), None)
        hits += rank is not None
        rr += 1 / rank if rank else 0.0
        rows.append({**q, "rank": rank, "ok": rank is not None, "got": paths[:3]})
    return {"k": k, "questions": len(rows), "answerable": answerable,
            "recall": round(hits / answerable, 3) if answerable else None,
            "mrr": round(rr / answerable, 3) if answerable else None,
            "unanswerable": unanswerable, "said_not_found": refused, "rows": rows,
            "file": settings(brain)["questions"]}
