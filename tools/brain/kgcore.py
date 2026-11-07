"""Knowledge graph core: turn the brain's documents into subject → predicate → object triples, and read them back.

Portable on purpose: it knows nothing about the vault. A caller hands it documents and the [kg] configuration;
it hands back triples, retrieved facts and suggestions. Standard library only.

The pipeline follows robert-mcdermott/ai-knowledge-graph (Apache License 2.0): chunk the text, ask an LLM for
S-P-O triples, standardise entity names, infer a few missing edges, and answer questions from the neighbourhood
of the entities a question mentions. The extraction prompt, the singularisation rule and the retrieval ranking
(seed-to-seed paths first, then by hop distance) are adapted from that project; see NOTICE.md. Unlike it, every
triple here carries where it came from and how far it can be trusted, and the graph also builds without an LLM
from what the notes already say explicitly (links, tags, frontmatter, short "X is Y" sentences).

A document:  {"id", "kind", "title", "text", "links": [titles], "tags": [...], "relations": [(p, o)], "trust", "grade"}
A triple:    {"s", "p", "o", "st", "ot", "src", "kind", "method", "trust", "grade", "quote"}
  kind   note (from a document) · memory (from a conversation) · inferred (added by a rule)
  trust  dave or owner (the brain owner's own notes and words) · graded (an agent fact that passed G1; see grade) ·
         unverified (source D/F, or G1 has not checked it) · agent (written by an agent, never through G1)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from collections import defaultdict, deque

TRUST_ORDER = ["dave", "owner", "graded", "unverified", "agent"]   # most trusted first; retrieval prefers the left
TITLE_TYPES = {"note", "task", "project", "area", "map", "conversation"}   # entities that are titles, not concepts

_WORD = re.compile(r"[^\W_][\w\-']*", re.UNICODE)
_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+|\n+")
_STOP_EN = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "by", "from", "at", "as", "is", "are",
    "was", "were", "be", "been", "it", "its", "this", "that", "these", "those", "what", "which", "who", "whom",
    "how", "why", "when", "where", "did", "do", "does", "has", "have", "had", "can", "could", "would", "should",
    "about", "into", "than", "then", "there", "their", "they", "them", "between", "tell", "me", "us", "any",
    "some", "all", "most", "many", "much", "over", "under", "please", "you", "your", "my", "our", "we", "i",
}
_STOP_VI = {
    "và", "hoặc", "của", "cho", "với", "là", "thì", "mà", "những", "các", "một", "này", "kia", "đó", "được", "bị",
    "có", "không", "gì", "nào", "sao", "thế", "như", "để", "khi", "đã", "đang", "sẽ", "rồi", "cũng", "vẫn", "ra",
    "vào", "lên", "xuống", "tôi", "bạn", "mình", "anh", "chị", "em", "nó", "họ", "ta", "đi", "lại", "nữa", "hãy",
    "giúp", "xem", "làm", "trong", "trên", "dưới", "ở", "tại", "từ", "theo", "về", "nhé", "nha", "ạ", "à", "ơi",
}
_PLURAL_EXCEPTIONS = {"news", "physics", "mathematics", "series", "species", "analysis", "basis", "crisis", "status",
                      "bus", "gas", "lens", "chaos", "process", "access", "address", "business", "class", "glass"}


# ---------------------------------------------------------------- names
def _singularize(word: str) -> str:
    """Cheap English singularisation used only to group variants ("factories"/"factory"). Leaves other words alone."""
    if not word.isascii() or len(word) <= 3 or word in _PLURAL_EXCEPTIONS or word.endswith(("ss", "us", "is")):
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith(("sses", "xes", "ches", "shes", "zes")):
        return word[:-2]
    if word.endswith("s"):
        return word[:-1]
    return word


def norm(name: str, max_len: int = 120) -> str:
    """The canonical form of an entity: lower case, single spaces, no wrapping punctuation or leading article."""
    s = re.sub(r"\s+", " ", str(name or "")).strip().strip(" .,:;!?\"'`*_").lower()
    while len(s) > 1 and s[0] + s[-1] in ("()", "[]", "{}", "<>"):   # only a pair that wraps the whole name
        s = s[1:-1].strip()
    s = re.sub(r"^(the|a|an) ", "", s)
    if s and " " not in s:
        s = _singularize(s)
    elif s:
        head, _, last = s.rpartition(" ")
        s = f"{head} {_singularize(last)}"
    return s[:max_len].strip()


def words(text: str, extra_stop=()) -> set[str]:
    stop = _STOP_EN | _STOP_VI | set(extra_stop)
    return {_singularize(w) for w in (m.group(0).lower() for m in _WORD.finditer(text or ""))
            if len(w) >= 2 and w not in stop and not w.isdigit()}


def _short(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


# ---------------------------------------------------------------- rule extraction (no LLM)
def sentences(text: str) -> list[str]:
    out = []
    for raw in _SENTENCE_END.split(text or ""):
        s = re.sub(r"^\s*(?:[-*+]|\d+[.)]|#+|>)\s*", "", raw).strip()
        s = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", s)
        s = re.sub(r"[*_`]", "", s)
        if s:
            out.append(s)
    return out


def _verb_re(cfg: dict) -> re.Pattern:
    verbs = sorted({v.strip().lower() for v in cfg.get("sentence_verbs", []) if v.strip()}, key=len, reverse=True)
    if not verbs:
        return re.compile(r"(?!x)x")
    return re.compile(r"\s(" + "|".join(re.escape(v) for v in verbs) + r")\s", re.IGNORECASE)


def sentence_triples(text: str, cfg: dict) -> list[tuple[str, str, str, str]]:
    """Short "X <verb> Y" sentences → (subject, predicate, object, sentence). Bounded lengths keep the noise low."""
    rx = _verb_re(cfg)
    max_s, max_o = int(cfg.get("sentence_max_subject_words", 6)), int(cfg.get("sentence_max_object_words", 8))
    out = []
    for s in sentences(text):
        m = rx.search(" " + s + " ")
        if not m:
            continue
        subj, obj = (" " + s + " ")[: m.start()].strip(), (" " + s + " ")[m.end():].strip()
        if not subj or not obj:
            continue
        if len(subj.split()) > max_s or len(obj.split()) > max_o:
            continue
        out.append((subj, m.group(1).lower(), obj, s))
    return out


def rule_triples(doc: dict, cfg: dict) -> list[dict]:
    """Triples a document states outright: its links, tags and fields, and its short "X is Y" sentences."""
    title = doc.get("title") or doc["id"]
    base = {"src": doc["id"], "kind": "note", "trust": doc.get("trust", "dave"), "grade": doc.get("grade", "")}
    out = []

    def add(s, p, o, method, st="concept", ot="concept", quote=""):
        s2, o2 = norm(s), norm(o)
        if s2 and o2 and s2 != o2:
            out.append({**base, "s": s2, "p": p, "o": o2, "st": st, "ot": ot, "method": method,
                        "quote": _short(quote, 200)})

    kind_type = {"project": "project", "area": "area", "next": "task", "moc": "map"}.get(doc.get("kind"), "note")
    for target in doc.get("links", []):
        add(title, "links to", target, "rule:link", kind_type, "note")
    for tag in doc.get("tags", []):
        add(title, "tagged", tag, "rule:tag", kind_type, "topic")
    for p, o in doc.get("relations", []):
        add(title, p, o, "rule:field", kind_type, "concept")
    if cfg.get("sentence_rules", True):
        for s, p, o, quote in sentence_triples(doc.get("text", ""), cfg):
            add(s, p, o, "rule:sentence", "concept", "concept", quote)
    return out


# ---------------------------------------------------------------- LLM extraction (optional)
# Adapted from ai-knowledge-graph's MAIN_SYSTEM_PROMPT / MAIN_USER_PROMPT (Apache-2.0); shortened, and told to keep
# the document's language because Dave writes in Vietnamese.
LLM_SYSTEM = ("You extract knowledge graph triples. Identify consistent entity names and meaningful relationships. "
              "Every predicate is 1 to 3 words.")
LLM_USER = """Read the text between triple backticks and list every Subject-Predicate-Object relationship in it.

