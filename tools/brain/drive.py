"""The platform map: every folder and file under a brain's platform root, as a graph of locations.

A brain may name a platform root in brain.toml ([drive] root): a disk or folder that holds the whole brain platform,
its functions (the brain CLI, hooks, tools), its memory (the vault, the knowledge graph, this map, exports), its
library and its archive. The knowledge graph (kg.py) holds what the brain knows; this map holds where everything is.
Rules for agents (docs/platform-map.md):

  write  everything an agent produces is saved under the root, then mapped (`brain kg drive`; the Stop hook does it)
  read   before opening anything on the root, ask the map (`brain where`; the prompt hook shows the best hits)

Off until a brain sets [drive] enabled and root. Storage (machine-local; .gitignore keeps it out of git):
  _kg/drive-state.json   one entry per folder: mtime, sub-folders and files (name, size, mtime), or a summary when the
                         folder holds more than [drive] bulk_files files (a dataset: one node with counts)
  _kg/drive.jsonl        the map as triples in the knowledge graph's shape: kind "location", trust "system"

Only names, sizes and dates are read; the one file opened is .git/config, for a repository's remote. An update
re-reads only folders whose mtime changed (adding, removing or renaming a file changes its folder's mtime).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from . import notes
from .textnorm import fold  # noqa: F401  (also used by callers as drive.fold)
from .config import Brain, now

KIND = "location"
CATEGORIES = {
    "document": {".md", ".txt", ".pdf", ".docx", ".doc", ".html", ".htm", ".rtf", ".odt", ".pptx", ".xlsx", ".epub"},
    "code": {".py", ".js", ".ts", ".tsx", ".jsx", ".dart", ".go", ".java", ".kt", ".rs", ".c", ".cpp", ".h", ".cs",
             ".sh", ".ps1", ".cmd", ".bat", ".sql", ".css", ".scss", ".tf", ".hcl", ".yaml", ".yml", ".toml", ".ini",
             ".cfg", ".lock", ".gradle", ".iml"},
    "data": {".json", ".jsonl", ".csv", ".tsv", ".xml", ".db", ".sqlite", ".parquet", ".log"},
    "media": {".mp3", ".wav", ".ogg", ".m4a", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".mp4", ".mov",
              ".ico", ".woff", ".woff2", ".ttf", ".otf"},
    "archive": {".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".bz2"},
    "program": {".exe", ".msi", ".dll", ".apk"},
}
# Words that never locate anything: English and Vietnamese function words (marks folded) and words about files.
STOP = {"d", "c", "the", "a", "an", "of", "and", "to", "in", "on", "for", "is", "it", "va", "cua", "cho", "la", "o",
        "trong", "nay", "do", "di", "khong", "co", "duoc", "nhung", "cac", "mot", "voi", "toi", "anh", "em", "minh",
        "hay", "thi", "ma", "nhe", "roi", "vao", "ra", "len", "xuong", "den", "khi", "lam", "sao", "gi", "nao",
        "file", "files", "md", "html", "json", "py", "txt", "thu", "muc", "folder", "mo", "tim", "xem", "doc", "ghi",
        "luu", "giup", "repo", "project", "open", "find", "show", "where", "kiem", "tra", "check"}
JD_LINE = re.compile(r"^-\s+(\d\d\.\d\d)\s+([^·]+?)\s*(?:·\s*(.*))?$")
# A Windows path (D:/…) or a POSIX one (/home/…); a "/" inside a URL or a word never starts a path.
PATH_IN_TEXT = re.compile(r"((?<![\w])[A-Za-z]:[/\\][^\s,;)`'\"]+|(?<![\w:/.])/[^\s,;)`'\"]+)")


def settings(brain: Brain) -> dict:
    return brain.cfg["drive"]


def enabled(brain: Brain) -> bool:
    cfg = settings(brain)
    return bool(cfg.get("enabled") and cfg.get("root"))


def root(brain: Brain) -> Path:
    return Path(settings(brain)["root"]).expanduser()


def _key(p: Path | str) -> str:
    """A location's name in the graph: an absolute path with forward slashes."""
    s = str(p).replace("\\", "/")
    return s if not s.endswith("/") or len(s) <= 3 else s.rstrip("/")


def _parent(k: str) -> str:
    up = _key(Path(k).parent)
    return "" if up == k else up


def category(name: str) -> str:
    ext = Path(name).suffix.lower()
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cat
    return "other"


def _iso() -> str:
    return now().isoformat(timespec="seconds")


# ---------------------------------------------------------------- scan
def _state(brain: Brain) -> dict:
    f = brain.path("drive_state")
    try:
        return json.loads(notes.read(f)) if f.is_file() else {}
    except json.JSONDecodeError:
        return {}


