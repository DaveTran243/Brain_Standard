"""The script library (ADR-21, docs/script-library.md): every script an AI generates is kept on the owner's disk,
filed by topic, with one variant per operating system.

Layout, inside the files and code lane (Johnny Decimal, category [scripts] category, 52 by default):

  Code/52 Scripts/                       [paths] scripts
    52.02 network/                       one topic = one AC.ID, with its line in the JDex first
      check-port.md                      the manifest: purpose, who generated it, from which request, its variants
      check-port.linux.sh                <name>.<os>.<ext>: one file per operating system
      check-port.rhel.sh
      check-port.macos.sh
      check-port.windows.ps1
  _log/scripts.md                        every file added or changed, with its sha256 (written by brain commands only)

Nothing is nested below the AC.ID (lane rule 3): the operating system is part of the file name, not a folder.
A variant named <name>.any.<ext> (Python, for instance) covers every operating system.

The library is also a small code knowledge graph: each script enters the brain's graph (kind "script") with the
topic it is in, the operating systems it runs on, the commands it calls and the modules it imports, extracted by
rules, never by running anything.
"""
from __future__ import annotations

import fnmatch
import hashlib
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import notes, textnorm
from .config import Brain, BrainError

VARIANT_RE = re.compile(r"^(?P<name>[a-z0-9][a-z0-9-]*)\.(?P<os>[a-z0-9]+)\.(?P<ext>[A-Za-z0-9]+)$")
TOPIC_DIR_RE = re.compile(r"^(?P<cat>\d\d)\.(?P<id>\d\d)\s+(?P<name>.+)$")
LOG_HEADER = "# Script log\n\nEvery script file added to or changed in the library, with its sha256. Written by brain commands.\n\n"
VARIANTS_HEADING = "## Variants"

# Words that start a shell line but are not commands the script depends on.
SHELL_WORDS = set("""if then else elif fi for while until do done case esac in function return local export echo printf
set unset read shift exit test true false break continue declare readonly trap source eval cd pwd let typeset shopt
wait time exec sudo command builtin select getopts printf umask alias unalias type hash nohup env xargs""".split())
PS_WORDS = set("""if else elseif foreach for while do until switch function filter param return try catch finally throw
begin process end trap break continue exit class enum using data dynamicparam""".split())
CMDLET_RE = re.compile(r"\b([A-Z][a-z]+-[A-Z][A-Za-z]+)\b")
PY_IMPORT_RE = re.compile(r"^\s*(?:from\s+([A-Za-z_][\w.]*)\s+import|import\s+([A-Za-z_][\w.]*))", re.M)
SPLIT_RE = re.compile(r"\|\||&&|[|;&]|\$\(|`|\bthen\b|\bdo\b|\belse\b")
FUNC_DEF_RE = re.compile(r"^\s*(?:function\s+)?([A-Za-z_][\w-]*)\s*\(\s*\)", re.M)
TOKEN_RE = re.compile(r"^[A-Za-z][\w.+-]*$")
WINDOWS_EXT = {".ps1", ".psm1", ".bat", ".cmd"}
RUN_HINT = {".sh": "bash {f}", ".bash": "bash {f}", ".zsh": "zsh {f}", ".command": "zsh {f}",
            ".ps1": "pwsh -File {f}  (Windows PowerShell: powershell -ExecutionPolicy Bypass -File {f})",
            ".psm1": "Import-Module ./{f}", ".bat": "{f}", ".cmd": "{f}", ".py": "python3 {f}  (Windows: py {f})"}


def settings(brain: Brain) -> dict:
    return brain.cfg["scripts"]


def library(brain: Brain) -> Path:
    return brain.path("scripts")


def _rel(brain: Brain, p: Path) -> str:
    try:
        return brain.rel(p)
    except ValueError:
        return p.as_posix()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- topics
@dataclass
class Topic:
    id: str              # "52.02"
    name: str            # "network"
    keywords: list[str] = field(default_factory=list)

    @property
    def folder_name(self) -> str:
        return f"{self.id} {self.name}"


