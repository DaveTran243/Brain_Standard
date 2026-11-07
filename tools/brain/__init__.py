"""Brain_Standard: the brain CLI as a package of reusable modules.

config     defaults.toml merged with brain.toml, and the Brain context
notes      files, frontmatter, titles, slugs, dates
gates      Admiralty grades and the reach of a fact (G1–G4)
intake     capture (your words) and submit (facts through G1)
checks     every rule of brain check
metrics    Weekly Review metrics
assistant  assign, list and report tasks for the assistant
guard      write guard shared by the Claude Code hook and every integration
kgcore     the knowledge graph, portable (no vault)
kg         the knowledge graph of this vault: build, ask, remember
agent_tools  the tools every agent platform gets
migrate    convert a 3.0 brain to 4.0 names
cli        the command line
"""
from .config import Brain, BrainError, open_brain

__all__ = ["Brain", "BrainError", "open_brain"]
