# The brain as an MCP server

`brain_mcp.py` gives any platform that speaks the Model Context Protocol the brain's shared agent tools, over stdio, with nothing to install but Python 3.10 or newer. Design and the full platform list: [docs/integrations.md](../../docs/integrations.md).

```bash
python integrations/mcp/brain_mcp.py                          # the brain at the repository root
python integrations/mcp/brain_mcp.py --root path/to/brain      # a brain elsewhere (its own brain.toml)
python integrations/mcp/brain_mcp.py --read-only              # only the tools a level-suggest run may use
```

| Tool | Mode | What it does |
| --- | --- | --- |
| `brain_recall` | readonly | what the knowledge graph holds about a question, with source and trust per fact |
| `brain_remember` | safe | fold a turn into the graph: the owner's message verbatim + a one-line summary |
| `brain_capture` | safe | the owner's words, verbatim, to the Inbox |
| `brain_submit` | readonly | facts the agent looked up, through gate G1 with a source record |
| `brain_check` | readonly | `brain check` |
| `brain_suggest` | readonly | gaps the graph sees (suggestions only) |
| `brain_turn` | safe | close a turn |
| `brain_weekly` | readonly | Weekly Review metrics, not saved |
| `brain_assigned` | readonly | tasks the owner assigned to the assistant, by level |
| `brain_report` | readonly | report an assigned task done; the result goes to the Inbox |

There is no tool to assign work, add a label or edit a list file. Every call runs the CLI with `BRAIN_ACTOR=agent`.

The server sends `instructions` at `initialize` (recall first, capture the owner's words verbatim, submit facts through G1, remember and close the turn), so clients that pass server instructions to the model get the protocol without any other setup.

## Client configuration

Replace `/path/to/brain` with the repository path, and `python` with `python3` on macOS and Linux. Most clients use the same `mcpServers` JSON block:

```json
{
  "mcpServers": {
    "brain": {
      "command": "python",
      "args": ["/path/to/brain/integrations/mcp/brain_mcp.py"]
    }
  }
}
```

| Client | Where the block goes | Notes |
| --- | --- | --- |
| Claude Code | `claude mcp add brain -- python /path/to/brain/integrations/mcp/brain_mcp.py` (user scope with `-s user`), or `.mcp.json` in a project | inside the brain repository the hooks in `integrations/claude-code/` do recall and remember; the server is for Claude Code sessions in other folders |
| Claude Desktop (and Cowork) | `claude_desktop_config.json` (Settings → Developer → Edit Config) | restart the app after editing |
| Cursor | `.cursor/mcp.json` in a project, or `~/.cursor/mcp.json` | |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | |
| Gemini CLI | `~/.gemini/settings.json` (`mcpServers`) | |
| Kiro | `.kiro/settings/mcp.json` in a workspace, or `~/.kiro/settings/mcp.json` | |
| Cline, Roo Code | the extension's MCP settings file (MCP Servers → Configure) | |
| Codex CLI | `~/.codex/config.toml`, see below | TOML, not JSON |
| Hermes Agent | `~/.hermes/config.yaml`, see below | then `/reload-mcp` |
| Goose | `goose configure` → Add Extension → Command-line Extension, command `python …/brain_mcp.py` | |
| OpenClaw | `openclaw mcp add`, or the MCP section of `openclaw.json` | |
| Javis OS | prefer the plugin in `integrations/javis/`: its hook also guards Javis's own file tools | the MCP hub works too |

Codex CLI:

```toml
[mcp_servers.brain]
command = "python"
args = ["/path/to/brain/integrations/mcp/brain_mcp.py"]
```

Hermes Agent:

```yaml
mcp_servers:
  brain:
    command: python
    args: ["/path/to/brain/integrations/mcp/brain_mcp.py"]
```

The paths and menu names above are where each client kept its MCP settings when this page was written (2026-11). Clients move them between versions; if a path does not exist, look up "MCP" in that client's settings or documentation. The JSON block itself is the same everywhere.

## Clients that need HTTP instead of stdio

n8n's MCP Client Tool node, Zapier, Make, Dify and remote connectors (claude.ai, ChatGPT) reach MCP servers over HTTP, not by starting a process. Two ways, in order of preference:

1. **A stdio-to-HTTP bridge** such as `mcp-proxy` or `supergateway`, run on the owner's machine next to the brain, with a token. Only expose it on a private network: the tools write to the brain.
2. **An HTTP API** in front of the `brain` package (for example a small FastAPI server). Brain_Standard does not ship one; [docs/knowledge-graph.md](../../docs/knowledge-graph.md) describes the `recall` endpoint it would need.

## Test it

```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | python integrations/mcp/brain_mcp.py --read-only
```

The tests in `tests/test_kg.py` (`TestMCP`) drive the protocol end to end.