def topics(brain: Brain) -> dict[str, Topic]:
    """Topics from [scripts.topics] and from folders already in the library, by AC.ID."""
    cfg = settings(brain)
    cat = str(cfg["category"])
    out: dict[str, Topic] = {}
    for key, t in (cfg.get("topics") or {}).items():
        tid = f"{cat}.{int(key):02d}"
        out[tid] = Topic(tid, t["name"], list(t.get("keywords", [])))
    lib = library(brain)
    if lib.is_dir():
        for d in sorted(lib.iterdir()):
            m = TOPIC_DIR_RE.match(d.name)
            if d.is_dir() and m and m.group("cat") == cat:
                tid = f"{cat}.{m.group('id')}"
                if tid in out:
                    out[tid].name = m.group("name").strip()
                else:
                    out[tid] = Topic(tid, m.group("name").strip())
    return dict(sorted(out.items()))


def resolve_topic(brain: Brain, value: str) -> Topic:
    """A topic from "52.02", "02", "2" or its name."""
    ts = topics(brain)
    v = (value or "").strip()
    cat = str(settings(brain)["category"])
    if re.fullmatch(r"\d{1,2}", v):
        v = f"{cat}.{int(v):02d}"
    if v in ts:
        return ts[v]
    for t in ts.values():
        if textnorm.fold(t.name) == textnorm.fold(v) or textnorm.fold(t.folder_name) == textnorm.fold(v):
            return t
    raise BrainError(f"No script topic '{value}'. Topics: " + ", ".join(t.folder_name for t in ts.values())
                     + ". Add one in brain.toml under [scripts.topics].")


def classify(brain: Brain, text: str, commands: set[str] | None = None) -> tuple[Topic, int]:
    """The topic whose keywords the text (name, purpose, request) and the commands match best, and its score.
    Score 0 means nothing matched: the fallback topic, for the Weekly Review to file."""
    words = textnorm.words(text)
    folded = " " + " ".join(words) + " "
    cmds = {textnorm.fold(c) for c in (commands or set())}
    best, score = None, 0
    for t in topics(brain).values():
        s = 0
        for k in t.keywords:
            fk = textnorm.fold(k)
            s += 3 * folded.count(f" {fk} ") + (1 if fk in cmds else 0)
        if s > score:
            best, score = t, s
    if best is None:
        best = resolve_topic(brain, str(settings(brain)["fallback_topic"]))
    return best, score


def _jd_has(brain: Brain, tid: str) -> bool:
    index = brain.vault / brain.cfg["drive"]["jd_index"]
    return index.is_file() and re.search(rf"^-\s+{re.escape(tid)}\s", notes.read(index), re.M) is not None


def ensure_topic(brain: Brain, t: Topic) -> Path:
    """The topic's folder, after its JDex line (lane rule 1: the line first, then the folder)."""
    folder = library(brain) / t.folder_name
    index = brain.vault / brain.cfg["drive"]["jd_index"]
    if not _jd_has(brain, t.id):
        cat = str(settings(brain)["category"])
        loc = _rel(brain, folder) + "/"
        line = f"- {t.id} {t.name} · location: {loc} · status: in use"
        text = notes.read(index) if index.is_file() else "# Index (JDex)\n"
        lines = text.splitlines()
        heading = f"## {cat} {settings(brain)['category_name']}"
        if heading in lines:
            i = lines.index(heading) + 1
            while i < len(lines) and not lines[i].startswith("## "):
                i += 1
            while i > 0 and not lines[i - 1].strip():
                i -= 1
            lines.insert(i, line)
        else:
            block = [heading, line, ""]
            at = next((i for i, l in enumerate(lines) if l.startswith("## ") and "format" in l.lower()), len(lines))
            if at == len(lines) and lines and lines[-1].strip():
                block = ["", *block]
            lines[at:at] = block
        notes.write(index, "\n".join(lines).rstrip("\n") + "\n")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# ---------------------------------------------------------------- reading scripts