Rules:
- Use one consistent name per entity (the most complete form); replace pronouns with the entity they refer to.
- Keep entities atomic and general ("computing", not "modern computing devices"); add a separate "is a" triple for a
  specific kind of a general concept.
- Predicates are 1 to 3 words. All text in lower case. Keep the language of the text; do not translate.
- Only relationships the text states or plainly implies. Never add outside knowledge.
- Entity types: person, organization, place, event, technology, product, work, date, concept.

Return only a JSON array of objects with "subject", "predicate", "object", "subject_type", "object_type".

```
{text}
```"""


def chunk_words(text: str, size: int = 100, overlap: int = 20) -> list[str]:
    ws = (text or "").split()
    if not ws:
        return []
    size, overlap = max(1, size), max(0, min(overlap, size - 1))
    return [" ".join(ws[i:i + size]) for i in range(0, max(len(ws) - overlap, 1), size - overlap)]


def llm_ready(cfg: dict) -> bool:
    mode = str(cfg.get("llm", "auto")).lower()
    return mode == "on" or (mode == "auto" and bool(cfg.get("llm_base_url")) and bool(cfg.get("llm_model")))


def llm_chat(cfg: dict, system: str, user: str) -> str:
    """One call to an OpenAI-compatible chat completions endpoint (Ollama, vLLM, LiteLLM, OpenRouter…)."""
    url = cfg.get("llm_base_url") or ""
    if not url:
        raise RuntimeError("kg.llm_base_url is not set")
    body = {"model": cfg.get("llm_model"), "temperature": float(cfg.get("llm_temperature", 0.2)),
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    headers = {"Content-Type": "application/json"}
    key_env = cfg.get("llm_api_key_env") or ""
    if key_env and os.environ.get(key_env):
        headers["Authorization"] = "Bearer " + os.environ[key_env]
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=float(cfg.get("llm_timeout", 120))) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"] or ""


def parse_json_array(text: str) -> list | None:
    """The first JSON array in a model reply, ignoring reasoning blocks and code fences."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.S)
    for cand in fenced + [text]:
        start = cand.find("[")
        while start != -1:
            depth = 0
            for i in range(start, len(cand)):
                depth += {"[": 1, "]": -1}.get(cand[i], 0)
                if depth == 0:
                    try:
                        val = json.loads(cand[start:i + 1])
                        if isinstance(val, list):
                            return val
                    except json.JSONDecodeError:
                        pass
                    break
            start = cand.find("[", start + 1)
    return None


