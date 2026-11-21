# The script library

Every script an AI generates for you is kept on your own disk, filed by topic, and written once per operating system. The library lives in the files and code lane, as Johnny Decimal category **52 Scripts**; `brain check` enforces the rules below with the codes `SC-01` to `SC-08`, and every script enters the knowledge graph as a small **code graph**. The decision is [ADR-21](architecture.md#adr-21--the-script-library-every-ai-script-kept-by-topic-one-file-per-os); the research behind the code graph is in [research/code-knowledge-graphs.md](research/code-knowledge-graphs.md).

## The four rules

| # | Rule | How it is enforced |
| --- | --- | --- |
| S1 | **Every script an AI generates is saved and recorded on the local disk.** | Claude Code: the `PostToolUse` hook `brain hook script` files every `.sh`, `.ps1`, `.bat`… the agent writes, wherever it writes it. Other agents: the MCP tool `brain_script_save`, which `vault/AGENTS.md` and the MCP instructions require. Every file added or changed gets a line with its sha256 in `vault/_log/scripts.md`; a file changed without a line raises `SC-05`. |
| S2 | **Scripts are filed by topic.** | One topic = one Johnny Decimal ID (`52.01 system`, `52.02 network`…), with its JDex line written before its folder (`SC-04`). Without `--topic` the topic is chosen from keywords in the name, purpose, request and the commands the script calls; nothing matched → `52.99 unsorted` and `SC-08` until it is moved at the Weekly Review. |
| S3 | **Every script has one variant per operating system.** | Files are named `<name>.<os>.<ext>`, the OS in the name, never in a folder (lane rule 3, `SC-02`). The required systems are Linux, Red Hat, macOS and Windows; a missing one raises `SC-03` unless the manifest says why it does not apply. A variant using a command its OS lacks raises `SC-07`. |
| S4 | **Every script has a manifest.** | `<name>.md` beside the files: purpose, who generated it, when, from which request, and a table of variants with how to run each (`SC-01`, `SC-06`). The manifest is a note, so `brain search` finds it. |

## Layout

```text
vault/Code/52 Scripts/                 [paths] scripts (an absolute path puts the library on another disk)
  52.01 system/
  52.02 network/                       a topic: one AC.ID, its line in the JDex first
    check-port.md                      the manifest
    check-port.linux.sh                Linux: Debian, Ubuntu and generic
    check-port.rhel.sh                 Red Hat family: RHEL, Rocky, AlmaLinux, CentOS Stream, Fedora
    check-port.macos.sh                macOS: zsh, bash 3.2, BSD tools
    check-port.windows.ps1             Windows: PowerShell 5.1 and 7
  52.99 unsorted/                      the fallback topic, emptied at the Weekly Review
vault/_log/scripts.md                  every file added or changed, with its sha256 (brain commands only)
```

A variant named `<name>.any.<ext>` (Python, for example) covers every operating system.

### Why these four systems, and why Red Hat is separate from Linux

| OS key | Covers | What differs and breaks scripts |
| --- | --- | --- |
| `linux` | Debian, Ubuntu and generic Linux | `apt`/`dpkg`, `ufw`, AppArmor; GNU coreutils |
| `rhel` | RHEL, Rocky, AlmaLinux, CentOS Stream, Fedora | `dnf`/`yum`/`rpm`, `firewalld` (`firewall-cmd`), SELinux (`semanage`, `restorecon`), different package names (`httpd` not `apache2`) |
| `macos` | macOS | BSD tools (`sed -i ''`, `date -v`, no `readlink -f` before 12.3), bash 3.2 with zsh as default shell, `brew`, `launchctl` instead of `systemctl`, no `ip`, `ss`, `free` |
| `windows` | Windows 10/11, Server | PowerShell cmdlets (`Get-Service`, `Test-NetConnection`), `.ps1` execution policy, `\` paths, CRLF; no POSIX tools by default |

Add a system (Alpine, FreeBSD, SUSE…) with a table under `[scripts.os]` in `brain.toml`; list it in `required_os` if every script must have it.

## The manifest

```markdown
---
type: script
name: check-port
purpose: "Check whether a TCP port is open on a host"
generated_by: claude-code
generated_on: 2026-11-21
prompt: "viết script kiểm tra port"
origin_linux: /home/me/project/check-port.sh
not_applicable: macos: the owner has no Mac
tested: linux, windows
status: in use
topic: 52.02 network
os: linux, rhel, windows
---

# check-port

## Variants
| OS | File | Run |
...
```

`brain script add` and `brain script sync` rewrite only `topic`, `os` and the **Variants** table; everything else you write in the manifest is kept. `not_applicable` takes `os: reason` pairs separated by `;`. `tested` is yours to fill in after you have run a variant.

## Commands

| Command | What it does |
| --- | --- |
| `brain script add <file> [--name] [--os] [--topic] [--purpose] [--prompt] [--by] [--replace]` | Copy a script into the library as `<name>.<os>.<ext>`, write or refresh its manifest, record its hash. The OS comes from the extension and the commands used (`dnf` → rhel, `brew` → macos, `.ps1` → windows); the purpose from its leading comment or `.SYNOPSIS`. A variant with other content is replaced only with `--replace`; the old version stays in git and its hash in the log. |
| `brain script save --name … --os … --ext …` | The same with the script on stdin. |
| `brain script list [words] [--topic] [--os] [--json]` | Scripts with their OS coverage: `yes`, `n/a` or `—`. |
| `brain script topics` | Topics, their numbers and keywords. |
| `brain script sync` | Record files changed by hand, refresh every manifest. |
| `brain script move <name> <topic>` | Move a script and its manifest to another topic. |
| `brain script graph [--json]` | The code graph of the library. |
| `brain hook script` | Claude Code `PostToolUse` hook (below). |

MCP tools: `brain_script_save` (safe) and `brain_scripts` (readonly).

## Setting up the capture for Claude Code

Add to `.claude/settings.json` at the brain's root, next to the hooks in [integrations/claude-code](../integrations/claude-code/README.md):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [ { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR/bin/brain\" hook script" } ]
      }
    ]
  }
}
```

For the hook to see scripts Claude writes in *other* projects, put the same block in your user settings (`~/.claude/settings.json`) with the absolute path of your brain's `bin/brain` and `BRAIN_ROOT` set to your brain. The hook files the script, then tells Claude in its context which variants are still missing, so Claude writes them in the same turn. It never fails a turn.

Not captured: scripts that only exist inside a `Bash` command (`cat > x.sh <<EOF`), and files under `[scripts] capture_skip` (`.git`, `node_modules`, `.venv`…). Agents are told to save those with `brain_script_save`.

## Rule codes

| Code | Level | Meaning |
| --- | --- | --- |
| SC-01 | error | A script file has no manifest (`brain script sync` writes one); warning: a manifest with no file |
| SC-02 | error | A name is not `<name>.<os>.<ext>`, a folder is not `<AC.ID> <topic>`, or a folder is nested below a topic |
| SC-03 | warning | A required OS has no variant and `not_applicable` gives no reason for it |
| SC-04 | error | A topic folder has no line in the JDex |
| SC-05 | warning | A file's current content is not in the script log: it was changed by hand (`brain script sync`) |
| SC-06 | warning | No purpose in the manifest, or a shell variant has no shebang |
| SC-07 | warning | A variant calls a command its OS does not have by default (`[scripts.os.<os>] avoid`) |
| SC-08 | warning | A script is still in the unsorted topic |

## The code graph

`brain kg build` reads every script as a document of kind `script`, by rules only: it never runs a script and never sends code to an LLM.

```text
script check-port → in topic        → 52.02 network
script check-port → purpose         → check whether a tcp port is open on a host
script check-port → runs on         → windows (powershell 5.1 and 7)
script check-port → calls on linux  → nc
script check-port → calls on windows → test-netconnection
script open-port  → calls on rhel   → firewall-cmd
```

Commands are nodes shared by every script that calls them, so `brain kg ask "firewall-cmd"` answers "which of my scripts touch the firewall on Red Hat", and `brain kg ask "check port windows"` finds the Windows variant before an agent writes a new one. The facts carry trust `system`: they describe the files, they are not claims about the world.

## Measure every week

- Scripts in `52.99 unsorted` (`SC-08`).
- Scripts missing a variant (`SC-03`), and how many `not_applicable` reasons you still agree with.
- Variants never marked `tested`.
