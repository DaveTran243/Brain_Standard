"""The knowledge graph of a Brain_Standard brain: the vault as triples, read before a conversation, updated after it.

kgcore does the graph work; this module feeds it the vault and keeps the result in the vault:

  _kg/triples.jsonl   one triple per line, sorted, so git diffs stay readable
  _kg/state.json      the content hash of every document already in the graph, so updates only redo what changed

Both live under a folder starting with the template prefix ("_"), so the write guard already stops an AI from
editing them by hand; only brain commands write them.

Two kinds of knowledge enter the graph and never mix:
  note    what a clarified note, project, area, map or next action says (the Inbox is not clarified, so it stays out)
  memory  what was said in a conversation: the owner's words (trust owner) and the turn summaries an agent recorded
          (trust agent). An agent's answer is never stored as a fact: facts an agent brings in enter only through
          gate G1 (brain submit), and come back as notes with their grade.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import gates, kgcore, notes
from .config import Brain

KINDS = {"permanent": "permanent", "literature": "literature", "fleeting": "fleeting", "projects": "project",
         "areas": "area", "maps": "moc"}
SEGMENT_RE = re.compile(r"\s+·\s+")


def settings(brain: Brain) -> dict:
    return brain.cfg["kg"]


# ---------------------------------------------------------------- documents
def _trust(brain: Brain, fm: dict) -> tuple[str, str]:
    g = brain.gates
    if fm.get("label") == g["unverified_label"]:
        return "unverified", fm.get("grade", "")
    grade = fm.get("grade", "").strip().upper()
    if not grade:
        return "owner", ""
    parsed = gates.parse_grade(grade, g)
    if parsed is None or parsed[0] in g["fleeting_only_sources"]:
        return "unverified", grade
    return "graded", grade


def _links(text: str) -> list[str]:
    return [m.strip("[]").split("|")[0].strip() for m in notes.LINK_RE.findall(text or "")]


def _list(value: str) -> list[str]:
    value = (value or "").strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [v.strip().strip("\"'").lstrip("#") for v in value.split(",") if v.strip().strip("\"'")]


def documents(brain: Brain) -> dict[str, dict]:
    """Every clarified document the graph is built from, by id."""
    kinds = set(settings(brain)["kinds"])
    prefix = brain.cfg["files"]["template_prefix"]
    read = {}
    for key in KINDS:
        for p in notes.list_notes(brain.path(key), prefix):
            fm, body = notes.frontmatter(notes.read(p))
            read[(key, p)] = (fm, body, fm.get("title") or notes.title(body, p.stem))
    titles = {p.stem: t for (_, p), (_, _, t) in read.items()}
    docs = []
    for (key, p), (fm, body, title) in read.items():
        kind = KINDS[key]
        if kind not in kinds:
            continue
        links = []
        for k in brain.cfg["notes"]["link_keys"]:
            links += _links(fm.get(k, ""))
        links += _links(body)
        rel = []
        for field, pred in (("outcome", "aims at"), ("area", "in area"), ("source", "cites"),
                            ("original_source", "cites"), ("author", "written by")):
            val = fm.get(field, "").strip()
            if val and not notes.LINK_RE.fullmatch(val) and len(val) <= 160:
                rel.append((pred, val))
            elif val and notes.LINK_RE.fullmatch(val):
                links += _links(val)
        trust, grade = _trust(brain, fm)
        docs.append({"id": f"{kind}:{p.stem}", "kind": kind, "title": title, "text": body,
                     "links": sorted({titles.get(l, l) for l in links if l}), "tags": _list(fm.get("tags", "")),
                     "relations": rel, "trust": trust, "grade": grade})
    na = brain.path("next_actions")
    if "next" in kinds and na.is_file():
        for i, line in enumerate(notes.read(na).splitlines()):
            m = re.match(r"^\s*- \[ \] (.+)$", line)
            if not m:
                continue
            segs = SEGMENT_RE.split(m.group(1))
            rel = [("advances", titles.get(l, l)) for s in segs[1:] for l in _links(s)]
            rel += [("context", s) for s in segs[1:] if s.startswith("@") and ":" not in s]
            docs.append({"id": f"next:{i + 1}", "kind": "next", "title": segs[0], "text": "", "links": [],
                         "tags": [], "relations": rel, "trust": "owner", "grade": ""})
    return {d["id"]: d for d in docs}


def _doc_hash(d: dict) -> str:
    return kgcore.digest(json.dumps([d["title"], d["text"], d["links"], d["tags"], d["relations"], d["trust"],
                                     d["grade"]], ensure_ascii=False, default=str))


# ---------------------------------------------------------------- storage
def load(brain: Brain) -> list[dict]:
    f = brain.path("kg_triples")
    if not f.is_file():
        return []
    return [json.loads(line) for line in notes.read(f).splitlines() if line.strip()]


def _state(brain: Brain) -> dict:
    f = brain.path("kg_state")
    try:
        return json.loads(notes.read(f)) if f.is_file() else {}
    except json.JSONDecodeError:
        return {}


def save(brain: Brain, triples: list[dict], state: dict) -> None:
    triples = kgcore.dedupe(triples)
    triples.sort(key=lambda t: (t["kind"], t["src"], t["s"], t["p"], t["o"]))
    notes.write(brain.path("kg_triples"), "".join(json.dumps(t, ensure_ascii=False, sort_keys=True) + "\n"
                                                  for t in triples))
    notes.write(brain.path("kg_state"), json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


# ---------------------------------------------------------------- build
def build(brain: Brain, full: bool = False, use_llm: bool | None = None, chat=None) -> dict:
    """Bring the graph up to date with the vault. Only documents whose content changed are read again; memory
    triples are kept; inferred triples are recomputed."""
    cfg = settings(brain)
    if use_llm is None:
        use_llm = kgcore.llm_ready(cfg)
    docs = documents(brain)
    state = {} if full else _state(brain)
    seen = dict(state.get("docs") or {})
    llm_docs = set(state.get("llm_docs") or [])
    triples = [t for t in load(brain) if t["kind"] != "inferred"]
    changed = [d for d in docs.values() if full or seen.get(d["id"]) != _doc_hash(d)
               or (use_llm and d["id"] not in llm_docs and d.get("text"))]
    gone = set(seen) - set(docs)
    redo = {d["id"] for d in changed} | gone
    triples = [t for t in triples if not (t["kind"] == "note" and t["src"] in redo)]
    errors = 0
    for d in changed:
        triples += kgcore.rule_triples(d, cfg)
        if use_llm and d.get("text", "").strip():
            try:
                triples += kgcore.llm_triples(d, cfg, chat or kgcore.llm_chat)
                llm_docs.add(d["id"])
            except Exception:  # noqa: BLE001 - one failed call keeps the rules' triples and moves on
                errors += 1
                llm_docs.discard(d["id"])
        seen[d["id"]] = _doc_hash(d)
    for g in gone:
        seen.pop(g, None)
        llm_docs.discard(g)
    triples = kgcore.dedupe(triples)
    inferred = kgcore.infer(triples, cfg)
    save(brain, triples + inferred, {"docs": seen, "llm_docs": sorted(llm_docs), "built": brain.stamp})
    return {"documents": len(docs), "changed": len(changed), "removed": len(gone), "triples": len(triples),
            "inferred": len(inferred), "llm": bool(use_llm), "llm_errors": errors}


def stale(brain: Brain) -> int:
    seen = _state(brain).get("docs") or {}
    docs = documents(brain)
    return sum(1 for d in docs.values() if seen.get(d["id"]) != _doc_hash(d)) + len(set(seen) - set(docs))


# ---------------------------------------------------------------- read
def ask(brain: Brain, question: str, max_facts: int | None = None, hops: int | None = None):
    cfg = settings(brain)
    triples = load(brain)
    if not triples:
        return [], []
    index = kgcore.GraphIndex(triples)
    seeds = kgcore.match_entities(index, question, int(cfg["max_seeds"]), cfg.get("stopwords", []))
    picked = kgcore.retrieve(index, seeds, int(hops or cfg["hops"]), int(max_facts or cfg["max_facts"]))
    return seeds, [triples[i] for i in picked]


def context(brain: Brain, prompt: str) -> str:
    seeds, facts = ask(brain, prompt)
    if not facts:
        return ""
    lines = [f"[Brain KG] {len(facts)} facts the brain already holds about: {', '.join(seeds)}. Read them before "
             "answering and use them instead of asking again. The brackets give the source and trust: owner = "
             "the owner's own notes or words; a grade such as B2 = an agent fact that passed G1; unverified and "
             "agent = leads to check, not facts; inferred = added by a rule."]
    lines += [f"- {kgcore.fact_line(t)}" for t in facts]
    return "\n".join(lines)


# ---------------------------------------------------------------- memory
def remember(brain: Brain, prompt: str, session: str = "", summaries: list[str] | None = None) -> int:
    """Fold one conversation turn into the graph. Returns the number of memory triples added."""
    cfg = settings(brain)
    build(brain, use_llm=bool(cfg.get("llm_in_hooks")) and kgcore.llm_ready(cfg))
    triples = load(brain)
    index = kgcore.GraphIndex(triples)
    day = f"{brain.today:%Y-%m-%d}"
    node = f"chat {day}" + (f" {session[:8]}" if session else "")
    src = f"chat:{day}" + (f"#{session[:8]}" if session else "")
    base = {"src": src, "kind": "memory", "grade": "", "quote": "", "st": "conversation", "ot": "concept"}
    limit = int(cfg["max_memory_facts"])
    new = []
    if prompt.strip():
        for e in kgcore.match_entities(index, prompt, limit, cfg.get("stopwords", [])):
            new.append({**base, "s": node, "p": "mentions", "o": e, "trust": "owner", "method": "rule:match"})
        for t in kgcore.rule_triples({"id": src, "title": node, "text": prompt, "trust": "owner"}, cfg):
            new.append({**t, "kind": "memory", "method": "rule:chat"})
    for summary in summaries or []:
        for e in kgcore.match_entities(index, summary, limit, cfg.get("stopwords", [])):
            new.append({**base, "s": node, "p": "about", "o": e, "trust": "agent", "method": "rule:turn"})
    new = new[: limit * 3]
    if new:
        save(brain, triples + new, _state(brain))
    return len(new)


TURN_LINE_RE = re.compile(r"^- \[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\] \S+ · (.+)$")


def summaries_since(brain: Brain, stamp: str) -> list[str]:
    """Turn summaries written to the turn log at or after stamp (YYYY-MM-DD HH:MM)."""
    p = brain.path("turn_log")
    if not p.is_file():
        return []
    return [m.group(2) for line in notes.read(p).splitlines()
            if (m := TURN_LINE_RE.match(line)) and m.group(1) >= stamp]


# ---------------------------------------------------------------- other views
def stats(brain: Brain) -> dict:
    triples = load(brain)
    index = kgcore.GraphIndex(triples)
    by = lambda key: {k: sum(1 for t in triples if t.get(key) == k) for k in sorted({t.get(key) for t in triples})}
    return {"triples": len(triples), "entities": len(index.adjacency), "components": len(index.components()),
            "by_kind": by("kind"), "by_trust": by("trust"), "top": index.entities[:10],
            "built": _state(brain).get("built", ""), "stale": stale(brain) if triples else None}


def suggest(brain: Brain, limit: int = 15) -> list[dict]:
    return kgcore.suggestions(load(brain), settings(brain), documents(brain))[:limit]


def export(brain: Brain, path: Path) -> int:
    """The graph in ai-knowledge-graph's JSON shape (subject, predicate, object, …) for its viewer and graph-chat."""
    out = [{"subject": t["s"], "predicate": t["p"], "object": t["o"], "subject_type": t.get("st", ""),
            "object_type": t.get("ot", ""), "inferred": t["kind"] == "inferred", "method": t.get("method", ""),
            "source": t.get("quote") or t["src"], "trust": t.get("trust", ""), "grade": t.get("grade", "")}
           for t in load(brain)]
    notes.write(Path(path), json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    return len(out)