def llm_triples(doc: dict, cfg: dict, chat=llm_chat) -> list[dict]:
    """Triples an LLM reads out of a document's text. Same source and trust as the document: the model only
    restructures what the document says, and the method field shows it was read by a model."""
    base = {"src": doc["id"], "kind": "note", "trust": doc.get("trust", "dave"), "grade": doc.get("grade", "")}
    max_p = int(cfg.get("max_predicate_words", 3))
    out = []
    for chunk in chunk_words(doc.get("text", ""), int(cfg.get("chunk_words", 100)), int(cfg.get("chunk_overlap", 20))):
        reply = chat(cfg, LLM_SYSTEM, LLM_USER.replace("{text}", chunk))
        for t in parse_json_array(reply) or []:
            if not isinstance(t, dict):
                continue
            s, p, o = norm(t.get("subject", "")), re.sub(r"\s+", " ", str(t.get("predicate", ""))).strip().lower(), \
                norm(t.get("object", ""))
            if not s or not o or not p or s == o or len(p.split()) > max_p:
                continue
            out.append({**base, "s": s, "p": p, "o": o, "st": str(t.get("subject_type") or "concept"),
                        "ot": str(t.get("object_type") or "concept"), "method": "llm", "quote": ""})
    return out


# ---------------------------------------------------------------- standardise and infer
def dedupe(triples: list[dict]) -> list[dict]:
    seen, out = set(), []
    for t in triples:
        key = (t["s"], t["p"], t["o"], t["src"], t["kind"])
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


def infer(triples: list[dict], cfg: dict) -> list[dict]:
    """Taxonomy rule from ai-knowledge-graph: "quantum computing" is a "computing". For head-first languages such as
    Vietnamese the general term comes first ("mô hình pkm" is a "mô hình"). Capped at max_inferred_ratio."""
    if not cfg.get("infer_taxonomy", True):
        return []
    have = {t["s"] for t in triples} | {t["o"] for t in triples}
    pairs = {(t["s"], t["o"]) for t in triples} | {(t["o"], t["s"]) for t in triples}
    titles = {t["s"] for t in triples if t.get("st") in TITLE_TYPES} | {t["o"] for t in triples if t.get("ot") in TITLE_TYPES}
    min_len, max_words = int(cfg.get("infer_min_chars", 4)), int(cfg.get("infer_max_words", 4))
    out = []
    for e in sorted(have - titles):   # a note title is a claim, not a kind of something
        ws = e.split()
        if len(ws) < 2 or len(ws) > max_words:
            continue
        heads = [" ".join(ws[i:]) for i in range(1, len(ws))] if e.isascii() else \
                [" ".join(ws[:i]) for i in range(len(ws) - 1, 0, -1)]
        for h in heads:
            if len(h) >= min_len and h in have and (e, h) not in pairs:
                out.append({"s": e, "p": "is a", "o": h, "st": "concept", "ot": "concept", "src": "rule",
                            "kind": "inferred", "method": "rule:taxonomy", "trust": "agent", "grade": "", "quote": ""})
                break
    cap = int(len([t for t in triples if t["kind"] != "inferred"]) * float(cfg.get("max_inferred_ratio", 0.5)))
    return out[:cap]


