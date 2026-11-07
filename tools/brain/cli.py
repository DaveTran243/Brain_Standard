"""The brain command line. Each command is a thin wrapper around a module; parameters come from configuration."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import assistant, checks, gates, intake, kg, kgcore, metrics, migrate, notes
from .config import Brain, BrainError, defaults, find_root, open_brain


def print_findings(errors: list[str], warnings: list[str]) -> None:
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print(f"Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")
    if not errors and not warnings:
        print("Vault is clean.")


# ---------------------------------------------------------------- commands

def cmd_capture(brain: Brain, a) -> int:
    print(f"Captured to Inbox: {intake.capture(brain, ' '.join(a.text), a.channel)}")
    return 0


def cmd_submit(brain: Brain, a) -> int:
    s = intake.submit(brain, Path(a.file))
    if s.warning:
        print("Warning: " + s.warning)
    if s.outcome == gates.REJECT:
        print(f"G1 rejected {Path(a.file).name} (grade {s.grade}). Logged to {brain.cfg['paths']['rejected_log']}; "
              "not added to the Inbox.")
        return 3
    print(f"G1 passed: {s.title} · grade {s.grade} · may go up to {brain.gates['reach_names'][s.outcome]}.")
    return 0


def cmd_check(brain: Brain, a) -> int:
    errors, warnings = checks.check(brain)
    print_findings(errors, warnings)
    return 1 if errors else 0


def cmd_turn(brain: Brain, a) -> int:
    types = brain.cfg["turn"]["types"]
    if a.type not in types:
        raise BrainError(f"Turn type must be one of: {', '.join(types)}.")
    summary = " ".join(" ".join(a.summary).split())
    if not summary:
        raise BrainError("A one-line summary of the turn is required.")
    errors, warnings = checks.check(brain)
    if errors and brain.gates["strict"]:
        print_findings(errors, [])
        raise BrainError(f"Turn not closed: fix {len(errors)} error(s), then run brain turn again.", code=1)
    notes.append(brain.path("turn_log"), f"- [{brain.stamp}] {a.type} · {summary}\n",
                 brain.cfg["files"]["turn_log_header"])
    print(f"Brain: {a.type} · {summary}")
    if warnings:
        print(f"({len(warnings)} warning(s), see brain check)")
    return 0


def cmd_weekly(brain: Brain, a) -> int:
    m = metrics.measure(brain)
    text = metrics.render(brain, m)
    print(text)
    if a.save:
        target = brain.path("weekly") / f"{m['week']}.md"
        notes.write(target, brain.cfg["files"]["weekly_title"].format(week=m["week"]) + text)
        print(f"Saved {brain.rel(target)}")
    return 0


def cmd_assign(brain: Brain, a) -> int:
    if os.environ.get("BRAIN_ACTOR", "").lower() == "agent":
        raise BrainError(f"Only the brain's owner assigns tasks to {brain.assistant['name']}. Suggest the task worth "
                         "assigning; the owner runs brain assign.", code=1)
    text = assistant.assign(brain, a.match, a.level)
    print(f"Assigned to {brain.assistant['name']} ({a.level}): {text}")
    return 0


def check_level(brain: Brain, level: str | None) -> None:
    levels = brain.assistant["levels"]
    if level is not None and level not in levels:
        raise BrainError(f"Level must be one of: {', '.join(levels)}.")


def cmd_assigned(brain: Brain, a) -> int:
    check_level(brain, a.level)
    open_ = assistant.open_up_to(brain, a.level)
    if not open_:
        suffix = f" at level {a.level} or below." if a.level else "."
        print(f"Nothing is assigned to {brain.assistant['name']}{suffix}")
    for n, task in enumerate(open_, 1):
        print(f"{n} · {task.level} · {task.text}")
    return 0


def cmd_report(brain: Brain, a) -> int:
    check_level(brain, a.level)
    task = assistant.report(brain, a.number, " ".join(a.result), a.level)
    print(f"Done: {task}. The result is in the Inbox for clarifying.")
    return 0


def cmd_kg(brain: Brain, a) -> int:
    if a.sub == "build":
        r = kg.build(brain, full=a.full, use_llm=True if a.llm else (False if a.no_llm else None))
        print(f"Knowledge graph: {r['triples']} triples (+{r['inferred']} inferred) from {r['documents']} documents; "
              f"{r['changed']} read again, {r['removed']} removed" + (" · with the LLM" if r["llm"] else " · rules only"))
        if r["llm_errors"]:
            print(f"  {r['llm_errors']} documents failed at the LLM and kept their rule triples; run again later.")
    elif a.sub == "ask":
        seeds, facts = kg.ask(brain, " ".join(a.question), a.max, a.hops)
        if not facts:
            print("The graph holds nothing about that yet." + ("" if kg.load(brain) else " Build it first: brain kg build"))
            return 0
        print(f"About: {', '.join(seeds)}")
        for t in facts:
            print(f"  {kgcore.fact_line(t)}")
    elif a.sub == "stats":
        st = kg.stats(brain)
        print(f"{st['triples']} triples · {st['entities']} entities · {st['components']} islands · built {st['built'] or 'never'}")
        print("  by kind:  " + ", ".join(f"{k} {n}" for k, n in st["by_kind"].items()))
        print("  by trust: " + ", ".join(f"{k} {n}" for k, n in st["by_trust"].items()))
        print("  hubs:     " + ", ".join(st["top"]))
    elif a.sub == "suggest":
        found = kg.suggest(brain, a.max)
        if not found:
            print("No suggestions: the graph has no gaps it can see." + ("" if kg.load(brain) else " Build it first: brain kg build"))
            return 0
        print("Suggestions from the graph. None is written anywhere; vet them first (docs/design-suggestions.md).")
        for i, sg in enumerate(found, 1):
            print(f"  {i:>2}. [{sg['kind']}] {sg['text']}\n      why: {sg['evidence']}")
    elif a.sub == "remember":
        n = kg.remember(brain, a.prompt or "", a.session or "", [a.summary] if a.summary else [])
        print(f"Remembered: {n} memory triples added to the knowledge graph.")
    elif a.sub == "export":
        print(f"Wrote {kg.export(brain, Path(a.path))} triples to {a.path} (ai-knowledge-graph's JSON shape).")
    return 0


def _hook_state(brain: Brain, session: str) -> Path:
    safe = "".join(c for c in (session or "default") if c.isalnum() or c in "-_")[:80] or "default"
    return brain.path("hook_state") / f"{safe}.json"


def cmd_hook(brain: Brain, a) -> int:
    """For agent platforms with turn hooks (Claude Code): read the graph before, remember the turn after.
    Reads the hook event as JSON on stdin; never fails the agent's turn."""
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        event = {}
    cfg, session = brain.cfg["kg"], str(event.get("session_id") or "")
    try:
        if a.event == "prompt":
            text = str(event.get("prompt") or "").strip()
            notes.write(_hook_state(brain, session), json.dumps({"stamp": brain.stamp, "prompt": text},
                                                                ensure_ascii=False) + "\n")
            if cfg["enabled"] and cfg["read_on_prompt"] and text:
                ctx = kg.context(brain, text)
                if ctx:
                    print(ctx)
        elif a.event == "stop":
            f = _hook_state(brain, session)
            if cfg["enabled"] and cfg["update_on_stop"] and f.is_file():
                st = json.loads(notes.read(f))
                if not st.get("remembered"):
                    kg.remember(brain, st.get("prompt", ""), session, kg.summaries_since(brain, st["stamp"]))
                    notes.write(f, json.dumps({**st, "remembered": True}, ensure_ascii=False) + "\n")
    except Exception as e:  # noqa: BLE001 - a broken graph must not stop the conversation
        print(f"brain hook {a.event}: {type(e).__name__}: {e}", file=sys.stderr)
    return 0


