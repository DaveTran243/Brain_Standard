# Using the brain with Javis OS

[Javis OS](https://github.com/blogminhquy/javis-os) is a self-hosted AI agent. It runs on a laptop or a VPS, lets you switch models (Claude Code, Codex, Grok, Antigravity, OpenRouter, Gemini, Ollama…), talks to you through a dashboard, voice, Telegram, Zalo and Slack, and works in the background with loops, reminders and a Kanban queue. It has its own "Second Brain": a folder of Markdown.

This page shows how to let Javis work on a Brain 4.0 without breaking the brain's rules. Since 3.0, Javis holds both ends of the [flow](flow.md#the-assistant-loop): it captures into the Inbox, and it follows up on tasks you have clarified and assigned to it. Read [using-with-ai.md](using-with-ai.md) first if the three connection levels and the shared rule block are new to you.

Surveyed on Javis OS 0.270.0, 21/10/2026. Javis ships new versions very quickly, so recheck the items marked "recheck after upgrading".

## Why they fit

Both share one idea: **rent the model, own the brain**. The brain is your Markdown and git; Javis is the layer that runs the AI, and switching models loses nothing. Javis fills exactly the gaps that Brain 2.2 left open on purpose, and 3.0 built the assistant loop around it:

| What Brain 2.2 lacked | What Javis provides |
| --- | --- |
| Quick capture away from the computer | Telegram, Zalo, Slack and voice, all landing in one place |
| Remembering to run the daily loop and the Weekly Review | Reminders on a clock or cron, with results sent to Telegram |
| Level 3 only for agents with a shell | Every engine, including API engines, can call `brain` commands through the plugin |
| Seeing the network of notes | A knowledge graph drawn from `[[...]]` links, offline |

In exchange, Javis has habits that run against the brain's rules. The sections below name each one and how to switch it off.

## Concept map

| Javis | Brain 4.0 | Note |
| --- | --- | --- |
| `sources/` | `30-Knowledge/literature/` | Javis stores raw sources without a source record |
| `wiki/` | `30-Knowledge/permanent/`, `40-Maps/` | Javis writes the wiki itself. The brain forbids AI from writing permanent notes |
| `memory/MEMORY.md`, `memory/facts/` | None | Javis's working memory about you. Keep it outside `vault/` |
| INGEST ("save to sources") | `brain submit` through G1 | Javis skips G1 |
| Learning after every chat | None | On by default, in write mode |
| Curator, wiki LINT | `brain check` | Javis's LINT only suggests; `brain check` is the rule |
| Kanban tasks, loops | Next actions labelled `@javis:<level>` | Javis works only on tasks you assigned with `brain assign` |
| Permission modes `suggest`, `auto`, `full` | The level on the `@javis` label | Same three names, same meaning. A loop's mode is the ceiling for the tasks it takes |
| Loops, reminders | Daily, weekly and monthly rhythm | Use them to run the rhythm, read-only |
| Skills, plugins | `AGENTS.md`, the `brain` CLI | The plugin in this package connects the two |

## Conflicts to know up front

1. **Self-learning is on by default, in write mode.** Every few chat turns, Javis distils the conversation into `memory/facts/`, `wiki/` pages and new skills, and commits them with a `learn:` prefix. AI-written wiki pages are exactly what principle 2 forbids, and the facts in them carry no source record.
2. **INGEST bypasses G1.** Drop a file into the chat and say "save to sources", and Javis writes straight to `sources/` and `wiki/`.
3. **Javis creates folders in the brain.** On the first chat turn it creates `memory/`, `skills/` (the system skills), `.claude/skills/`, `Javis/` and a few housekeeping files. If you press "create standard structure" or "normalise structure" in Settings, it also creates `sources/`, `wiki/`, `agents/`, `workflows/`, `attachments/`, `00 - Dashboard/`, `01 - Daily Log/`… It deletes nothing of yours, but it clutters the tree if pointed at `vault/`.
4. **Self-learning touches the repository's git.** When the brain is already a git repository, Javis merges a block into `.gitignore` that ignores everything except text extensions, and commits it as `chore:`. New files without a text extension (a script such as `bin/brain`, for example) are then skipped by `git add`. Files already tracked are not affected.
5. **Only the Claude Code engine reads the repository's `CLAUDE.md`.** Javis runs Claude Code with the brain as its working directory and loads the project settings, so `CLAUDE.md` at the brain root applies. API engines see only Javis's prompt, `MEMORY.md` and the Javis project instructions.
6. **The plugin hook only sees tools that go through the MCP Hub.** Claude Code writes files with its own Write and Edit tools, which bypass the hub. It needs a Claude Code hook as well (step 7).
7. **Loops created from chat default to `full`**, which allows real actions outside. For the brain, use `suggest` (read-only) for every rhythm task.

## Setup, step by step

### 1. Install Javis

Follow the [Javis quick start](https://github.com/blogminhquy/javis-os#-quick-start). Read Javis's warning about running background work on a Claude Pro/Max subscription: 24/7 background work or running on a VPS falls outside personal use. For background work, use an API key or point the "background model" at another provider.

### 2. Point the brain at the brain repository root

In the top-left corner of the toolbar, press 📁 and choose the **repository root**, the folder that holds `brain.toml`, not `vault/`.

Why: the folders Javis creates then sit next to `vault/`, outside what `brain check` scans, and the plugin finds `brain.toml` and the `tools/brain` package. The knowledge graph still draws the notes in `vault/`.

**Do not press** "create standard structure" or "normalise structure" for this brain. Ignore the "structure not standard" banner.

### 3. Add to the repository's `.gitignore`

```gitignore
# Javis OS: raw logs, caches and run state
memory/conversations/
attachments/
inbox/
.javis-learn.lock
Javis/learn-staging/
Javis/learn-log/
Javis/loop-log/
Javis/skill-usage.json
drafts/
```

`memory/conversations/` holds raw conversations and may contain things you pasted by mistake. `attachments/` and `inbox/` are caches Javis clears after 30 days (not the same as `vault/00-Inbox/`). `drafts/` is where Javis puts drafts at level `auto`, and where shell engines write source records before submitting them.

### 4. Turn self-learning down to a mode that writes nothing

Open **Self-learning** (Brain group). The **Write mode** field has three buttons: Dry run, Suggest and Write automatically. A fresh install uses Write automatically.

- **Recommended:** Dry run or Suggest. Neither creates files; both only log "what it would learn" for you to read and decide.
- **If you still want Javis to remember things about you:** keep Write automatically, but under **What to learn** turn on Memories only and turn off Wiki and Skills. Memories live in `memory/` at the repository root, outside `vault/`, and each learning pass is a `learn:` commit in your repository.
- **Curator:** leave it off. Use `brain check` instead of the wiki LINT.
- Press **Save**. The mode and switches only take effect after saving.

The self-learning writer is Javis's own Python code and does not go through a tool, so the plugin hook cannot block it. Only the settings here keep it out of `vault/`.

Do not use INGEST. To bring a document into the brain, follow "Verified research" below.

### 5. Set the rules for every engine

- **Claude Code and Codex engines:** copy the rules to the repository root as in [using-with-ai.md](using-with-ai.md):

  ```sh
  cp vault/AGENTS.md AGENTS.md
  cp vault/AGENTS.md CLAUDE.md
  ```

- **Every engine:** create a Javis project, for example "Brain", open its panel (the **Instructions** tab) and paste the [shared rule block](using-with-ai.md#the-shared-rule-block), plus three lines:

  ```text
  9. In Javis: use the tools brain_capture, brain_submit, brain_check, brain_turn, brain_weekly, brain_assigned and brain_report instead of shell commands.
  10. Facts you look up: write each claim as a source record following vault/_templates/source-record.md and submit it with brain_submit, passing the whole record in the record parameter. Never write to vault/00-Inbox/agent.
  11. Never use INGEST, and never write to sources/ or wiki/.
  ```

  Project instructions go into every chat turn in that project, for every engine, up to 4,000 characters. Chats outside the project do not get them, so work with the brain inside this project.

### 6. Install the `brain-standard` plugin

This package ships a plugin in `integrations/javis/brain-standard/`. It does two things:

- It exposes seven commands as tools for every engine:

  | Tool | Command | Minimum level |
  | --- | --- | --- |
  | `brain_capture` | `brain capture` · captures your words | `auto` |
  | `brain_turn` | `brain turn` | `auto` |
  | `brain_submit` | `brain submit` · brings facts in through G1 | `suggest` |
  | `brain_check`, `brain_weekly` | `brain check`, `brain weekly` | `suggest` |
  | `brain_assigned` | `brain assigned --level` · lists the tasks assigned to Javis | `suggest` |
  | `brain_report` | `brain report` · sends the result back to the Inbox | `suggest` |

  `brain_submit` and `brain_report` run at `suggest` because the only writes to the brain are the CLI's own: the item that passed G1, the done mark and one Inbox line. `brain_submit` takes the whole record (`record`), writes it to a temporary folder outside the vault and submits it, so a read-only run can still submit facts it looked up. If the record is already in a file, pass `file`. There is no tool for `brain assign`: only you assign tasks.
- A `pre_tool_call` hook stops the AI from writing with `javis_write_file` or `javis_edit_file` to `30-Knowledge/permanent/`, `00-Inbox/agent/` and any file or folder in `vault/` whose name starts with `_`, and stops it from adding or raising an `@javis` label in Next Actions. The AI gets back an explanation and the right way to do it. The protected paths and tools come from `[assistant.guard]` in the config.

Copy it into the brain (the repository root):

```sh
mkdir -p plugins
cp -r integrations/javis/brain-standard plugins/
```

To give it to every brain in Javis, copy it to `<JAVIS_STATE_DIR>/plugins/` instead of `plugins/` in the repository. The plugin ships with `enabled: false`; read `plugin.py`, then switch it on from the Javis **Plugins** page, or change it to `enabled: true`.

The plugin uses only the standard library and calls back into the repository's `brain` package, so the rules live in one place. Timeouts and the default channel come from `[assistant.plugin]`. If the brain selected in Javis is not a brain repository, the tools report an error and the hook blocks nothing.

### 7. A hook for Claude Code

Add this to `.claude/settings.json` at the repository root (Javis loads it when it runs the Claude Code engine, and so does Claude Code run directly in the repository):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|NotebookEdit",
        "hooks": [
          { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/integrations/javis/claude_write_guard.py\"" }
        ]
      }
    ]
  }
}
```

The script applies the same guard as the plugin. On Windows change `python3` to `python`. The hook is useful even when you use Claude Code without Javis.

## Sample workflows

### Capture from your phone

Message Javis on Telegram:

> capture: ask the accountant again about the October invoice

Javis calls `brain_capture` with channel `telegram`. The item lands in `vault/00-Inbox/Inbox.md`, exactly as if you had typed `brain capture` at the computer.

### Daily loop

Create a reminder on the **Scheduled tasks** page, or say in chat:

> Create a reminder at 7:00 every day, read-only: read vault/10-Action/11-next-actions.md, suggest at most 3 tasks for today, run brain_check and report any errors. Send the result to Telegram.

Level `suggest` can read files and call `brain_check`, and writes nothing. You pick the tasks.

### Weekly Review

> Create a reminder at 17:00 on Sunday, read-only: run brain_weekly, then go through vault/weekly/_template-weekly.md and point out stalled projects, Inbox items older than 7 days and late milestones. Send it to Telegram.

You sit down, decide, then save the metrics yourself with `brain weekly --save`.

### Verified research

> Look this up for me: <question>. Split the answer into single claims. Write each claim as a source record following vault/_templates/source-record.md, then submit it with brain_submit using the record parameter.

CLI engines have the web built in; API engines use `javis_web_search` and `javis_web_fetch`. Items without a record are returned by G1, and items graded E or credibility 5 go to `_log/rejected.md`. Records passed through `record` leave no file behind; shell engines that write records into `drafts/` should delete them after submitting.

### Clarifying the Inbox

A `suggest` loop suits a crowded Inbox:

> Create a 60-minute loop, read-only: on each cycle read vault/00-Inbox/Inbox.md, pick one item not yet clarified, answer the 2 questions and suggest a destination. Do not move the item.

The loop only suggests; you move the item. Do not use Javis's sample "digest sources" loop.

### The assistant loop: Javis follows up on assigned tasks

You assign a task after clarifying it:

```sh
bin/brain assign "accountant" auto    # adds @javis:auto · assigned <today> to that next action
```

Then create one loop per level, with the loop's mode equal to the level of the tasks it takes:

> Create a 30-minute loop, read-only, named "Javis · suggest": on each cycle call brain_assigned with max_level suggest. If there is nothing, stop. Otherwise work on task 1: research and propose; write each fact you look up as a source record and submit it with brain_submit using the record parameter. When done, call brain_report for number 1 with max_level suggest, and a one-sentence result saying what you did and where the result is.

> Create a 30-minute loop, mode auto, named "Javis · auto": as above but with max_level auto; it may write drafts in drafts/, code in the 5x area and issues on the board.

Create a `full` loop only when there is real outside work to do, such as sending an approved email, and switch it off when the work is done.

Each result is a `(javis) Result "…": …` line in the Inbox. You clarify it like any other item: a draft becomes the next task, a fact becomes literature, or you drop it. `brain check` warns about tasks assigned more than 7 days ago and not done (`[assistant] stale_after_days`); `brain weekly` counts assigned, done and stale tasks.

### Closing a turn

At the end of each turn of work in the "Brain" project, Javis calls `brain_check`, fixes errors if it can, then `brain_turn`. Committing is still your job, or the job of an engine with a shell.

## Staying safe

- **Javis runs the AI with full rights on the machine.** On a VPS Javis requires a login; still keep the brain repository private and don't expose Javis to the internet unless you need to.
- **Loops and reminders for the brain use `suggest`.** Raise to `auto` only for work that writes, such as `brain_capture` or the "Javis · auto" loop. Use `full` only for the loop that works on `@javis:full` tasks, and switch it off when the work is done.
- **Back up with the brain repository's own git.** You don't need Javis's "GitHub backup" for this brain.
- **The plugin runs real Python code inside the Javis server.** Read `plugin.py` before enabling it.
- **The hook does not replace the rules.** It blocks the most common way to write, not every way, a shell command for example. `brain check` and your own review remain the final gate.

## Sources

Checked 21/10/2026 on Javis OS 0.270.0. Recheck after upgrading.

- Brain layout, memory, INGEST, cache folders: [docs/en/13-second-brain.md](https://github.com/blogminhquy/javis-os/blob/main/docs/en/13-second-brain.md)
- Self-learning on by default, write mode, learning memories, wiki and skills: [docs/en/22-self-learning.md](https://github.com/blogminhquy/javis-os/blob/main/docs/en/22-self-learning.md), `server/learn.py`, `LearnFeature.DEFAULT`
- Folders Javis creates: `server/main.py`, `STANDARD_STRUCTURE`, `_ensure_brain_scaffold`; `server/system_sync.py`, `sync_brain`
- Merging `.gitignore` and committing in an existing repository: `server/git_brain.py`, `ensure_git_repo`
- Claude Code runs in the brain folder and loads project settings: `server/claude_sdk_engine.py`, `setting_sources`
- Plugins, tools, and a `pre_tool_call` hook that can block with `{"deny": …}`: `server/plugins_host.py`, `register_tool`, `register_hook`, `wrap_with_hooks`
- Project instructions go into every chat turn, capped at 4,000 characters: `server/main.py`, `build_system_prompt`, `_project_block`; `server/sessions.py`, `PROJECT_INSTRUCTIONS_MAX`
- Enabling and disabling plugins on the Plugins page: [docs/en/20-plugins.md](https://github.com/blogminhquy/javis-os/blob/main/docs/en/20-plugins.md)
