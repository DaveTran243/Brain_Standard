"""Javis OS plugin for a Brain_Standard brain.

A thin adapter: the tools and the rules live in the brain package (tools/brain/agent_tools.py and tools/brain/guard.py),
shared with every other platform. This file only translates them into Javis OS's plugin API:

1. Registers every tool in agent_tools.TOOLS with Javis, for every engine, including API engines without a shell.
   Each tool runs the brain CLI with BRAIN_ACTOR=agent, so `brain assign` is refused and a fact must pass G1.
2. A pre_tool_call hook: the shared write guard (guard.block_reason) with Javis's own file-writing tool names.

Point the brain in Javis at the repository root (the folder that holds brain.toml), or set BRAIN_ROOT.
Standard library only.
"""
from __future__ import annotations

import sys
from pathlib import Path

WRITE_TOOLS = ("javis_write_file", "javis_edit_file")
CHANNEL = "javis"   # recorded on the owner's words captured through Javis
PACKAGE_DIR = "tools"


def brain_package(root: Path):
    """Import the brain package of this repository.

    Javis is one long-running process that may serve several brains. When the package already imported comes from
    another repository, drop it and import this one, so each brain runs its own rules.
    """
    package = (Path(root) / PACKAGE_DIR).resolve()
    loaded = sys.modules.get("brain")
    if loaded is not None and Path(loaded.__file__).resolve().parent.parent != package:
        for name in [n for n in sys.modules if n == "brain" or n.startswith("brain.")]:
            del sys.modules[name]
    if str(package) not in sys.path:
        sys.path.insert(0, str(package))
    import brain
    import brain.agent_tools
    import brain.config
    import brain.guard
    return brain


def _locate(vault_root):
    """(repository, brain) for the brain selected in Javis, or None."""
    here = Path(vault_root or ".").resolve()
    repo = next((p for p in [here, *here.parents] if (p / PACKAGE_DIR / "brain" / "agent_tools.py").is_file()), None)
    if repo is None:
        return None
    return brain_package(repo).agent_tools.locate(here)


NOT_A_BRAIN = ("ERROR: the brain selected in Javis is not a Brain_Standard repository (no brain.toml). "
               "Point the brain at the repository root, or set BRAIN_ROOT.")


def _handler(name: str):
    def handle(args, ctx):
        found = _locate(getattr(ctx, "vault_root", None))
        if found is None:
            return NOT_A_BRAIN
        root, home = found
        args = dict(args or {})
        if name == "brain_capture":
            args.setdefault("channel", CHANNEL)
        return brain_package(root).agent_tools.call(root, name, args, home)
    return handle


def block_reason(tool_name: str, args: dict, vault_root) -> str | None:
    found = _locate(vault_root)
    if found is None:
        return None
    root, home = found
    package = brain_package(root)
    return package.guard.block_reason(package.config.open_brain(home), tool_name, args or {}, vault_root,
                                      write_tools=WRITE_TOOLS)


def pre_tool_call(tool_name=None, args=None, vault_root=None, **kwargs):
    reason = block_reason(tool_name, args or {}, vault_root)
    return {"deny": f"Brain: {reason}"} if reason else None


def register(ctx):
    found = _locate(getattr(ctx, "vault_root", None)) or _locate(Path(__file__).parent)
    tools = brain_package(found[0]).agent_tools.TOOLS if found else []
    for tool in tools:
        ctx.register_tool(name=tool["name"], description=tool["description"], handler=_handler(tool["name"]),
                          min_mode=tool["min_mode"], schema=tool["schema"])
    ctx.register_hook("pre_tool_call", pre_tool_call)