# ---------------------------------------------------------------- read back
class GraphIndex:
    """In-memory index of a triples list for retrieval (from ai-knowledge-graph's query.GraphIndex)."""

    def __init__(self, triples: list[dict]):
        self.triples = triples
        self.adjacency: dict[str, set[str]] = defaultdict(set)
        self.by_pair: dict[tuple[str, str], list[int]] = defaultdict(list)
        self.degree: dict[str, int] = defaultdict(int)
        for i, t in enumerate(triples):
            s, o = t["s"], t["o"]
            self.adjacency[s].add(o)
            self.adjacency[o].add(s)
            self.by_pair[(s, o)].append(i)
            self.by_pair[(o, s)].append(i)
            self.degree[s] += 1
            self.degree[o] += 1

    @property
    def entities(self) -> list[str]:
        return sorted(self.adjacency, key=lambda n: (-self.degree[n], n))

    def components(self) -> list[set[str]]:
        seen, comps = set(), []
        for start in self.entities:
            if start in seen:
                continue
            comp, queue = set(), deque([start])
            while queue:
                n = queue.popleft()
                if n in comp:
                    continue
                comp.add(n)
                queue.extend(self.adjacency[n] - comp)
            seen |= comp
            comps.append(comp)
        return sorted(comps, key=len, reverse=True)


def match_entities(index: GraphIndex, question: str, limit: int = 6, extra_stop=()) -> list[str]:
    """Entities a question is about: whole names first (longest wins), then names sharing content words."""
    q = " " + " ".join(m.group(0).lower() for m in _WORD.finditer(question or "")) + " "
    matched = [n for n in index.adjacency if len(n) >= 2 and f" {n} " in q]
    matched = [n for n in matched if not any(n != m and f" {n} " in f" {m} " for m in matched)]
    matched.sort(key=lambda n: (-len(n), -index.degree[n]))
    if len(matched) < limit:
        qw = words(question, extra_stop)
        cands = []
        for name in index.entities:
            if name in matched:
                continue
            nw = words(name, extra_stop) or {name}
            overlap = len(nw & qw)
            if overlap:
                cands.append((-overlap / len(nw), -index.degree[name], name))
        cands.sort()
        matched += [n for _, _, n in cands[: limit - len(matched)]]
    return matched[:limit]


def _shortest_path(index: GraphIndex, a: str, b: str, max_depth: int = 6):
    parent, queue = {a: None}, deque([(a, 0)])
    while queue:
        node, d = queue.popleft()
        if node == b:
            path = [b]
            while parent[path[-1]] is not None:
                path.append(parent[path[-1]])
            return path[::-1]
        if d < max_depth:
            for n in index.adjacency[node]:
                if n not in parent:
                    parent[n] = node
                    queue.append((n, d + 1))
    return None


def retrieve(index: GraphIndex, seeds: list[str], hops: int = 2, max_triples: int = 15) -> list[int]:
    """Triple indices around the seeds: seed-to-seed paths first, then by hop distance, trust, inferred last."""
    seeds = [s for s in seeds if s in index.adjacency]
    if not seeds:
        return []
    dist, queue = {s: 0 for s in seeds}, deque(seeds)
    while queue:
        n = queue.popleft()
        if dist[n] < hops:
            for m in index.adjacency[n]:
                if m not in dist:
                    dist[m] = dist[n] + 1
                    queue.append(m)
    chosen, seen = [], set()

    def add(ids):
        for i in ids:
            if i not in seen:
                seen.add(i)
                chosen.append(i)

    for i, a in enumerate(seeds):
        for b in seeds[i + 1:]:
            path = _shortest_path(index, a, b)
            for u, w in zip(path or [], (path or [])[1:]):
                add(index.by_pair[(u, w)][:1])
    ranked = []
    for i, t in enumerate(index.triples):
        if i in seen:
            continue
        ds, do = dist.get(t["s"]), dist.get(t["o"])
        if ds is None and do is None:
            continue
        d = min(x for x in (ds, do) if x is not None)
        trust = TRUST_ORDER.index(t.get("trust")) if t.get("trust") in TRUST_ORDER else len(TRUST_ORDER)
        ranked.append((d, 0 if ds is not None and do is not None else 1, t.get("kind") == "inferred", trust,
                       -(index.degree[t["s"]] + index.degree[t["o"]]), i))
    ranked.sort()
    add(i for *_, i in ranked)
    return chosen[:max_triples]


