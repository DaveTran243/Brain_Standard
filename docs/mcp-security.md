# MCP security checklist · before the brain is opened to an agent

2026-11-21 · what to check before any agent or MCP client is connected to a brain, and what the code already enforces. Requirement BR-05 of the search round; metric M5 (cases where a tool reads outside the vault or writes a permanent note) must stay at 0.

The brain's MCP server (`integrations/mcp/brain_mcp.py`) runs over stdio on your own machine. It has no network port. Every tool runs one `brain` command with `BRAIN_ACTOR=agent`, so the CLI applies the same rules to every platform. The checklist follows the threat areas surveyed in Hou et al., *Model Context Protocol (MCP): Landscape, Security Threats, and Future Research Directions* (arXiv 2503.23278, preprint, grade B2 in the evidence notebook). The mapping of their categories to the controls below is ours, not the paper's.

## 1 · What the code decides (no agent can talk its way past these)

| Threat | Control | Where | Test |
| --- | --- | --- | --- |
| Reading outside the vault (`../brain.toml`, `/etc/passwd`, `C:\…`, `~`) | `brain read` takes only `.md` paths relative to the vault; absolute paths, drive letters, `..` and links that lead out are refused with exit code 4 | `tools/brain/reading.py` `safe_path` | `tests/test_reading.py` `test_m5_no_escape_succeeds`, `test_link_leading_out_is_refused`, `test_escape_through_mcp_is_an_error` |
| An agent writing permanent notes | No tool writes `30-Knowledge/permanent`; the write guard blocks it for Claude Code and Javis | `tools/brain/agent_tools.py`, `tools/brain/guard.py` | `test_no_tool_writes_a_permanent_note` |
| An agent's claim becoming a fact | Facts enter only through `brain_submit` and gate G1, with a source record and a grade | `tools/brain/intake.py`, `tools/brain/gates.py` | `tests/test_brain.py` |
| An agent assigning itself work | `brain assign` is refused when `BRAIN_ACTOR=agent`; MCP does not offer it | `tools/brain/cli.py` | `tests/test_kg.py` `test_protocol` |
| Instructions hidden in a note (indirect prompt injection) | What `brain_recall`, `brain_search`, `brain_read` and `brain_where` return is wrapped in `<brain-data>`, marked as data; a closing tag inside a note cannot end the frame | `tools/brain/agent_tools.py` `frame` | `tests/test_search.py` `test_note_text_is_framed_as_data` |
| Too much context handed over | `brain_search` returns at most `k` = 8 sections within `max_chars`; `brain_read` at most `max_lines` = 200 lines | `[search]`, `[read]` in `defaults.toml` | `test_agent_form_is_capped_and_says_not_found`, `test_read_numbers_lines_and_caps` |
| Broken or invented citations | `brain_cite_check` checks every `path:line` and its quote | `tools/brain/reading.py` | `CiteCheckTest` |
| A read-only run that can still write | `--read-only` lists only tools whose `min_mode` is `readonly` | `integrations/mcp/brain_mcp.py` | `test_read_only_server_reads_and_cannot_write` |

## 2 · What you check when you connect a client

1. **Read-only first.** Start a new client with `brain_mcp.py --read-only`. Give it the write tools only once it behaves.
2. **One brain per server.** Pass `--root` to the brain you mean. Never point a server at a folder above several brains.
3. **The server's own code.** Use `brain_mcp.py` from this repository. Never use a copy another tool installed or rewrote. Its tool descriptions are part of what the model reads.
4. **No secrets in the vault.** Search and read return note text to the model. Keys, passwords and tokens never go in a note. Leave them out entirely, or list their folder in `[search] exclude`.
5. **Other servers in the same client.** A client that also runs a shell, file or browser server can do what those allow. The brain's rules protect only the brain's tools. The write guard in `integrations/claude-code/` covers Claude Code's own file tools.
6. **Watch the turn log.** Each agent turn is logged with `BRAIN_ACTOR=agent`. Read `vault/_log/turns.md` in the Weekly Review.
7. **Updates.** Pull `tools/` and `integrations/` from the standard and read the CHANGELOG first. A changed tool description is a changed instruction to every model that uses it.

## 3 · Not done yet

- **A remote endpoint over HTTP.** Kept out of scope (BRD section 5). It opens only after this list passes, and it needs authentication of its own.
- **A per-client allow-list of tools.** `--read-only` is the only switch today.
- **Signed tool definitions.** No signature yet proves that `agent_tools.py` was not changed.