def _git_remote(path: Path) -> str:
    try:
        text = notes.read(path / ".git" / "config")
    except OSError:
        return ""
    m = re.search(r'\[remote "origin"\][^\[]*?url\s*=\s*(\S+)', text) or re.search(r"url\s*=\s*(\S+)", text)
    return m.group(1) if m else "local"


def _read_dir(path: Path, cfg: dict) -> dict:
    skip, skip_files = set(cfg["skip"]), {s.lower() for s in cfg["skip_files"]}
    dirs, files, git = [], [], False
    with os.scandir(path) as it:
        for e in it:
            try:
                if e.is_dir(follow_symlinks=False):
                    git = git or e.name == ".git"
                    if e.name not in skip:
                        dirs.append(e.name)
                elif e.is_file(follow_symlinks=False) and e.name.lower() not in skip_files:
                    st = e.stat()
                    files.append([e.name, st.st_size, int(st.st_mtime)])
            except OSError:
                continue
    entry = {"mtime": int(path.stat().st_mtime), "dirs": sorted(dirs)}
    if git or (path / ".git").is_file():
        entry["git"] = _git_remote(path)
    if len(files) > int(cfg["bulk_files"]):
        exts: dict[str, int] = {}
        for name, _, _ in files:
            ext = Path(name).suffix.lower() or "(none)"
            exts[ext] = exts.get(ext, 0) + 1
        entry["bulk"] = {"count": len(files), "bytes": sum(f[1] for f in files),
                         "exts": dict(sorted(exts.items(), key=lambda kv: -kv[1])[:8]),
                         "newest": max(f[2] for f in files)}
    else:
        entry["files"] = sorted(files)
    return entry


def scan(brain: Brain, full: bool = False) -> dict:
    """Bring the map up to date with the disk; only folders whose mtime changed are read again."""
    cfg = settings(brain)
    base = root(brain)
    if not base.exists():
        raise FileNotFoundError(f"platform root not found: {base}")
    old = {} if full else (_state(brain).get("dirs") or {})
    new, read, depth_of, stack = {}, 0, {_key(base): 0}, [base]
    while stack:
        path = stack.pop()
        k = _key(path)
        try:
            mtime = int(path.stat().st_mtime)
        except OSError:
            continue
        prev = old.get(k)
        if prev and prev.get("mtime") == mtime:
            entry = prev
        else:
            try:
                entry = _read_dir(path, cfg)
                read += 1
            except OSError:
                continue
        new[k] = entry
        if depth_of[k] < int(cfg["max_depth"]):
            for name in entry["dirs"]:
                depth_of[_key(path / name)] = depth_of[k] + 1
                stack.append(path / name)
    notes.write(brain.path("drive_state"), json.dumps({"root": _key(base), "built": _iso(), "dirs": new},
                                                      ensure_ascii=False, separators=(",", ":")) + "\n")
    triples = graph(brain)
    notes.write(brain.path("drive_graph"), "".join(json.dumps(t, ensure_ascii=False, sort_keys=True) + "\n"
                                                   for t in triples))
    return {"folders": len(new), "read": read, "removed": len(set(old) - set(new)), "triples": len(triples),
            "files": sum(len(e.get("files", [])) + e.get("bulk", {}).get("count", 0) for e in new.values()),
            "datasets": sum(1 for e in new.values() if "bulk" in e)}


# ---------------------------------------------------------------- graph
def _t(s: str, p: str, o: str, st: str, ot: str) -> dict:
    return {"s": s, "p": p, "o": o, "st": st, "ot": ot, "src": "drive", "kind": KIND, "method": "rule:scan",
            "trust": "system", "grade": "", "quote": ""}


def jd_entries(brain: Brain) -> list[dict]:
    """JDex lines with their fields and locations: `location:` (relative to the vault) and absolute paths in `note:`."""
    rel = settings(brain).get("jd_index") or ""
    f = brain.vault / rel if rel else None
    if not f or not f.is_file():
        return []
    out, live = [], True
    for line in notes.read(f).splitlines():
        if line.startswith("#"):
            live = "format" not in line.lower()      # the template's "Line format" example is not a real number
            continue
        m = JD_LINE.match(line.strip())
        if not (live and m):
            continue
        fields = {}
        for part in (m.group(3) or "").split(" · "):
            k, _, val = part.partition(":")
            if val:
                fields[k.strip()] = val.strip()
        paths = []
        if fields.get("location"):
            loc = Path(fields["location"])
            paths.append(_key(loc if loc.is_absolute() else brain.vault / loc))
        paths += [_key(p.rstrip(".")) for p in PATH_IN_TEXT.findall(fields.get("note", ""))]
        out.append({"id": m.group(1), "name": m.group(2).strip(), "fields": fields, "paths": paths})
    return out