def os_names(brain: Brain) -> list[str]:
    return list(settings(brain)["os"].keys())


def commands(text: str, ext: str) -> set[str]:
    """The external commands a script calls, by rules: the first word of each shell pipeline stage, PowerShell
    cmdlets (Verb-Noun) and native programs. Keywords, builtins and the script's own functions are left out."""
    out: set[str] = set()
    ext = ext.lower()
    if ext == ".py":
        return out
    if ext in {".ps1", ".psm1"}:
        out |= set(CMDLET_RE.findall(text))
        text = re.sub(r"<#.*?#>", "", text, flags=re.S)
    own = set(FUNC_DEF_RE.findall(text))
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "::", "REM ", "rem ", "@REM")):
            continue
        line = re.sub(r"(^|\s)#.*$", "", line)
        for part in SPLIT_RE.split(line):
            toks = part.strip().lstrip("({!").split()
            while toks and (re.match(r"^[A-Za-z_]\w*=", toks[0]) or toks[0] in {"sudo", "exec", "time", "nohup",
                                                                               "command", "env", "xargs", "!"}):
                toks = toks[1:]
                while toks and toks[0].startswith("-"):
                    toks = toks[1:]
            if not toks:
                continue
            tok = toks[0].strip("\"'")
            low = tok.lower()
            if ext in {".bat", ".cmd"}:
                tok = low.lstrip("@")
            if not TOKEN_RE.match(tok) or low in SHELL_WORDS or low in PS_WORDS or tok in own:
                continue
            if ext in {".ps1", ".psm1"} and not (CMDLET_RE.fullmatch(tok) or re.fullmatch(r"[a-z][\w.-]*", tok)):
                continue
            out.add(tok)
    return out


def imports(text: str, ext: str) -> set[str]:
    if ext.lower() != ".py":
        return set()
    return {(a or b).split(".")[0] for a, b in PY_IMPORT_RE.findall(text)}


def detect_os(brain: Brain, path: Path, text: str) -> str:
    """The operating system a script is written for, from its extension, then the commands it uses."""
    ext = path.suffix.lower()
    if ext in WINDOWS_EXT:
        return "windows"
    if ext in {".zsh", ".command"}:
        return "macos"
    cmds = {c.lower() for c in commands(text, ext)} | set(textnorm.words(text))
    hints = settings(brain)["detect"]
    for os_name in ("rhel", "macos", "linux"):
        if os_name in hints and cmds & {h.lower() for h in hints[os_name]}:
            return os_name
    return settings(brain)["any_os"] if ext == ".py" else "linux"


def purpose_from(text: str) -> str:
    """A script's purpose from its leading comment (after the shebang), or from a PowerShell .SYNOPSIS."""
    m = re.search(r"\.SYNOPSIS\s*\n\s*(.+)", text)
    if m:
        return m.group(1).strip()
    m = re.search(r'^\s*(?:"""|\'\'\')\s*(.+)', text, re.M)
    for line in text.splitlines()[:15]:
        s = line.strip()
        if s.startswith("#!") or not s:
            continue
        if s.startswith(("#", "::", "REM ")):
            s = re.sub(r"^(#+|::|REM)\s*", "", s).strip()
            if s and not re.match(r"^(-\*-|requires|shellcheck|set |vim:|encoding)", s, re.I):
                return s
            continue
        break
    return m.group(1).strip().strip("\"'") if m else ""


@dataclass
class Script:
    name: str
    topic: Topic
    folder: Path
    manifest: Path
    meta: dict
    variants: dict[str, Path]          # os -> file

    @property
    def key(self) -> str:
        return f"{self.topic.id}/{self.name}"

    def not_applicable(self) -> dict[str, str]:
        out = {}
        for part in (self.meta.get("not_applicable") or "").split(";"):
            k, _, why = part.partition(":")
            if k.strip():
                out[k.strip().lower()] = why.strip()
        return out