def fact_line(t: dict) -> str:
    """One fact with its provenance, for an agent's context or a person's screen."""
    where = t["src"] if t["kind"] != "inferred" else "inferred"
    trust = t.get("trust", "")
    if trust == "graded" and t.get("grade"):
        trust = t["grade"]
    how = "" if t.get("method", "").startswith("rule:") else f" · {t.get('method')}"
    return f"{t['s']} → {t['p']} → {t['o']}  [{where} · {trust}{how}]"


# ---------------------------------------------------------------- suggestions
def suggestions(triples: list[dict], cfg: dict, documents: dict[str, dict]) -> list[dict]:
    """What the graph says is missing. Each suggestion names its evidence; none of them writes anything."""
    index = GraphIndex(triples)
    out = []
    comps = index.components()
    if len(comps) > 1:
        main = comps[0]
        for comp in comps[1:]:
            notes = sorted({t["src"] for t in triples if t["s"] in comp and t["src"] in documents})
            if not notes:
                continue
            ws = set().union(*(words(e) for e in comp))
            near = [e for e in sorted(main, key=lambda n: -index.degree[n]) if words(e) & ws][:3]
            names = sorted(comp, key=lambda n: -index.degree[n])[:3]
            out.append({"kind": "link", "score": len(comp),
                        "text": "Connect " + ", ".join(f'"{n}"' for n in names) + " to the rest of the brain"
                                + (f"; it shares words with: {'; '.join(near)}" if near else ""),
                        "evidence": f"an island of {len(comp)} entities, from {', '.join(notes[:3])}, "
                                    "not linked to the main graph"})
    titled = {norm(d.get("title", "")) for d in documents.values() if d.get("kind") == "permanent"}
    named = {t["s"] for t in triples if t.get("st") in TITLE_TYPES | {"topic"}} | \
            {t["o"] for t in triples if t.get("ot") in TITLE_TYPES | {"topic"}}   # titles and tags: MOCs cover tags (R11)
    min_degree = int(cfg.get("suggest_min_degree", 4))
    for e in index.entities[: int(cfg.get("suggest_hubs", 25))]:
        if index.degree[e] >= min_degree and e not in titled and e not in named:
            out.append({"kind": "note", "score": index.degree[e],
                        "text": f"Write a permanent note in your own words on \"{e}\"",
                        "evidence": f"{index.degree[e]} facts mention it and no permanent note is about it"})
    memory = defaultdict(set)
    for t in triples:
        if t["kind"] == "memory" and t["p"] == "mentions":
            memory[t["o"]].add(t["s"])
    for e, chats in memory.items():
        notes = {t["src"] for t in triples if t["kind"] == "note" and e in (t["s"], t["o"])}
        if len(chats) >= int(cfg.get("suggest_min_chats", 3)) and not notes:
            out.append({"kind": "capture", "score": len(chats),
                        "text": f"Clarify \"{e}\": it keeps coming up in chats but no note holds it",
                        "evidence": f"mentioned in {len(chats)} conversations, in 0 notes"})
    for e in index.entities[: int(cfg.get("suggest_hubs", 25))]:
        weak = [t for t in triples if e in (t["s"], t["o"]) and t.get("trust") in ("unverified", "agent")
                and t["kind"] != "inferred"]
        if len(weak) >= 2:
            out.append({"kind": "verify", "score": len(weak),
                        "text": f"Check the unverified facts about \"{e}\" through G1 before relying on them",
                        "evidence": f"{len(weak)} facts about a central entity are unverified or agent-written"})
    empty = [d for d in documents.values() if d.get("kind") in ("permanent", "literature")
             and not any(t["src"] == d["id"] for t in triples)]
    for d in empty[:10]:
        out.append({"kind": "link", "score": 1, "text": f"Add links or tags to {d['id']}",
                    "evidence": "the note adds no fact to the graph"})
    order = {"verify": 0, "link": 1, "note": 2, "capture": 3}
    out.sort(key=lambda s: (order.get(s["kind"], 9), -s["score"]))
    return out


def digest(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]