def graph(brain: Brain) -> list[dict]:
    """The map as triples: folders contain folders and files; JDex numbers, repositories, projects and the vault's
    notes are attached to the locations they live at."""
    dirs = _state(brain).get("dirs") or {}
    out = []
    for k, e in dirs.items():
        parent = _parent(k)
        if parent in dirs:
            out.append(_t(parent, "contains", k, "folder", "folder"))
        if "bulk" in e:
            b = e["bulk"]
            out.append(_t(k, "is a", "dataset", "folder", "type"))
            out.append(_t(k, "holds", f"{b['count']} files ({', '.join(f'{x} {n}' for x, n in b['exts'].items())})",
                          "folder", "count"))
        for name, _, _ in e.get("files", []):
            fk = f"{k.rstrip('/')}/{name}"
            out.append(_t(k, "contains", fk, "folder", "file"))
            out.append(_t(fk, "is a", category(name), "file", "type"))
        if e.get("git"):
            out.append(_t(k, "is a", "git repository", "folder", "type"))
            if e["git"] != "local":
                out.append(_t(k, "repo", e["git"], "folder", "url"))
    for j in jd_entries(brain):
        label = f"{j['id']} {j['name']}"
        for p in dict.fromkeys(j["paths"]):
            out.append(_t(label, "located at", p, "jd", "folder" if p in dirs else "path"))
        if j["fields"].get("project"):
            out.append(_t(label, "for project", j["fields"]["project"].strip("[]"), "jd", "project"))
        if j["fields"].get("repo"):
            out.append(_t(label, "repo", j["fields"]["repo"], "jd", "url"))
    try:
        from . import kg
        for d in kg.documents(brain).values():
            if d.get("path"):
                out.append(_t(d["title"].lower(), "stored at", _key(d["path"]), d["kind"], "file"))
    except Exception:  # noqa: BLE001 - the map must build even when a note cannot be read
        pass
    seen, uniq = set(), []
    for t in out:
        if (t["s"], t["p"], t["o"]) not in seen:
            seen.add((t["s"], t["p"], t["o"]))
            uniq.append(t)
    return uniq


def load(brain: Brain) -> list[dict]:
    f = brain.path("drive_graph")
    if not f.is_file():
        return []
    return [json.loads(line) for line in notes.read(f).splitlines() if line.strip()]


# ---------------------------------------------------------------- read
def tokens(text: str, extra_stop=()) -> list[str]:
    raw = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(text))
    stop = STOP | {fold(s) for s in extra_stop}
    return [w for w in re.split(r"[^a-z0-9]+", fold(raw)) if len(w) >= 2 and w not in stop]


def where(brain: Brain, query: str, limit: int | None = None) -> list[dict]:
    """The locations that best match a question, best first: 3 per query word in a location's own name or labels,
    1 per word only in a parent folder, +2 when every word matched, +3 per pair of words side by side in order,
    -3 under a [drive] demote folder."""
    cfg = settings(brain)
    q = list(dict.fromkeys(tokens(query, cfg.get("stopwords", []))))
    if not q:
        return []
    triples = load(brain)
    labels: dict[str, list[str]] = {}
    for t in triples:
        if t["p"] in ("located at", "stored at"):
            labels.setdefault(t["o"], []).append(t["s"])
    for t in triples:
        if t["p"] == "for project":
            for x in triples:
                if x["s"] == t["s"] and x["p"] == "located at":
                    labels.setdefault(x["o"], []).append(t["o"])
    kinds, info = {}, {}
    for t in triples:
        if t["p"] == "is a":
            kinds.setdefault(t["s"], []).append(t["o"])
        elif t["p"] in ("holds", "repo") and t["st"] == "folder":
            info.setdefault(t["s"], []).append(t["o"])
    nodes = {t["s"] for t in triples if t["st"] in ("folder", "file")} | \
            {t["o"] for t in triples if t["ot"] in ("folder", "file")}
    hits = []
    for n in nodes:
        name = n.rstrip("/").rsplit("/", 1)[-1]
        own = set(tokens(name)) | {w for lab in labels.get(n, []) for w in tokens(lab)}
        strong = [w for w in q if w in own or any(o.startswith(w) and len(w) >= 4 for o in own)]
        if not strong:
            continue
        above = set(tokens(n.rsplit("/", 1)[0]))
        weak = [w for w in q if w not in strong and w in above]
        score = 3 * len(strong) + len(weak) + (2 if len(strong) + len(weak) == len(q) else 0)
        flat = " " + " ".join(tokens(name)) + " "
        score += 3 * sum(1 for a, b in zip(q, q[1:]) if f" {a} {b} " in flat)
        if any(f"/{d}/" in f"{n}/" for d in cfg.get("demote", [])):
            score -= 3
        hits.append({"path": n, "score": score, "kinds": kinds.get(n, []), "labels": sorted(set(labels.get(n, []))),
                     "info": info.get(n, []), "depth": n.count("/")})
    hits.sort(key=lambda h: (-h["score"], h["depth"], h["path"]))
    return hits[: int(limit or cfg["max_hits"])]