def scan(brain: Brain) -> tuple[list[Script], list[tuple[str, str, str]]]:
    """Every script in the library, and the problems found while reading it: (code, path, message)."""
    lib = library(brain)
    problems: list[tuple[str, str, str]] = []
    out: list[Script] = []
    if not lib.is_dir():
        return out, problems
    known = os_names(brain) + [settings(brain)["any_os"]]
    ts = topics(brain)
    for d in sorted(lib.iterdir()):
        if d.name.startswith(brain.cfg["files"]["template_prefix"]) or not d.is_dir():
            continue
        m = TOPIC_DIR_RE.match(d.name)
        if not m or f"{m.group('cat')}.{m.group('id')}" not in ts:
            problems.append(("SC-02", _rel(brain, d), "folder name is not '<AC.ID> <topic>', e.g. 52.02 network"))
            continue
        topic = ts[f"{m.group('cat')}.{m.group('id')}"]
        by_name: dict[str, dict[str, Path]] = {}
        manifests: dict[str, Path] = {}
        for f in sorted(d.iterdir()):
            if f.name.startswith(".") or f.name.startswith(brain.cfg["files"]["template_prefix"]):
                continue
            if f.is_dir():
                problems.append(("SC-02", _rel(brain, f), "no folders below the AC.ID; put the OS in the file name"))
                continue
            if f.suffix == ".md":
                manifests[f.stem] = f
                continue
            vm = VARIANT_RE.match(f.name)
            if not vm or vm.group("os") not in known:
                problems.append(("SC-02", _rel(brain, f), f"name is not <name>.<os>.<ext> with os one of {', '.join(known)}"))
                continue
            by_name.setdefault(vm.group("name"), {})[vm.group("os")] = f
        for name in sorted(set(by_name) | set(manifests)):
            man = manifests.get(name) or d / f"{name}.md"
            meta = notes.frontmatter(notes.read(man))[0] if man.is_file() else {}
            out.append(Script(name, topic, d, man, meta, by_name.get(name, {})))
    return out, problems


# ---------------------------------------------------------------- the log
def recorded(brain: Brain) -> dict[str, set[str]]:
    """sha256 values recorded per library path (relative to the library)."""
    p = brain.path("script_log")
    out: dict[str, set[str]] = {}
    if p.is_file():
        for line in notes.read(p).splitlines():
            m = re.search(r"· (\S.*?) · sha256:([0-9a-f]{64})", line)
            if m:
                out.setdefault(m.group(1), set()).add(m.group(2))
    return out


def _log(brain: Brain, action: str, f: Path, digest: str, by: str) -> None:
    rel = f.relative_to(library(brain)).as_posix()
    notes.append(brain.path("script_log"), f"- [{brain.stamp}] {action} · {rel} · sha256:{digest} · by {by}\n",
                 LOG_HEADER)


# ---------------------------------------------------------------- the manifest
def _set_fields(text: str, fields: dict[str, str]) -> str:
    parts = notes.split_frontmatter(text)
    head, body = (parts if parts else ([], text.splitlines()))
    keys = [l.split(":", 1)[0].strip() for l in head]
    for k, v in fields.items():
        line = f"{k}: {v}"
        if k in keys:
            head[keys.index(k)] = line
        else:
            head.append(line)
            keys.append(k)
    return "\n".join(["---", *head, "---", *body]).rstrip("\n") + "\n"


def _quote(v: str) -> str:
    v = " ".join(str(v or "").split())
    return '"' + v.replace('"', "'") + '"' if v else ""


