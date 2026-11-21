#!/usr/bin/env python3
"""Update a personal brain from the Brain_Standard repository, check it, and connect it to MCP clients, in one run.

    python bin/update_brain.py --brain D:/Brain_dave/Coding/second-brain [--commit] [--tests] [--mcp claude-desktop,claude-code]

What it does, in order, and what it never touches:

  1. Preflight: Python 3.11+, git, a brain (brain.toml) inside a git repository, and no uncommitted change in the
     paths it is about to replace, so nothing of yours is overwritten. --force skips the last check.
  2. Fetch the standard (remote "standard", added if missing) and compare versions. Already current: stop, unless
     --force.
  3. Replace only the standard's own paths: docs, tools, bin, tests, integrations, CHANGELOG.md. Never vault/ (your
     notes) and never brain.toml (your settings). Adds vault/_eval/questions.md if you have none yet, and .brain/ to
     .gitignore. vault/AGENTS.md is replaced only with --update-agents; otherwise it says whether it differs.
  4. Verify: the CLI prints the new version; with --tests the standard's tests run on this machine (in a
     temporary copy of the standard), and if they fail every replaced path is rolled back to what you had. Then brain check, brain index, and brain eval when you have questions.
  5. MCP (--mcp): register the brain's server with Claude Desktop (its config file, backed up first) and/or Claude
     Code (claude mcp add, user scope). Read-only unless --mcp-write (docs/mcp-security.md).
  6. --commit: one commit with the replaced paths. Without it the changes wait for you in git status.

--dry-run prints the plan and changes nothing. Exit codes: 0 done or already current, 1 a check failed (and was rolled
back where it could be), 2 wrong input or preflight failed. Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

STANDARD_URL = "https://github.com/DaveTran243/Brain_Standard.git"
REMOTE = "standard"
BRANCH = "main"
PATHS = ["docs", "tools", "bin", "tests", "integrations", "CHANGELOG.md"]
QUESTIONS = "vault/_eval/questions.md"
AGENTS = "vault/AGENTS.md"
SERVER = "brain"


class Stop(Exception):
    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.code = code


def say(msg: str = "") -> None:
    print(msg, flush=True)


def git(brain: Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-C", str(brain), *args], capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode:
        raise Stop(f"git {' '.join(args)} failed: {(r.stderr or r.stdout).strip()}")
    return r.stdout.strip()


def version_of(text: str) -> str:
    try:
        return tomllib.loads(text)["brain"]["version"]
    except (tomllib.TOMLDecodeError, KeyError):
        return "unknown"


def brain_cli(brain: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(brain / "tools"), "PYTHONUTF8": "1"}
    env.pop("BRAIN_ACTOR", None)
    return subprocess.run([sys.executable, "-m", "brain", "--root", str(brain), *args], cwd=str(brain), env=env,
                          capture_output=True, text=True, encoding="utf-8")


# ---------------------------------------------------------------- steps
def preflight(brain: Path, force: bool) -> None:
    if sys.version_info < (3, 11):
        raise Stop(f"Python 3.11 or later is needed; this is {sys.version.split()[0]}.")
    if shutil.which("git") is None:
        raise Stop("git is not on the PATH. Install Git for Windows, then run this again.")
    if not (brain / "brain.toml").is_file():
        raise Stop(f"No brain.toml in {brain}. Pass --brain with your brain's folder.")
    if git(brain, "rev-parse", "--is-inside-work-tree", check=False) != "true":
        raise Stop(f"{brain} is not a git repository; the update relies on git to undo itself.")
    dirty = git(brain, "status", "--porcelain", "--", *PATHS)
    if dirty and not force:
        raise Stop("You have uncommitted changes in paths the update replaces:\n" + dirty +
                   "\nCommit or stash them first, or pass --force to overwrite them.")


def fetch(brain: Path, url: str) -> None:
    remotes = git(brain, "remote").split()
    if REMOTE not in remotes:
        git(brain, "remote", "add", REMOTE, url)
        say(f"  added remote {REMOTE} → {url}")
    git(brain, "fetch", "--quiet", REMOTE, BRANCH)


def versions(brain: Path) -> tuple[str, str]:
    here = brain / "tools/brain/defaults.toml"
    old = version_of(here.read_text(encoding="utf-8")) if here.is_file() else "none"
    new = version_of(git(brain, "show", f"{REMOTE}/{BRANCH}:tools/brain/defaults.toml"))
    return old, new


def changelog_since(brain: Path, old: str) -> list[str]:
    text = git(brain, "show", f"{REMOTE}/{BRANCH}:CHANGELOG.md", check=False)
    heads = re.findall(r"^## (.+)$", text, flags=re.M)
    out = []
    for h in heads:
        if h.split(" ")[0] == old:
            break
        out.append(h)
    return out[:10]


def replace(brain: Path) -> list[str]:
    ref = f"{REMOTE}/{BRANCH}"
    present = [p for p in PATHS if exists_at(brain, ref, p)]
    git(brain, "checkout", ref, "--", *present)
    done = list(present)
    if not (brain / QUESTIONS).is_file():
        git(brain, "checkout", ref, "--", QUESTIONS)
        done.append(QUESTIONS)
    gi = brain / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines() if gi.is_file() else []
    if ".brain/" not in [l.strip() for l in lines]:
        with gi.open("a", encoding="utf-8", newline="\n") as f:
            f.write(("\n" if lines and lines[-1] else "") + "# derived search index (brain search)\n.brain/\n")
        done.append(".gitignore")
    return done


def agents(brain: Path, update: bool) -> str:
    theirs = git(brain, "show", f"{REMOTE}/{BRANCH}:{AGENTS}", check=False)
    mine = (brain / AGENTS).read_text(encoding="utf-8") if (brain / AGENTS).is_file() else ""
    if theirs.strip() == mine.strip():
        return "same"
    if update:
        git(brain, "checkout", f"{REMOTE}/{BRANCH}", "--", AGENTS)
        return "updated"
    return "differs"


def exists_at(brain: Path, ref: str, path: str) -> bool:
    return subprocess.run(["git", "-C", str(brain), "cat-file", "-e", f"{ref}:{path}"],
                          capture_output=True).returncode == 0


def rollback(brain: Path, head: str, paths: list[str]) -> None:
    """Put every replaced path back exactly as it was at head: files the update added are removed again. Safe because
    preflight refused to start while those paths held uncommitted or untracked work."""
    for p in paths:
        if p == ".gitignore":
            continue
        git(brain, "rm", "-r", "-q", "--cached", "--ignore-unmatch", "--", p, check=False)
        if exists_at(brain, head, p):
            git(brain, "checkout", head, "--", p)
            git(brain, "clean", "-f", "-d", "-q", "--", p, check=False)
        else:
            target = brain / p
            if target.is_dir():
                shutil.rmtree(target)
            elif target.is_file():
                target.unlink()
            parent = target.parent
            while parent != brain and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()                          # folders the update made only for this path
                parent = parent.parent


def verify(brain: Path, new: str, run_tests: bool) -> list[str]:
    """Problems found; empty when the update works."""
    problems = []
    r = brain_cli(brain, "--version")
    if r.stdout.strip() != f"brain {new}":
        problems.append(f"the CLI prints '{(r.stdout or r.stderr).strip()}', expected 'brain {new}'")
    if run_tests:
        problems += standard_tests(brain)
    return problems


def standard_tests(brain: Path) -> list[str]:
    """Run the standard's tests on this machine, in a temporary copy of the standard: they are written against its
    template vault, so running them inside a personal brain would fail for the wrong reason."""
    import tempfile
    import zipfile
    with tempfile.TemporaryDirectory(prefix="brain-update-") as tmp:
        archive = Path(tmp) / "standard.zip"
        git(brain, "archive", "--format=zip", "-o", str(archive), f"{REMOTE}/{BRANCH}")
        with zipfile.ZipFile(archive) as z:
            z.extractall(Path(tmp) / "standard")
        root = Path(tmp) / "standard"
        env = {**os.environ, "PYTHONPATH": str(root / "tools"), "PYTHONUTF8": "1"}
        env.pop("BRAIN_ACTOR", None)
        env.pop("BRAIN_ROOT", None)
        t = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"], cwd=str(root),
                           env=env, capture_output=True, text=True, encoding="utf-8")
    tail = (t.stderr or t.stdout).strip().splitlines()[-1:] or [""]
    if t.returncode:
        return [f"the standard's tests fail on this machine: {tail[0]}"]
    say(f"  tests of the standard on this machine: {tail[0]}")
    return []


def after(brain: Path) -> bool:
    """brain check, index and eval. Returns False when check found errors (your notes, not the update)."""
    c = brain_cli(brain, "check")
    last = (c.stdout or c.stderr).strip().splitlines()
    say(f"  brain check: {last[0] if last else ''}" + (f" (+{len(last) - 1} lines)" if len(last) > 1 else ""))
    i = brain_cli(brain, "index")
    say("  " + (i.stdout or i.stderr).strip())
    if (brain / QUESTIONS).is_file():
        e = brain_cli(brain, "eval")
        lines = [l for l in (e.stdout or e.stderr).strip().splitlines() if l.startswith(("recall", "Not in", "No q"))]
        say("  brain eval: " + (" · ".join(lines) or "no result"))
    return c.returncode == 0


# ---------------------------------------------------------------- MCP clients
def desktop_config() -> Path | None:
    if os.name == "nt" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    base = os.environ.get("XDG_CONFIG_HOME")
    return Path(base) / "Claude" / "claude_desktop_config.json" if base else Path.home() / ".config/Claude/claude_desktop_config.json"


def server_args(brain: Path, write: bool) -> list[str]:
    args = [str(brain / "integrations/mcp/brain_mcp.py"), "--root", str(brain)]
    return args if write else args + ["--read-only"]


def mcp_desktop(brain: Path, write: bool, dry: bool, path: Path | None = None) -> str:
    path = path or desktop_config()
    entry = {"command": sys.executable, "args": server_args(brain, write)}
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        except ValueError:
            return f"Claude Desktop: {path} is not valid JSON; left it alone. Fix it, then run with --mcp again."
    if data.get("mcpServers", {}).get(SERVER) == entry:
        return f"Claude Desktop: already set in {path}"
    if dry:
        return f"Claude Desktop: would set mcpServers.{SERVER} in {path}"
    if path.is_file():
        shutil.copy2(path, path.with_name(path.name + f".{dt.datetime.now():%Y%m%d-%H%M%S}.bak"))
    data.setdefault("mcpServers", {})[SERVER] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return f"Claude Desktop: set mcpServers.{SERVER} in {path} (old file kept as .bak). Restart Claude Desktop."


def mcp_code(brain: Path, write: bool, dry: bool) -> str:
    claude = shutil.which("claude")
    if claude is None:
        return "Claude Code: the claude command is not on the PATH; skipped."
    if subprocess.run([claude, "mcp", "get", SERVER], capture_output=True).returncode == 0:
        return f"Claude Code: a server named {SERVER} already exists; remove it with 'claude mcp remove {SERVER} -s user' to replace it."
    cmd = [claude, "mcp", "add", "-s", "user", SERVER, "--", sys.executable, *server_args(brain, write)]
    if dry:
        return "Claude Code: would run " + " ".join(cmd[1:])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return "Claude Code: added (user scope)." if r.returncode == 0 else f"Claude Code: failed: {(r.stderr or r.stdout).strip()}"


# ---------------------------------------------------------------- main
def run(a) -> int:
    brain = Path(a.brain).expanduser().resolve()
    say(f"Brain: {brain}")
    preflight(brain, a.force)
    head = git(brain, "rev-parse", "HEAD")
    fetch(brain, a.standard)
    old, new = versions(brain)
    say(f"Version: {old} → {new}")
    for h in changelog_since(brain, old):
        say(f"  · {h}")
    current = old == new and not a.force
    if current:
        say("Already up to date.")
    if a.dry_run:
        if not current:
            say("Dry run: would replace " + ", ".join(PATHS) + "; nothing changed.")
        for c in a.mcp:
            say("  " + (mcp_desktop(brain, a.mcp_write, True) if c == "claude-desktop" else mcp_code(brain, a.mcp_write, True)))
        return 0
    status = 0
    if not current:
        changed = replace(brain)
        say("Replaced: " + ", ".join(changed))
        problems = verify(brain, new, a.tests)
        if problems:
            rollback(brain, head, changed)
            for p in problems:
                say(f"  FAILED: {p}")
            say(f"Rolled back to {old}: nothing of the update is left. Report this and keep working on {old}.")
            return 1
        state = agents(brain, a.update_agents)
        if state == "differs":
            say(f"  {AGENTS} differs from the standard's; kept yours. See: git diff HEAD {REMOTE}/{BRANCH} -- {AGENTS}")
        elif state == "updated":
            say(f"  {AGENTS} updated from the standard.")
            changed.append(AGENTS)
        if a.commit:
            git(brain, "add", "--", *changed)
            git(brain, "commit", "-q", "-m", f"Update Brain_Standard {old} → {new}", "--", *changed)
            say(f"Committed: Update Brain_Standard {old} → {new}")
        else:
            say("Not committed: review with git status and git diff --stat, then commit.")
        say(f"Undo: git checkout {head[:12]} -- " + " ".join(changed))
    if not after(brain):
        say("  brain check found errors in the vault; the update itself is fine. Fix them as usual.")
        status = 0
    for c in a.mcp:
        say("  " + (mcp_desktop(brain, a.mcp_write, False) if c == "claude-desktop" else mcp_code(brain, a.mcp_write, False)))
    say("Done.")
    return status


def parse(argv=None):
    ap = argparse.ArgumentParser(prog="update_brain", description="Update a brain from Brain_Standard, check it, "
                                 "and connect MCP clients.")
    ap.add_argument("--brain", default=".", help="the brain's folder (holds brain.toml); default: here")
    ap.add_argument("--standard", default=STANDARD_URL, help="the standard's git URL or path")
    ap.add_argument("--commit", action="store_true", help="commit the update")
    ap.add_argument("--tests", action="store_true", help="run the standard's tests; roll back if they fail")
    ap.add_argument("--update-agents", action="store_true", help=f"also replace {AGENTS}")
    ap.add_argument("--mcp", default="", help="claude-desktop, claude-code or both, comma-separated")
    ap.add_argument("--mcp-write", action="store_true", help="register the full server, not --read-only")
    ap.add_argument("--force", action="store_true", help="update even when current or when those paths have changes")
    ap.add_argument("--dry-run", action="store_true", help="show the plan, change nothing")
    a = ap.parse_args(argv)
    a.mcp = [m.strip() for m in a.mcp.split(",") if m.strip()]
    bad = [m for m in a.mcp if m not in ("claude-desktop", "claude-code")]
    if bad:
        ap.error(f"unknown --mcp client: {', '.join(bad)} (use claude-desktop, claude-code)")
    return a


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    try:
        return run(parse(argv))
    except Stop as e:
        print(str(e), file=sys.stderr)
        return e.code


if __name__ == "__main__":
    sys.exit(main())