def cmd_migrate(root: Path, a) -> int:
    plan = migrate.run(root, dry_run=a.dry_run)
    if not plan.changes:
        print("Nothing to migrate: this brain already uses the current names.")
        return 0
    print(("Would change" if a.dry_run else "Changed") + f" ({len(plan.changes)}):")
    for c in plan.changes:
        print(f"  - {c}")
    if not a.dry_run:
        print("Run brain check, review the diff, then commit.")
    return 0


# ---------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    d = defaults()
    levels = "/".join(d["assistant"]["levels"])
    ap = argparse.ArgumentParser(prog="brain", description=f"Brain_Standard {d['brain']['version']}")
    ap.add_argument("--root", help="folder that holds brain.toml (default: search upwards from here)")
    ap.add_argument("--version", action="version", version=f"brain {d['brain']['version']}")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("capture", help="write your words to the Inbox")
    p.add_argument("text", nargs="+")
    p.add_argument("--channel", help=f"where it came from: hand, voice, telegram… (default: {d['capture']['default_channel']})")
    p.set_defaults(fn=cmd_capture)

    p = sub.add_parser("submit", help="submit a fact with its source record through G1")
    p.add_argument("file")
    p.set_defaults(fn=cmd_submit)

    p = sub.add_parser("check", help="check the vault against the rules and trust gates")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("turn", help="close a turn")
    p.add_argument("type", help="/".join(d["turn"]["types"]))
    p.add_argument("summary", nargs="+")
    p.set_defaults(fn=cmd_turn)

    p = sub.add_parser("weekly", help="Weekly Review metrics")
    p.add_argument("--save", action="store_true", help="save to the weekly folder")
    p.set_defaults(fn=cmd_weekly)

    name = d["assistant"]["name"]
    p = sub.add_parser("assign", help=f"assign a next action to {name} (owner only)")
    p.add_argument("match", help="text found in exactly one open next action")
    p.add_argument("level", help=levels)
    p.set_defaults(fn=cmd_assign)

    p = sub.add_parser("assigned", help=f"list open tasks assigned to {name}")
    p.add_argument("--level", help=f"{levels}: only tasks at this level or below")
    p.set_defaults(fn=cmd_assigned)

    p = sub.add_parser("report", help=f"{name} reports an assigned task done; the result goes to the Inbox")
    p.add_argument("number", type=int, help="position in brain assigned")
    p.add_argument("result", nargs="+")
    p.add_argument("--level", help=f"{levels}: the same --level used with brain assigned")
    p.set_defaults(fn=cmd_report)

    p = sub.add_parser("kg", help="the knowledge graph: read before a conversation, updated after it")
    kgs = p.add_subparsers(dest="sub", required=True)
    p.set_defaults(fn=cmd_kg)
    q = kgs.add_parser("build", help="bring the graph up to date (only changed notes are read again)")
    q.add_argument("--full", action="store_true"); q.add_argument("--llm", action="store_true"); q.add_argument("--no-llm", action="store_true")
    q = kgs.add_parser("ask", help="what the graph holds about a question"); q.add_argument("question", nargs="+")
    q.add_argument("--max", type=int); q.add_argument("--hops", type=int)
    kgs.add_parser("stats", help="size, trust and hubs of the graph")
    q = kgs.add_parser("suggest", help="gaps the graph sees"); q.add_argument("--max", type=int, default=15)
    q = kgs.add_parser("remember", help="fold a conversation turn into the graph (for agents without hooks)")
    q.add_argument("--prompt", help="the owner's message, verbatim"); q.add_argument("--summary"); q.add_argument("--session")
    q = kgs.add_parser("export", help="write the graph as JSON for ai-knowledge-graph's tools"); q.add_argument("path")

    p = sub.add_parser("hook", help="turn hooks for agent platforms (Claude Code): read the graph, remember the turn")
    p.add_argument("event", choices=["prompt", "stop"])
    p.set_defaults(fn=cmd_hook)

    p = sub.add_parser("migrate", help="convert a 3.0 or 4.0 brain to the current names")
    p.add_argument("--dry-run", action="store_true", help="show what would change, change nothing")
    p.set_defaults(fn=cmd_migrate)
    return ap


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    a = build_parser().parse_args(argv)
    try:
        if a.fn is cmd_migrate:
            root = Path(a.root).resolve() if a.root else find_root()
            if root is None:
                raise BrainError("No brain.toml found. Run inside a brain folder or pass --root.", code=1)
            return cmd_migrate(root, a)
        return a.fn(open_brain(a.root), a)
    except BrainError as e:
        print(str(e), file=sys.stderr)
        return e.code