def variants_table(brain: Brain, s: Script) -> str:
    labels = settings(brain)["os"]
    rows = ["| OS | File | Run |", "| --- | --- | --- |"]
    na = s.not_applicable()
    for os_name in [*os_names(brain), settings(brain)["any_os"]]:
        f = s.variants.get(os_name)
        label = labels.get(os_name, {}).get("label", "every OS") if os_name in labels else "every OS"
        if f:
            ext = f.suffix.lower()
            first = f.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0]
            if ext == ".sh" and "zsh" in first:
                ext = ".zsh"
            hint = RUN_HINT.get(ext, "{f}").format(f=f.name)
            rows.append(f"| {os_name} · {label} | `{f.name}` | `{hint}` |")
        elif os_name in na:
            rows.append(f"| {os_name} · {label} | not applicable | {na[os_name] or 'no reason given'} |")
    return "\n".join(rows)


def write_manifest(brain: Brain, s: Script, fields: dict[str, str]) -> None:
    """Create or refresh the manifest: the given fields, the list of variants, the Variants table. Text the owner
    wrote elsewhere in it is kept."""
    if s.manifest.is_file():
        text = notes.read(s.manifest)
    else:
        text = (f"---\ntype: script\nname: {s.name}\n---\n\n# {s.name}\n\n{fields.get('purpose', '').strip(chr(34))}\n\n"
                f"{VARIANTS_HEADING}\n\n## Notes\n\nWhat was tested, on which machine, and what to watch for.\n")
    present = [o for o in [*os_names(brain), settings(brain)["any_os"]] if o in s.variants]
    text = _set_fields(text, {**fields, "topic": s.topic.folder_name, "os": ", ".join(present)})
    lines = text.splitlines()
    if VARIANTS_HEADING not in lines:
        lines += ["", VARIANTS_HEADING, ""]
    i = lines.index(VARIANTS_HEADING) + 1
    j = i
    while j < len(lines) and not lines[j].startswith("## "):
        j += 1
    lines[i:j] = ["", variants_table(brain, s), ""]
    notes.write(s.manifest, "\n".join(lines).rstrip("\n") + "\n")
    s.meta = notes.frontmatter(notes.read(s.manifest))[0]


# ---------------------------------------------------------------- adding
def find(brain: Brain, name: str) -> Script | None:
    for s in scan(brain)[0]:
        if s.name == name:
            return s
    return None


