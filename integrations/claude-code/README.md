# Claude Code integration

Claude Code is the one platform whose turns the brain can hook, so here "read the brain first" and "remember the turn" are enforced by hooks, not just asked for. Other platforms use the MCP server (`../mcp/`); the reasons are in [docs/integrations.md](../../docs/integrations.md).

| Hook | Runs | Does |
| --- | --- | --- |
| `UserPromptSubmit` | `bin/brain hook prompt` | puts what the knowledge graph holds about the prompt in Claude's context (`[Brain KG]` lines) |
| `Stop` | `bin/brain hook stop` | folds the finished turn into the graph: notes changed, what the chat was about |
| `PreToolUse` (`Write|Edit|MultiEdit|NotebookEdit`) | `write_guard.py` | the shared write guard: no permanent notes, agent items, templates, logs or graph files written by hand, no assignment labels added |

Add this to `.claude/settings.json` at the brain's root (on Windows use `bin\\brain.cmd` and `python`):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR/bin/brain\" hook prompt" } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR/bin/brain\" hook stop" } ] }
    ],
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|NotebookEdit",
        "hooks": [
          { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/integrations/claude-code/write_guard.py\"" }
        ]
      }
    ]
  }
}
```

The prompt hook prints nothing when the graph holds nothing about the prompt, and the hooks never fail a turn: an error goes to stderr and the conversation goes on. Build the graph once with `bin/brain kg build`; after that the Stop hook keeps it current.

Copy `vault/AGENTS.md` to `CLAUDE.md` at the root so Claude also gets the rules: G1 for facts it brings in, `brain turn` to close a turn, never `brain assign`.