def line(h: dict) -> str:
    bits = [h["path"]]
    if h["kinds"]:
        bits.append("/".join(h["kinds"]))
    if h["labels"]:
        bits.append("; ".join(h["labels"][:3]))
    if h["info"]:
        bits.append("; ".join(h["info"][:2]))
    return " · ".join(bits)


def context(brain: Brain, prompt: str) -> str:
    """What the prompt hook adds: where the things a prompt names live on the platform root."""
    hits = [h for h in where(brain, prompt) if h["score"] >= int(settings(brain)["min_score"])]
    if not hits:
        return ""
    lines = [f"[Brain Drive] {len(hits)} locations on the platform root ({_key(root(brain))}) that match the prompt. "
             "Read these from the map before searching the disk; save anything you produce under the root "
             "(docs/platform-map.md)."]
    return "\n".join(lines + [f"- {line(h)}" for h in hits])


def stats(brain: Brain) -> dict:
    st = _state(brain)
    dirs = st.get("dirs") or {}
    return {"root": st.get("root", ""), "built": st.get("built", ""), "folders": len(dirs),
            "files": sum(len(e.get("files", [])) + e.get("bulk", {}).get("count", 0) for e in dirs.values()),
            "datasets": sum(1 for e in dirs.values() if "bulk" in e),
            "repositories": sum(1 for e in dirs.values() if e.get("git")),
            "bytes": sum(sum(f[1] for f in e.get("files", [])) + e.get("bulk", {}).get("bytes", 0)
                         for e in dirs.values())}


# ---------------------------------------------------------------- draw
def draw_data(brain: Brain, with_files: bool = False, with_knowledge: bool = True) -> dict:
    """Nodes and links for the viewer: folders (and files when asked), JDex numbers, repositories and the knowledge
    graph's entities linked to the folders their notes live in."""
    st = _state(brain)
    dirs = st.get("dirs") or {}
    nodes, links = {}, []

    def node(i, kind, label, **extra):
        nodes.setdefault(i, {"id": i, "kind": kind, "label": label, **extra})

    for k, e in dirs.items():
        files, b = e.get("files", []), e.get("bulk")
        node(k, "dataset" if b else ("repo" if e.get("git") else "folder"), k.rstrip("/").rsplit("/", 1)[-1] or k,
             path=k, files=b["count"] if b else len(files), bytes=b["bytes"] if b else sum(f[1] for f in files),
             git=e.get("git", ""), exts=b["exts"] if b else {})
        if _parent(k) in dirs:
            links.append({"source": _parent(k), "target": k, "kind": "contains"})
        if with_files:
            for fname, size, _ in files:
                fk = f"{k.rstrip('/')}/{fname}"
                node(fk, "file", fname, path=fk, bytes=size, category=category(fname))
                links.append({"source": k, "target": fk, "kind": "contains"})
    triples = load(brain)
    for t in triples:
        if t["p"] == "located at" and t["o"] in nodes:
            node("jd:" + t["s"], "jd", t["s"])
            links.append({"source": "jd:" + t["s"], "target": t["o"], "kind": "jd"})
    if with_knowledge:
        try:
            from . import kg
            stored = {t["s"]: t["o"] for t in triples if t["p"] == "stored at"}
            for t in kg.load(brain):
                if t["kind"] == "inferred":
                    continue
                node("kg:" + t["s"], "concept", t["s"])
                node("kg:" + t["o"], "concept", t["o"])
                links.append({"source": "kg:" + t["s"], "target": "kg:" + t["o"], "kind": "knows", "p": t["p"]})
            for title, path in stored.items():
                folder = path.rsplit("/", 1)[0]
                if "kg:" + title in nodes and folder in nodes:
                    links.append({"source": "kg:" + title, "target": folder, "kind": "stored"})
        except Exception:  # noqa: BLE001
            pass
    return {"root": st.get("root", ""), "built": st.get("built", ""), "nodes": list(nodes.values()), "links": links}