def add(brain: Brain, data: bytes, source_name: str, name: str = "", os_name: str = "", topic: str = "",
        purpose: str = "", prompt: str = "", by: str = "", origin: str = "", replace: bool = False) -> dict:
    """File one script variant into the library and record it. Returns what was done."""
    cfg = settings(brain)
    text = data.decode("utf-8", errors="replace")
    src = Path(source_name)
    ext = src.suffix.lower() or ".sh"
    vm = VARIANT_RE.match(src.name)
    known = os_names(brain) + [cfg["any_os"]]
    if vm and vm.group("os") in known:
        name, os_name = name or vm.group("name"), os_name or vm.group("os")
    os_name = (os_name or detect_os(brain, src, text)).lower()
    if os_name not in known:
        raise BrainError(f"Unknown OS '{os_name}'. Use one of {', '.join(known)}.")
    allowed = cfg["os"].get(os_name, {}).get("extensions")
    if allowed and ext not in allowed:
        raise BrainError(f"A {os_name} variant has one of the extensions {', '.join(allowed)}, not {ext}.")
    name = notes.slug(name or (src.stem.split(".")[0] if src.stem else "script"))
    purpose = purpose or purpose_from(text)
    cmds = commands(text, ext)
    existing = find(brain, name)
    if existing:
        t = existing.topic
        if topic and resolve_topic(brain, topic).id != t.id:
            raise BrainError(f"{name} is already filed under {t.folder_name}; one script lives in one topic.")
        score = -1
    elif topic:
        t, score = resolve_topic(brain, topic), -1
    else:
        t, score = classify(brain, " ".join([name.replace("-", " "), purpose, prompt]), cmds)
    folder = ensure_topic(brain, t)
    target = folder / f"{name}.{os_name}{ext}"
    for other in existing.variants.values() if existing else []:
        if other.name.startswith(f"{name}.{os_name}.") and other != target:
            raise BrainError(f"{_rel(brain, other)} is already the {os_name} variant of {name}; "
                             "give a different --os or --name.")
    digest = sha256(data)
    action = "add"
    if target.is_file():
        if sha256(target.read_bytes()) == digest:
            action = "same"
        elif not replace:
            raise BrainError(f"{_rel(brain, target)} already exists with other content. Pass --replace to save the new "
                             "version (the old one stays in git history and its hash in the log), or give another --name.")
        else:
            action = "replace"
    if action != "same":
        target.write_bytes(data)
        if ext in {".sh", ".bash", ".zsh", ".command", ".py"}:
            try:
                target.chmod(target.stat().st_mode | 0o111)
            except OSError:
                pass
    s = find(brain, name) or Script(name, t, folder, folder / f"{name}.md", {}, {os_name: target})
    fields = {}
    if not s.meta.get("purpose") and purpose:
        fields["purpose"] = _quote(purpose)
    if not s.meta.get("generated_by"):
        fields["generated_by"] = by or cfg["default_by"]
        fields["generated_on"] = f"{brain.today:%Y-%m-%d}"
    if prompt and not s.meta.get("prompt"):
        fields["prompt"] = _quote(prompt)
    if origin:
        fields[f"origin_{os_name}"] = origin
    for key, default in (("not_applicable", ""), ("tested", ""), ("status", "in use")):
        if key not in s.meta:
            fields[key] = default
    write_manifest(brain, s, fields)
    if action != "same" or target.relative_to(library(brain)).as_posix() not in recorded(brain):
        _log(brain, action if action != "same" else "record", target, digest, by or cfg["default_by"])
    missing = [o for o in os_names(brain) if o not in s.variants and cfg["any_os"] not in s.variants
               and o not in s.not_applicable()]
    return {"name": name, "os": os_name, "topic": t.folder_name, "path": _rel(brain, target), "action": action,
            "classified": score, "missing": missing, "manifest": _rel(brain, s.manifest)}


def sync(brain: Brain, by: str = "") -> list[str]:
    """Record files changed by hand and refresh every manifest's variant list. Returns what changed."""
    done = []
    rec = recorded(brain)
    scripts, _ = scan(brain)
    for s in scripts:
        for os_name, f in s.variants.items():
            rel = f.relative_to(library(brain)).as_posix()
            digest = sha256(f.read_bytes())
            if digest not in rec.get(rel, set()):
                _log(brain, "record" if rel not in rec else "change", f, digest, by or "owner")
                done.append(f"recorded {rel}")
        before = notes.read(s.manifest) if s.manifest.is_file() else ""
        fields = {} if s.manifest.is_file() else {"generated_by": by or "owner", "generated_on": f"{brain.today:%Y-%m-%d}",
                                                  "not_applicable": "", "tested": "", "status": "in use"}
        if s.variants or s.manifest.is_file():
            write_manifest(brain, s, fields)
            if notes.read(s.manifest) != before:
                done.append(f"manifest {_rel(brain, s.manifest)}")
    return done


# ---------------------------------------------------------------- capture from an agent's file writes
def capture_reason(brain: Brain, path: Path) -> str | None:
    """Why a written file is not captured, or None when it is a script to file."""
    cfg = settings(brain)
    if not cfg["enabled"] or not cfg["capture_on_write"]:
        return "capture is off"
    if path.suffix.lower() not in set(cfg["capture_extensions"]):
        return "not a script"
    if any(part in set(cfg["capture_skip"]) for part in path.parts):
        return "skipped folder"
    if any(fnmatch.fnmatch(path.as_posix(), pat) for pat in cfg.get("capture_skip_globs", [])):
        return "skipped by glob"
    return None


def capture(brain: Brain, path: Path, by: str) -> str:
    """File a script an agent just wrote. Inside the library it is only recorded; elsewhere it is copied in."""
    path = path.resolve()
    lib = library(brain).resolve()
    if path.is_relative_to(lib):
        changed = sync(brain, by)
        return f"script library: recorded {', '.join(changed)}" if changed else ""
    if capture_reason(brain, path) or not path.is_file():
        return ""
    data = path.read_bytes()
    name = notes.slug(path.stem.split(".")[0])
    os_name = detect_os(brain, path, data.decode("utf-8", "replace"))
    vm = VARIANT_RE.match(path.name)
    if vm and vm.group("os") in os_names(brain) + [settings(brain)["any_os"]]:
        name, os_name = vm.group("name"), vm.group("os")

    def taken(n: str) -> bool:
        # A name is free for this file when no script has it, when its slot for this OS is empty (the file becomes
        # that script's variant), or when that slot was filled from this same file (an update).
        s = find(brain, n)
        return bool(s and os_name in s.variants and s.meta.get(f"origin_{os_name}") != path.as_posix())

    if taken(name):
        n = 2
        while taken(f"{name}-{n}"):
            n += 1
        name = f"{name}-{n}"
    r = add(brain, data, path.name, name=name, os_name=os_name, by=by, origin=path.as_posix(), replace=True)
    if r["action"] == "same":
        return ""
    gap = f" Still missing: {', '.join(r['missing'])} (write those variants, or set not_applicable in the manifest)." \
        if r["missing"] else ""
    return (f"script library: {path.name} filed as {r['path']} (topic {r['topic']}, {r['action']}).{gap} "
            f"Check the topic and purpose in {r['manifest']}.")


# ---------------------------------------------------------------- checks
def check(brain: Brain) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    cfg = settings(brain)
    if not cfg["enabled"]:
        return errors, warnings
    scripts, problems = scan(brain)
    for code, where, msg in problems:
        errors.append(f"{code} · {where}: {msg}")
    lib = library(brain)
    for t in topics(brain).values():
        if (lib / t.folder_name).is_dir() and not _jd_has(brain, t.id):
            errors.append(f"SC-04 · {_rel(brain, lib / t.folder_name)}: topic has no line in the JDex; write the line "
                          "first (brain script add does)")
    rec = recorded(brain)
    any_os = cfg["any_os"]
    fallback = resolve_topic(brain, str(cfg["fallback_topic"])).id
    for s in scripts:
        if not s.manifest.is_file():
            errors.append(f"SC-01 · {_rel(brain, s.folder)}/{s.name}.*: script has no manifest {s.name}.md: brain script sync")
            continue
        if not s.variants:
            warnings.append(f"SC-01 · {_rel(brain, s.manifest)}: manifest names no script file")
            continue
        na = s.not_applicable()
        if any_os not in s.variants:
            for o in cfg["required_os"]:
                if o not in s.variants and o not in na:
                    warnings.append(f"SC-03 · {_rel(brain, s.manifest)}: no {o} variant; write {s.name}.{o}.<ext> or "
                                    f"set not_applicable: {o}: <reason>")
        for o in na:
            if not na[o]:
                warnings.append(f"SC-03 · {_rel(brain, s.manifest)}: not_applicable {o} gives no reason")
        for o, f in s.variants.items():
            rel = f.relative_to(lib).as_posix()
            if sha256(f.read_bytes()) not in rec.get(rel, set()):
                warnings.append(f"SC-05 · {_rel(brain, f)}: not recorded in the script log (changed by hand?): "
                                "brain script sync")
            avoid = {a.lower() for a in cfg["os"].get(o, {}).get("avoid", [])}
            used = {c.lower() for c in commands(f.read_text(encoding="utf-8", errors="replace"), f.suffix)}
            if bad := sorted(used & avoid):
                warnings.append(f"SC-07 · {_rel(brain, f)}: uses {', '.join(bad)}, which {o} does not have by default")
            if o != "windows" and f.suffix.lower() in {".sh", ".bash", ".zsh"}:
                first = f.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0]
                if not first.startswith("#!"):
                    warnings.append(f"SC-06 · {_rel(brain, f)}: no shebang line (#!/usr/bin/env bash)")
        if not s.meta.get("purpose"):
            warnings.append(f"SC-06 · {_rel(brain, s.manifest)}: no purpose")
        if s.topic.id == fallback:
            warnings.append(f"SC-08 · {_rel(brain, s.manifest)}: in the unsorted topic; move it to a topic at the "
                            "Weekly Review (brain script move)")
    return errors, warnings


def move(brain: Brain, name: str, topic: str) -> str:
    s = find(brain, name)
    if s is None:
        raise BrainError(f"No script named {name}.")
    t = resolve_topic(brain, topic)
    if t.id == s.topic.id:
        return f"{name} is already in {t.folder_name}."
    folder = ensure_topic(brain, t)
    rec_moves = []
    for f in [*s.variants.values(), s.manifest]:
        if f.exists():
            dest = folder / f.name
            if dest.exists():
                raise BrainError(f"{_rel(brain, dest)} already exists.")
            shutil.move(str(f), str(dest))
            if f.suffix != ".md":
                rec_moves.append(dest)
    for dest in rec_moves:
        _log(brain, "move", dest, sha256(dest.read_bytes()), "owner")
    s2 = find(brain, name)
    if s2:
        write_manifest(brain, s2, {})
    return f"Moved {name} to {t.folder_name}."


# ---------------------------------------------------------------- the code knowledge graph
def documents(brain: Brain, max_calls: int = 40) -> list[dict]:
    """One knowledge-graph document per script: topic, operating systems, commands called, modules imported."""
    if not settings(brain)["enabled"]:
        return []
    labels = settings(brain)["os"]
    out = []
    for s in scan(brain)[0]:
        if not s.variants:
            continue
        purpose = s.meta.get("purpose", "")
        rel = [("in topic", s.topic.folder_name)] + ([("purpose", purpose[:160])] if purpose else [])
        mods: set[str] = set()
        for o, f in sorted(s.variants.items()):
            rel.append(("runs on", labels.get(o, {}).get("label", o) if o in labels else "every OS"))
            text = f.read_text(encoding="utf-8", errors="replace")
            # "calls on rhel → firewall-cmd": the same command node joins every script, on every OS, that calls it
            rel += [(f"calls on {o}", c) for c in sorted(commands(text, f.suffix))[:max_calls]]
            mods |= imports(text, f.suffix)
        for o in s.not_applicable():
            rel.append(("not for", labels.get(o, {}).get("label", o)))
        rel += [("imports", m) for m in sorted(mods)]
        # text stays empty: a purpose line is not a sentence of facts, and the code itself is never read as prose
        out.append({"id": f"script:{s.key}", "kind": "script", "title": f"script {s.name}", "text": "",
                    "links": [], "tags": [s.topic.name], "relations": rel, "trust": "system", "grade": "",
                    "path": s.manifest, "variants": sorted(s.variants)})
    return out


def listing(brain: Brain, topic: str = "", os_name: str = "", query: str = "") -> list[dict]:
    rows = []
    want_topic = resolve_topic(brain, topic).id if topic else ""
    q = textnorm.words(query)
    any_os = settings(brain)["any_os"]
    for s in scan(brain)[0]:
        if want_topic and s.topic.id != want_topic:
            continue
        if os_name and os_name not in s.variants and any_os not in s.variants:
            continue
        hay = " ".join(textnorm.words(" ".join([s.name.replace("-", " "), s.meta.get("purpose", ""),
                                                s.meta.get("prompt", ""), s.topic.name])))
        if q and not all(w in hay for w in q):
            continue
        rows.append({"name": s.name, "topic": s.topic.folder_name, "os": sorted(s.variants),
                     "not_applicable": sorted(s.not_applicable()), "purpose": s.meta.get("purpose", ""),
                     "manifest": _rel(brain, s.manifest),
                     "files": {o: _rel(brain, f) for o, f in sorted(s.variants.items())}})
    return rows
