# System architecture · Brain 4.0

The architecture design document (DAB) for Brain_Standard. It follows the [arc42](https://arc42.org) template and the viewpoints of ISO/IEC/IEEE 42010; diagrams follow the C4 model; decisions are recorded as Michael Nygard-style ADRs. The business rules are explained in the other `docs/` pages; this page describes how the system is built, how it runs and why it was built this way, in enough detail to rewrite the CLI from scratch without reading the code. Terms are defined in [glossary.md](glossary.md).

## Contents

0. [About this document](#0-about-this-document)
1. [Introduction and goals](#1-introduction-and-goals)
2. [Constraints](#2-constraints)
3. [Context and scope](#3-context-and-scope)
4. [Solution strategy](#4-solution-strategy)
5. [Building block view](#5-building-block-view)
6. [Runtime view](#6-runtime-view)
7. [Deployment view](#7-deployment-view)
8. [Cross-cutting concepts](#8-cross-cutting-concepts)
9. [Architecture decisions](#9-architecture-decisions)
10. [Quality requirements](#10-quality-requirements)
11. [Risks and technical debt](#11-risks-and-technical-debt)
12. [Future work · retrieval layer (proposed 4.1)](#12-future-work--retrieval-layer-proposed-41)
13. [Glossary](#13-glossary)
14. [References](#14-references)
15. [Maintaining this document](#15-maintaining-this-document)

## 0. About this document

| Item | Value |
| --- | --- |
| System | Brain_Standard · a second brain made of Markdown + git + the `brain` CLI |
| System version described | 4.0.1 (current: 4.0.0 plus a Docker image and CI; 4.0.0 brought English names, the modular package, defaults in configuration, `brain migrate`) and 4.1 (proposed, section 12) |
| Document version | 4.0. Version 3.0 (in Vietnamese) is in git history; version 1.1 is kept at [`archive/2.2.1/docs/kien-truc-he-thong.md`](../archive/2.2.1/docs/kien-truc-he-thong.md) |
| Status | Awaiting Design Authority Board review; code, tests and plugin are done; Javis OS has not yet run on a real brain |
| Owner | The owner of the Brain_Standard repository |
| Last updated | 22/10/2026 |
| Sources of truth | `tools/brain/` (package and `defaults.toml`), `brain.toml`, `tests/`, `integrations/javis/`, `vault/`, the `docs/` pages |
| Related systems | [Javis OS](https://github.com/blogminhquy/javis-os) 0.270.0, Claude Code |

### 0.1 Scope

The document covers the vault's data standard, the `brain` CLI, the check rules, how AI and agents interact with the brain, the assistant loop introduced in 3.0 (Javis captures, the owner clarifies, Javis follows up), the Javis OS plugin and hooks, deployment, migration from 3.0, and the design of the proposed retrieval layer. It does not replace the user guide ([getting-started.md](getting-started.md)) and does not re-explain GTD, Zettelkasten and the other methods beyond what the architecture needs.

### 0.2 Reading paths

| You are | Read |
| --- | --- |
| The brain's owner, wanting to understand the system | 1, 3, 4, 9, 11 |
| Changing the CLI | 5, 6, 8, 10, 11 |
| An agent working in the repository | 6.7, 8.1–8.4, 8.10 |
| Building the retrieval layer | 8, 12 |
| Running Javis | 1.7, 5.4, 6.9–6.12, 7.4, 8.4 (AS), 9 (ADR-10–12), 11 |
| Upgrading a 3.0 brain | 6.13, 7.2, 8.13, ADR-13, ADR-14 |

### 0.3 Conventions

- **Must / must not**: a rule the CLI or `AGENTS.md` enforces.
- **Should**: a recommendation that is not checked automatically.
- **(proposed)**: not in the code yet.
- Paths inside the vault are relative to `vault/`; other paths are relative to the repository root.
- Function names, configuration keys and frontmatter keys are written in `code`, exactly as in the source.

### 0.4 Document history

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 21/10/2026 | First version in arc42 form: collected the descriptions scattered across `docs/` and `tools/brain.py`, added ADRs, risks, and the 2.3 retrieval layer design |
| 1.1 | 21/10/2026 | Full detail: use cases, per-command specifications, rule catalogue, configuration reference, line grammar, threat model, test traceability, full ADRs, retrieval layer DDL and algorithms, MCP tool schemas, acceptance criteria |
| 3.0 | 21/10/2026 | DAB 3.0: the Javis loop in every view (requirements F13–F18, use cases UC10–UC12, success metrics, new containers and components, the assign, list and report commands, Javis OS deployment, label grammar, rules for labels, the `[javis]` table, threats, tests, ADR-10–12, risks R14–R17, open decisions). The retrieval layer moved from 2.3 to 3.1 |
| 4.0 | 22/10/2026 | DAB 4.0, in English: every command, key, rule code and file name in English; the CLI split into a package of modules (ADR-13, superseding ADR-02); every parameter in `defaults.toml`; rule codes in CLI messages; `brain migrate` (6.13); R9 fixed; English naming (ADR-14, superseding ADR-09). The retrieval layer moved from 3.1 to 4.1 |
| 4.0.1 | 29/10/2026 | Packaging: the Docker image as a deployment node (7.1, 7.2), CI and the release workflow in the test strategy (8.12), R7 resolved. No change to the flow, the rules or the data |

## 1. Introduction and goals

### 1.1 The problem

Someone who juggles many tasks, reads a lot, writes code and uses several AIs runs into five problems: tasks and ideas get scattered; reading a lot without remembering; half-finished projects with no clear next step; files all over the place; and AIs that forget between sessions, sometimes make things up, and behave differently on every platform. The brain answers with a single flow: everything goes into **one Inbox**, is clarified with **two questions**, then goes into exactly **one of three lanes**. The lanes exchange items through **7 links, I1–I7**. Facts an AI brings in must pass **gates G1–G4**. See [flow.md](flow.md).

Version 3.0 added **Javis**, an operations assistant, at both ends of the flow: Javis **captures** from Telegram, voice and the web into the Inbox, and **follows up** on next actions the owner has clarified and assigned with a `@javis:<level>` label. The middle, the two questions and the choice of lane, stays with the owner. Javis's results come back to the Inbox. See [flow.md](flow.md#the-assistant-loop) and [using-with-javis-os.md](using-with-javis-os.md).

Version 4.0 changes no behaviour of the flow. It makes the system readable for anyone (English names that say what they mean), reusable (one package of small modules shared by the CLI, the plugin and the hook) and configurable (every parameter in a configuration file, none hardcoded).

### 1.2 Functional requirements

| Code | Requirement | Priority | Status | Implemented by | Test |
| --- | --- | --- | --- | --- | --- |
| F1 | Capture the owner's words to the Inbox, with time and channel | Must | Done | `brain capture` | `test_capture_to_inbox` |
| F2 | Accept facts an agent brings in only with a source record holding every required field | Must | Done | `brain submit` | `test_submit_without_full_record_is_returned` |
| F3 | Read the Admiralty grade and decide how far the item may go | Must | Done | `gates.reach` | `test_reach_and_inbox_line` |
| F4 | Reject source E or credibility 5: log it, keep it out of the Inbox | Must | Done | `brain submit` | `test_rejected_grades_go_to_log` |
| F5 | Check the vault against the lane rules and gates G1–G3 | Must | Done | `brain check` | several, section 8.12 |
| F6 | Close a turn of work; refuse while the vault has errors | Must | Done | `brain turn` | `test_turn_*` |
| F7 | Metrics for the Weekly Review; measure, never block | Must | Done | `brain weekly` | `test_weekly` |
| F8 | One rule set for every AI | Must | Done | `vault/AGENTS.md`, [using-with-ai.md](using-with-ai.md) | Manual |
| F9 | Check gate G4 (flashcards) | Should | Not yet | | |
| F10 | Check that the Johnny Decimal index matches the folders | Should | Not yet | | |
| F11 | Find notes by keyword and by meaning | Should | Proposed | `brain index`, `brain search` | Section 12.13 |
| F12 | Let MCP clients read the brain and write through the gates | Should | Proposed | `brain mcp` | Section 12.13 |
| F13 | The owner assigns a next action to Javis with a level and the date | Must | Done | `brain assign` | `test_assign_adds_label_and_date`, `test_assign_needs_exactly_one_match` |
| F14 | List assigned tasks, filtered by the level of the run | Must | Done | `brain assigned --level` | `test_assigned_filters_by_level` |
| F15 | Report an assigned task done; the result goes back to the Inbox | Must | Done | `brain report` | `test_report_checks_off_and_writes_inbox` |
| F16 | Catch labels without a level and stale assignments | Must | Done | `brain check` (AS-01, AS-02) | `test_check_assignment_rules` |
| F17 | Measure assignments in the Weekly Review | Should | Done | `brain weekly` | `test_weekly_counts_assignments` |
| F18 | Every Javis OS engine can use the `brain` commands, and the AI can neither assign itself work nor take write shortcuts | Must | Done | `integrations/javis/` | `tests/test_javis_plugin.py` |
| F19 | Every parameter lives in configuration; a brain overrides only what it changes | Must | Done | `tools/brain/defaults.toml`, `config.merge` | `test_config_override_beats_default`, `test_turn_type_from_config`, `test_assistant_name_and_label_from_config`, `test_guard_paths_from_config` |
| F20 | Convert a 3.0 brain to the 4.0 names once, with a dry run, without touching personal note content | Must | Done | `brain migrate` | `tests/test_migrate.py` |

### 1.3 Non-functional requirements

| Code | Requirement | Measured by |
| --- | --- | --- |
| N1 | Runs on Python 3.11+ with the standard library only | No imports outside the standard library in `tools/brain/` |
| N2 | Runs on Linux, macOS and Windows | The `bin/brain` and `bin/brain.cmd` wrappers; UTF-8 on the console |
| N3 | Needs no network | The CLI opens no connections |
| N4 | Never edits or deletes an existing note, except `brain migrate` when the owner runs it | Section 8.8 |
| N5 | Deterministic results when the clock is fixed | `BRAIN_NOW` |
| N6 | Messages in English that name the file, the rule code and the problem | Message format, section 8.4 |
| N7 | `brain check` runs in under 2 seconds on a 5,000-note vault on a personal machine | Not measured yet, risk R2 |
| N8 | The Javis plugin uses only the standard library and reuses the `brain` package; no copied rules | The plugin imports nothing outside the standard library; every tool runs the CLI; the hook calls `brain.guard` |
| N9 | No hardcoded parameters: paths, thresholds, names, labels, levels and messages' fixed parts come from configuration | `tools/brain/defaults.toml`; review |

### 1.4 Quality goals

In priority order. When two conflict, the higher one wins.

| # | Goal | Meaning | Example when they conflict |
| --- | --- | --- | --- |
| Q1 | Data ownership and durability | Plain Markdown in git, opens in any editor, outlives every tool | Never keep data only in a database, even if faster |
| Q2 | Knowledge integrity | Facts an AI brings in cannot enter without a source and a grade; the grade decides how far they go | Accept an extra step for agents to write a source record |
| Q3 | Simplicity | A small standard-library package, no server | Don't add a YAML library even though the hand-written frontmatter reader is limited |
| Q4 | AI-platform neutrality | Switching AI loses nothing | Never rely on one platform's features in the rules |
| Q5 | Verifiability | Every CLI rule has a test; the clock can be faked | Rules as pure functions in their own module, easier to test than logic inside `main` |

### 1.5 Stakeholders

| Role | Expects | Architectural concern |
| --- | --- | --- |
| The brain's owner | Quick capture, nothing forgotten, knowledge that becomes their own | Q1, Q2, capture speed, easy to edit by hand |
| Agents in the repository (Claude Code, Codex, Gemini CLI, Cursor, Copilot) | Clear rules, checkable commands, machine-readable exit codes | Stable exit codes, messages with paths and rule codes |
| Chat AIs (levels 1–2) | A short rule block, the `Brain:` line | Q4 |
| Contributors to the standard | Small code, tests, a clear changelog | Q3, Q5 |
| Collaborators on a board | Backlog, people and deadlines on the board | Boundary between brain and board (ADR-07) |
| Javis (Javis OS or a similar agent) | Knows which tasks it may do, up to what level, and where to send results | The `@javis` label, levels, tools without write shortcuts (ADR-10–12) |
| Readers who don't speak Vietnamese | Names and docs they can read | ADR-14 |

### 1.6 Main use cases

| Code | Use case | Actor | Main flow | Command |
| --- | --- | --- | --- | --- |
| UC1 | Capture an idea | The owner; an AI via `capture:` | Type a sentence → a new Inbox line | `brain capture` |
| UC2 | Submit a researched fact | Agent | Write a source record → submit → G1 → Inbox or log | `brain submit` |
| UC3 | Clarify the Inbox | The owner, with AI suggestions | Each item through the two questions → moved into a lane by hand | None (edit files) |
| UC4 | Create a project | The owner | Copy `_template-project.md` → fill in the criteria → for many steps, open a category, repository and board (I3) | `brain check` |
| UC5 | Write a permanent note | The owner | Write in their own words → at least 1 link → G3 | `brain check` |
| UC6 | Close a turn | Person or agent | Check → fix errors → log the turn → commit | `brain turn` |
| UC7 | Weekly Review | The owner | Get the metrics → go through the weekly template → decide | `brain weekly --save` |
| UC8 | Switch AI | The owner | Copy `AGENTS.md` under the new tool's name, or paste the rule block | None |
| UC9 | Ask an AI about old notes | The owner through an MCP client | The AI calls `search` → reads notes → answers with paths and grades | **(proposed)** `brain mcp` |
| UC10 | Capture through Javis | The owner on Telegram, Javis | The owner's words → `brain capture --channel telegram`; facts Javis looks up → `brain submit` | `brain capture`, `brain submit` |
| UC11 | Assign a task to Javis | The owner | After clarifying → pick a next action → add the label and level | `brain assign` |
| UC12 | Javis follows up | Javis (one loop per level) | Take tasks at or below the run's level → do them → report → the result goes to the Inbox → the owner clarifies it | `brain assigned`, `brain report` |
| UC13 | Upgrade a 3.0 brain | The owner | Pull `tools/` and `bin/` → dry run → migrate → check → commit | `brain migrate` |

### 1.7 Success metrics for the assistant loop (proposed)

Measured after 4 weeks of real use, with `brain weekly`.

| Metric | Target |
| --- | --- |
| Inbox items arriving through Javis (Telegram, voice…) | ≥ 30% of new items |
| Assigned tasks done this week / assigned this week | ≥ 70% |
| Assigned tasks stale for more than 7 days | ≤ 2 |
| Oldest Inbox item | ≤ 7 days, as in 2.2 |

## 2. Constraints

### 2.1 Technical

| Constraint | Reason | Consequence |
| --- | --- | --- |
| Python 3.11 or newer | `tomllib` ships with 3.11 | Older machines need a newer Python |
| Standard library only | Installs anywhere, no `pip` | Hand-written frontmatter reader (R1) |
| A package of small modules in `tools/brain/`, run with `python -m brain` | Each concern reusable on its own by the CLI, the plugin and the hook (ADR-13) | `bin/brain` sets `PYTHONPATH`; no install step |
| `.md` files in UTF-8 with `\n` line endings | Readable by people, Obsidian and every AI | The CLI writes with `newline="\n"` |
| One-line `key: value` frontmatter | No YAML library | No multi-line values; lists are strings |
| Defaults in `tools/brain/defaults.toml`, overrides in `brain.toml` at the root | One place per concern; the brain's root is recognised by `brain.toml` | New parameters reach existing brains with the code |

### 2.2 Organisational

| Constraint | Reason |
| --- | --- |
| A user's brain repository must be private | Notes are personal data |
| Designed for one person; teamwork only on each project's board | Keeps the flow simple |
| AI never writes permanent notes, never deletes data, never raises a grade | Principles 2 and 3 in the README |
| No limit on projects or next actions since 2.2.0 | Measure instead of forbid (ADR-06) |
| Only the owner assigns tasks to Javis; Javis works only on labelled tasks and never above the label's level | ADR-10, ADR-11 |
| Javis's background work does not run on a Claude Pro/Max subscription | Those plans are for personal use; 24/7 work runs on an API key or another model |

### 2.3 Conventions

| Topic | Convention |
| --- | --- |
| Versions | x.y.z: x changes the shape of the flow or needs a migration, y adds a mechanism without breaking the flow, z fixes wording, labels or numbers. Recorded in [CHANGELOG.md](../CHANGELOG.md) and `brain.version` in `defaults.toml` |
| Names in code | English, `snake_case`, saying what they mean: `submit`, `reach`, `block_reason` |
| Frontmatter keys | English, `snake_case`: `done_when`, `retrieved` |
| Vault folder names | Numeric prefixes from PARA and Johnny Decimal: `00-Inbox`, `10-Action`, `30-Knowledge`… |
| Templates | Start with `_`, are skipped by checks, and are never edited directly |
| Dates | ISO 8601: `YYYY-MM-DD`, month `YYYY-MM`, time `YYYY-MM-DD HH:MM` |
| Messages | English, as `<rule code> · <path>: <problem>` |

## 3. Context and scope

### 3.1 Business context

```mermaid
flowchart LR
  U["The owner"] -- "own words: capture, clarify, write notes" --> B["Brain<br/>vault + brain CLI"]
  AI["Chat AI<br/>Claude, ChatGPT, Gemini, local"] -- "Brain: … line<br/>the owner copies it in" --> U
  AG["Agent in the repository<br/>Claude Code, Codex, Cursor…"] -- "brain capture / submit / check / turn" --> B
  JV["Javis OS<br/>operations assistant"] -- "capture: brain_capture, brain_submit<br/>follow up: brain_assigned, brain_report" --> B
  U -- "brain assign" --> B
  TG["Telegram, voice, web"] --> JV
  WEB["Outside sources<br/>web, papers, APIs"] -- "facts + source record" --> AG
  B -- "multi-step projects" --> BD["Project board<br/>GitHub Projects…"]
  B -- "git push" --> R["Private git remote"]
  FSRS["FSRS flashcard tool"] -. "cards made from permanent notes" .- B
```

| Partner | Into the brain | Out of the brain | Through a gate |
| --- | --- | --- | --- |
| The owner | Notes, decisions, permanent notes | Next Actions, metrics, notes to reread | No |
| Chat AI | Nothing directly; the owner copies the `Brain:` line | Notes pasted into the chat | G1 for facts the AI looked up |
| Agent in the repository | Inbox items, items through G1, file edits following `AGENTS.md` | The whole vault | G1 for outside facts |
| Javis | The owner's words from a channel; items through G1; done marks and result lines for assigned tasks | Assigned tasks, metrics, notes to read | G1 for facts it looks up; no permanent notes, no self-assignment |
| Outside sources | Only through an agent | No | G1 required |
| Board | No, the brain only keeps a link | Board link, milestone, issue numbers | No |
| FSRS tool | No | Card content | G4 |
| Git remote | No | Backups, history | No |

### 3.2 Technical context

| Channel | Protocol · format | Details |
| --- | --- | --- |
| Command line | `brain [--root DIR] <command> …` | Section 6; exit codes in 8.10 |
| stdout / stderr | UTF-8 text | Results go to stdout; bad input and refusals to stderr |
| Data files | Markdown + frontmatter | Sections 8.1–8.2 |
| Configuration | TOML: `tools/brain/defaults.toml` merged with `brain.toml` | Section 8.5 |
| Environment variables | `BRAIN_ROOT`, `BRAIN_NOW` | Sections 8.6–8.7 |
| Javis OS plugin | `register_tool`, `register_hook("pre_tool_call")`; tools run the CLI in a subprocess | Section 5.4 |
| Claude Code hook | PreToolUse, JSON on stdin, exit code 2 to block | Section 5.4 |
| Git | Plain git commands | Outside the CLI; people and agents commit and push |
| MCP | JSON-RPC over stdio | **(proposed)** section 12.9 |

### 3.3 Out of scope

- Real-time sync, or several people editing one vault.
- Reminders, push notifications, a dedicated mobile app.
- Replacing the project board.
- An FSRS review scheduler.
- Automatic Inbox clarifying: AI and Javis only suggest, the owner decides (see the open decisions in 11.1).
- Syncing issue status from the board back to Next Actions.
- Encrypting the vault at rest: rely on disk encryption and private repository access.
- A translation layer for messages: 4.0 is English only.

## 4. Solution strategy

| Goal | Approach | ADR |
| --- | --- | --- |
| Q1 Data ownership | Files are the only source of truth; any index is derived data that can be rebuilt | 01, 08 |
| Q2 Knowledge integrity | G1 blocks hard at the door; G2–G3 at the lane doors; two-axis Admiralty grades; thresholds in configuration | 04 |
| Q3 Simplicity | Small standard-library modules, short commands, no daemon | 13 |
| Q4 AI neutrality | Rules written as plain text; CLI commands are the common API for every agent | 05 |
| Q5 Verifiability | Rules in pure functions (`gates.reach`, `checks.check`, `metrics.measure`); the clock through `config.now()`; tests on a temporary vault | 13 |
| Q2 with Javis | AI at both ends, a person in the middle; the label and level on the task line; no assign tool in the plugin; a hook blocks write shortcuts | 10, 11, 12 |
| Reuse and configurability | One package used by the CLI, the plugin and the hook; every parameter in `defaults.toml`, overridable per brain | 13 |
| Readability | English names chosen for meaning, a glossary, a one-time migration | 14 |

The business model combines four methods: GTD + PARA for the action lane, Zettelkasten + LYT + FSRS for the knowledge lane, Johnny Decimal for the files and code lane, and the Admiralty system for trust. Rule details: [lanes.md](lanes.md), [trust-gates.md](trust-gates.md), [execution-layer.md](execution-layer.md).

Basic split of responsibilities:

| Work | Who |
| --- | --- |
| Decide which lane an item goes to | The owner (AI and Javis suggest) |
| Assign tasks to Javis and pick the level | The owner, with `brain assign` |
| Follow up on assigned tasks and report results | Javis, through the plugin's tools |
| Move files between lanes | The owner or an agent, editing files directly |
| Write the Inbox, accept agent items, write logs | The CLI |
| Check the rules | The CLI |
| Commit and push | The owner or an agent |

## 5. Building block view

### 5.1 Level 1 · Containers

```mermaid
flowchart TB
  subgraph Repo["Brain repository (git, private)"]
    CFG["brain.toml<br/>overrides"]
    V["vault/<br/>Markdown"]
    PKG["tools/brain/<br/>package + defaults.toml"]
    W["bin/brain · bin/brain.cmd<br/>wrappers"]
    AGM["vault/AGENTS.md<br/>rules for agents"]
    T["tests/<br/>unittest + fixtures"]
    D["docs/<br/>the standard"]
    PL["integrations/javis/<br/>plugin + hook"]
  end
  JOS["Javis OS"] -- "loads the plugin" --> PL
  PL -- "subprocess: python -m brain" --> PKG
  PL -- "import brain.guard" --> PKG
  W --> PKG
  PKG -- "reads" --> CFG
  PKG -- "reads, appends, creates" --> V
  T -- "calls brain.cli.main()" --> PKG
  AGM -. "agents read" .-> V
```

| Container | Responsibility | Does not |
| --- | --- | --- |
| `vault/` | Holds all data | Contain code |
| `brain.toml` | The brain's overrides of the defaults: usually only `[brain]` | Hold data |
| `tools/brain/` | Applies the rules, writes the Inbox and logs, accepts agent items, checks the vault, measures, migrates | Edit or delete existing notes (except `migrate`); call the network |
| `tools/brain/defaults.toml` | Every parameter with its default value and a comment | |
| `bin/brain` | POSIX wrapper: finds the repository, sets `PYTHONPATH`, runs `python3 -m brain` | |
| `bin/brain.cmd` | Windows wrapper: the same with `python -m brain` | |
| `vault/AGENTS.md` | Rules for agents; copied to the root as `AGENTS.md`, `CLAUDE.md` or `GEMINI.md` | |
| `tests/test_brain.py` | 28 behaviour tests on a temporary vault | |
| `tests/test_javis_plugin.py` | 24 test runs for the plugin and the Claude Code hook | |
| `tests/test_migrate.py` | 6 tests on a copy of a real 3.0 brain (`tests/fixtures/brain-3.0/`) | |
| `integrations/javis/brain-standard/` | Javis OS plugin: 7 tools that run the CLI, a `pre_tool_call` hook | Copy rules; offer an assign tool |
| `integrations/javis/claude_write_guard.py` | PreToolUse hook for Claude Code, using the same guard as the plugin | |
| `docs/` | The standard and guides | |

### 5.2 Level 2 · Vault layout

| Path | Lane | `[paths]` key | Shape | Written by the CLI? | Checked by |
| --- | --- | --- | --- | --- | --- |
| `00-Inbox/Inbox.md` | Entry | `inbox` | One file, one line per item | Appended (`capture`, `submit`, `report`) | `weekly` |
| `00-Inbox/agent/` | Entry | `inbox_agent` | One file per item | Created (`submit`) | G1-01…03, VD-01 |
| `10-Action/11-next-actions.md` | Action | `next_actions` | One file, a checklist | Lines edited (`assign`, `report`) | EX-02, AS-01, AS-02, `weekly` |
| `10-Action/12-waiting-for.md` | Action | `waiting_for` | One file | No | Not checked |
| `10-Action/13-Projects/` | Action | `projects` | One file per project | No | AC-01…03, EX-01…03 |
| `10-Action/14-someday.md` | Action | `someday` | One file | No | Not checked |
| `20-Areas/` | Action | `areas` | One file per area | No | Not checked |
| `30-Knowledge/fleeting/` | Knowledge | `fleeting` | One file per thought | No | KN-03 |
| `30-Knowledge/literature/` | Knowledge | `literature` | One file per source | No | G2-01…03, VD-01 |
| `30-Knowledge/permanent/` | Knowledge | `permanent` | One file per idea | No | KN-01, KN-02, G3-01…02, VD-01 |
| `40-Maps/` | Knowledge | `maps` | One file per MOC | No | Not checked |
| `Code/5x …/` | Files and code | `code` | AC.ID folders | No | Not checked (F10) |
| `Code/50 System/50.00 Index (JDex).md` | Files and code | | One file, one line per number | No | Not checked |
| `weekly/` | Rhythm | `weekly` | One file per week | Created (`weekly --save`) | |
| `90-Archive/` | Background | `archive` | Any | No | |
| `_log/rejected.md` | Background | `rejected_log` | One file, one line per rejected item | Appended (`submit`) | `weekly` |
| `_log/turns.md` | Background | `turn_log` | One file, one line per turn | Appended (`turn`) | `weekly` |
| `_templates/`, every `_*.md` file | Templates | `templates` | | No | Skipped |

`notes.list_notes(folder, skip_prefix)` returns every `*.md` file in a folder (recursively), skipping files and folders whose name starts with `files.template_prefix`, sorted by path. A missing folder returns an empty list, so a vault without some folders still checks.

### 5.3 Level 3 · Modules of the `brain` package

```mermaid
flowchart LR
  cli --> config
  cli --> intake --> gates
  intake --> notes
  cli --> checks --> gates
  checks --> notes
  checks --> assistant
  cli --> metrics --> assistant
  metrics --> notes
  metrics --> gates
  cli --> assistant --> notes
  cli --> migrate --> notes
  guard --> assistant
  guard --> notes
  plugin["Javis plugin"] --> guard
  hook["claude_write_guard.py"] --> guard
  config --> defaults[("defaults.toml")]
```

| Module | Main names | Role | Pure? |
| --- | --- | --- | --- |
| `config` | `BrainError`, `load_toml`, `merge`, `defaults`, `find_root`, `now`, `Brain`, `open_brain` | Load and merge configuration, find the root, the clock, the brain context | `merge` yes; the rest read disk or environment |
| `notes` | `read`, `write`, `append`, `split_frontmatter`, `frontmatter`, `add_frontmatter`, `title`, `slug`, `expires_on`, `note_date`, `list_notes`, `dated_lines`, `LINK_RE` | Files, frontmatter, text and dates | Text functions yes |
| `gates` | `grade_pattern`, `parse_grade`, `reach`, `missing_fields`, `grade_format`, `span`; `MALFORMED`, `REJECT`, `FLEETING`, `LITERATURE`, `CARD` | The trust model, all thresholds from `[gates]` | Yes |
| `intake` | `capture`, `submit`, `Submission` | The two ways in: the owner's words and agent items through G1 | No |
| `checks` | `check` | Returns `(errors, warnings)`, each prefixed with a rule code | Reads disk |
| `metrics` | `measure`, `render` | Weekly metrics as a dict, and the English table | Reads disk |
| `assistant` | `Assignment`, `label_re`, `assignments`, `open_up_to`, `is_stale`, `plain_text`, `assign`, `report` | The assistant loop on Next Actions | Reads and writes Next Actions and the Inbox |
| `guard` | `adds_label`, `block_reason` | The write guard for the plugin and the Claude Code hook, driven by `[assistant.guard]` | Reads disk |
| `migrate` | `CONFIG_TABLES`, `FIELDS`, `VALUES`, `RENAMES`, `LINE_RULES`, `convert_config`, `migrate_files`, `migrate_notes`, `run` | One-time conversion of a 3.0 brain | No |
| `cli` | `build_parser`, `main`, `cmd_*`, `check_level` | Parse arguments, call one module, print, return the exit code | |

`Brain` is a dataclass holding `root`, `cfg` and `now`, with the properties `vault`, `gates` (the `[gates]` table), `assistant` (the `[assistant]` table), `stamp` (`YYYY-MM-DD HH:MM`), `today`, the method `path(key)` returning `vault / paths[key]`, and `rel(p)` for messages.

### 5.4 Level 3 · The Javis plugin and the hook

| Part | Role | Note |
| --- | --- | --- |
| `plugin.yaml` | Declares the slug `brain-standard`, 7 tools, the `pre_tool_call` hook, `enabled: false` | The owner reads it and enables it on the Plugins page |
| `find_root(vault_root)` | Finds the root holding `brain.toml`, from `BRAIN_ROOT` or by walking up from the Javis vault | Not found: tools report an error and the hook blocks nothing |
| `brain_package(root)` | Imports the `brain` package of that repository; drops a cached copy from another repository first | Javis is one long-running process that may serve several brains |
| `run(ctx, …)` | Runs `python -m brain --root <root> …`, stopped after `[assistant.plugin] timeout_seconds` | A non-zero exit code is put at the top of the result |
| Tools | `brain_capture`, `brain_submit`, `brain_check`, `brain_turn`, `brain_weekly`, `brain_assigned`, `brain_report` | `min_mode` in section 6.12 |
| `brain.guard.block_reason(brain, tool, args, cwd)` | The shared write guard | Used by the Javis hook and the Claude Code hook |
| `claude_write_guard.py` | Reads the PreToolUse JSON, calls `block_reason`, exits 2 with the reason | Declared in `.claude/settings.json` |

`block_reason` refuses a file write by a tool in `[assistant.guard] write_tools` (by default `javis_write_file`, `javis_edit_file`, and Claude Code's `Write`, `Edit`, `MultiEdit`, `NotebookEdit`) when the target is inside the vault and:

| Target | Condition |
| --- | --- |
| `30-Knowledge/permanent/` | Always, while `permanent` is in `protected` |
| `00-Inbox/agent/` | Always, while `inbox_agent` is in `protected` (it must go through `brain submit`) |
| Any other `[paths]` key listed in `protected` | Always |
| A file or folder starting with `_` | Always (templates and logs) |
| `label_file` (Next Actions) | The new content has more labels at some level than the old one: a new or raised assignment |

## 6. Runtime view

Every command starts the same way: `cli.main` sets UTF-8 on stdout and stderr, parses the arguments, calls `config.open_brain` to find the root and merge the configuration (section 8.6), then calls the command function. Each command function is a thin wrapper around one module. Bad arguments are handled by `argparse` and exit with code 2; a `BrainError` raised anywhere is printed to stderr and its `code` becomes the exit code.

### 6.1 `brain capture`

| Item | Specification |
| --- | --- |
| Syntax | `brain capture <text…> [--channel CHANNEL]` |
| Input | The text is every remaining word, joined by spaces; `--channel` defaults to `[capture] default_channel` (`hand`; others such as `voice`, `telegram`, `mcp`, `export`) |
| Steps | 1. Collapse runs of whitespace into one space. 2. Empty → error. 3. Append one line to `inbox`; if the file does not exist, create it with `[files] inbox_header` |
| Writes | `00-Inbox/Inbox.md` |
| Line written | `- [2026-10-20 21:30] (hand) Read chapter 5` |
| Output | stdout: `Captured to Inbox: <text>` |
| Exit code | 0 success; 2 empty text |
| Note | No G1: the owner's words are trusted by default |

### 6.2 `brain submit`

| Item | Specification |
| --- | --- |
| Syntax | `brain submit <file.md>` |
| Input | A Markdown file with a source record in its frontmatter, anywhere on disk |
| Reads | The submitted file; the `[gates]` configuration |
| Writes | `00-Inbox/agent/<YYYYmmdd-HHMMSS>-<slug>.md` and `00-Inbox/Inbox.md`, or `_log/rejected.md` |
| Exit code | 0 passed; 2 file not found, missing fields (when strict), malformed grade; 3 rejected |

Steps (`intake.submit`):

1. File not found → stderr `File not found: …`, code 2.
2. Read the frontmatter; list the `required_fields` that are missing or empty (a value that is only a comment counts as empty).
3. Missing fields: with `strict = true`, stderr `G1 returned <name>: missing <fields>. Complete the source record and submit again.`, code 2. With `false`, print a warning and carry on.
4. Normalise `grade` (strip spaces, upper case) and call `gates.reach`.
5. `malformed` → stderr explaining the grade format, code 2. Note: with `strict = false` and no `grade`, the item is still returned at this step.
6. `reject` → append to `_log/rejected.md` (created with `[files] rejected_log_header`), stdout `G1 rejected …`, code 3. The item does not enter the Inbox.
7. Passed → add `max_reach: <card|literature|fleeting>` and `submitted: YYYY-MM-DD` to the frontmatter; for `fleeting` also add `label: unverified` (`[gates] unverified_label`). Write a new file to `inbox_agent`, then append one line to the Inbox, stdout `G1 passed: …`, code 0.

```mermaid
sequenceDiagram
  participant A as Agent
  participant C as brain submit
  participant L as _log/rejected.md
  participant AI as 00-Inbox/agent/
  participant I as Inbox.md
  A->>C: .md file with a source record
  C->>C: check required fields
  alt missing fields, strict = true
    C-->>A: returned, code 2
  end
  C->>C: gates.reach(grade)
  alt malformed
    C-->>A: returned, code 2
  else source E or credibility 5
    C->>L: line "rejected · grade · name · source"
    C-->>A: code 3
  else passed
    C->>AI: new file + max_reach, submitted (+ label: unverified)
    C->>I: line "(agent) title · grade · up to … → agent/name"
    C-->>A: code 0
  end
```

Example:

```text
$ brain submit research/inflation.md
G1 passed: September inflation was 2.9% · grade B2 · may go up to flashcard.
```

The submitted file itself is never deleted or changed. The title in the Inbox line is the first `# ` heading of the body, or the file name when there is none.

### 6.3 `brain check`

| Item | Specification |
| --- | --- |
| Syntax | `brain check` |
| Reads | `inbox_agent`, `literature`, `permanent`, `fleeting`, `projects`, `next_actions` (including `@javis` labels) |
| Writes | Nothing |
| Output | `Errors (n):` and `Warnings (m):`, one `  - …` line each; `Vault is clean.` when there is nothing |
| Exit code | 0 no errors (warnings allowed); 1 at least one error |

Order inside `checks.check`: G1 in `inbox_agent` → G2 in literature → permanent rules and G3 → fleeting age → `valid_until` on literature, permanent and inbox_agent → project rules → assistant rules (AS-01, AS-02). The full catalogue is in section 8.4.

Example:

```text
$ brain check
Errors (2):
  - KN-01 · 30-Knowledge/permanent/p1.md: permanent note links to no other note
  - G3-02 · 30-Knowledge/permanent/p1.md: permanent needs credibility 1–2, has B3
Warnings (1):
  - KN-03 · 30-Knowledge/fleeting/idea.md: fleeting note is 19 days old; move it to literature or delete it
```

### 6.4 `brain turn`

| Item | Specification |
| --- | --- |
| Syntax | <code>brain turn &lt;task&#124;idea&#124;file&#124;drop&gt; &lt;summary…&gt;</code> |
| Steps | 1. The type must be in `[turn] types`, else code 2. 2. Collapse the summary's whitespace; empty → code 2. 3. Run `checks.check`. 4. Errors and `strict = true` → print the errors (not the warnings), stderr `Turn not closed: fix n error(s), then run brain turn again.`, code 1. 5. Otherwise append to `_log/turns.md` (created with `[files] turn_log_header`) and print `Brain: <type> · <summary>`; with warnings also print `(m warning(s), see brain check)` |
| Writes | `_log/turns.md` |
| Exit code | 0 closed; 1 the vault has errors; 2 empty summary or unknown type |

The four default turn types: `task` produced something to do, `idea` produced something to keep, `file` produced a file or code, `drop` kept nothing. The types are validated against the brain's configuration, not a fixed list in the parser, so a brain can change them.

### 6.5 `brain weekly`

| Item | Specification |
| --- | --- |
| Syntax | `brain weekly [--save]` |
| Output | A Markdown table `## Metrics · <year>-W<week>` (`metrics.render`) |
| Writes | With `--save`: `weekly/<year>-W<week>.md`, overwritten if it exists, titled with `[files] weekly_title` |
| Exit code | Always 0 |

Each metric in `metrics.measure` (the 7-day window is the days `> today − 7`):

| Key | Definition |
| --- | --- |
| `week` | ISO year and week of today |
| `projects_active`, `projects_done`, `projects_stopped` | Projects whose `status` is `[project] active_status`, `done_status`, `stopped_status` |
| `projects_overdue` | Active projects past their `due` date |
| `next_open`, `next_done` | `- [ ]` and `- [x]` (or `[X]`) lines in Next Actions |
| `inbox` | Lines of the form `- [YYYY-MM-DD …]` in the Inbox |
| `inbox_oldest_days` | Age in days of the oldest Inbox line, 0 when empty |
| `fleeting_old` | Fleeting notes older than `fleeting_max_days` |
| `permanent_new` | Permanent notes dated (section 8.7) inside the 7-day window |
| `turns`, `turns_by_type` | Lines in `_log/turns.md` inside the window, counted per type |
| `rejected` | Lines in `_log/rejected.md` inside the window |
| `incomplete_records_pct` | % of files in `inbox_agent` missing at least one required field, rounded |
| `past_valid_until` | Literature, permanent and inbox_agent notes past their `valid_until` |
| `assigned_open` | Labelled tasks not done |
| `assigned_done` | Labelled tasks done, with `done` inside the window |
| `assigned_stale` | Open tasks with `assigned` older than `stale_after_days` |

### 6.6 The rhythm as runtime scenarios

| Rhythm | Scenario | Commands |
| --- | --- | --- |
| Whenever something comes to mind | Capture it at once | `brain capture` |
| Whenever an agent researches | Write a record, submit it | `brain submit` |
| After clarifying | Assign the tasks Javis can do | `brain assign` |
| Every 30 minutes, in a Javis loop | Take assigned tasks, do them, report | `brain assigned`, `brain report` |
| Every turn of work | Check, close the turn, commit | `brain check`, `brain turn` |
| Every morning, 30–45 minutes | Pick at most 3 tasks (`[rhythm] daily_pick_max`), do at least 1, review 15–20 cards | None |
| Sunday, 30 minutes | Weekly Review following `weekly/_template-weekly.md` | `brain weekly --save` |
| Every month | Recheck 10 random claims; if wrong, follow I7 | None |
| Every quarter | Each Area spawns a project; merge categories if needed | None |

### 6.7 An agent's turn

```mermaid
sequenceDiagram
  participant U as Owner
  participant A as Agent
  participant F as vault/
  participant C as brain CLI
  participant G as git
  U->>A: request
  A->>F: read AGENTS.md, related notes
  A->>A: two questions → choose the lane
  opt facts from outside
    A->>A: write a source record, grade it
    A->>C: brain submit
  end
  A->>F: edit or create files in the lane
  A->>C: brain check
  alt errors
    A->>F: fix
    A->>C: brain check
  end
  A->>C: brain turn <type> "summary"
  A->>G: commit (+ push)
  A-->>U: answer + "Brain: …" line
```

### 6.8 The seven links as data flows

Links I1–I7 are done by people or agents by hand; the CLI does not check them yet.

| Code | From → to | Trigger | Data produced | Automatic check |
| --- | --- | --- | --- | --- |
| I1 | action → knowledge | A milestone, a large task or a project is finished | A lesson as a permanent note, linking back to the project | KN-01 (has a link) |
| I2 | knowledge → action | A note suggests something to do | A Someday item linking to the note | No |
| I3 | action → files | A multi-step project is created | An index line, a category folder, a repository, a board | No (F10) |
| I4 | knowledge → action | A card forgotten 3 times | A next action "reread <source>" | No |
| I5 | files → knowledge | A run produces new numbers | A literature note whose source is the log's AC.ID | No |
| I6 | files → action | An issue assigned to you, or a bug blocking the project | A next action pointing at the issue number | No |
| I7 | knowledge → action | A recheck finds a claim wrong | A task to fix the note, the card, the map node | No |

### 6.9 `brain assign`

| Item | Specification |
| --- | --- |
| Syntax | <code>brain assign &lt;match&gt; &lt;suggest&#124;auto&#124;full&gt;</code> |
| Who runs it | Only the owner. The plugin has no tool for it; the hook stops an AI from adding a label (section 5.4) |
| Steps | 1. The level must be in `[assistant] levels`. 2. Collapse the whitespace of `match`. 3. Find the `- [ ]` lines in Next Actions containing `match` (case-insensitive). 4. Not exactly 1 line → stderr `Need exactly 1 open next action containing '…', found n.`, code 2. 5. The line already has a label → stderr, code 2. 6. Append ` · @javis:<level> · assigned <today>` and write the file |
| Writes | `10-Action/11-next-actions.md` |
| Output | `Assigned to Javis (<level>): <line>` |
| Exit code | 0; 2 not exactly 1 match, already assigned, or unknown level |

### 6.10 `brain assigned`

| Item | Specification |
| --- | --- |
| Syntax | <code>brain assigned [--level suggest&#124;auto&#124;full]</code> |
| Reads | Next Actions |
| Output | Each open task with a valid label whose level is at most `--level`: `<n> · <level> · <line>`. Nothing: `Nothing is assigned to Javis…` |
| Exit code | 0; 2 unknown level |

`<n>` is the position in the filtered list, counting from 1. A label without a level is not listed; `brain check` reports it as error AS-01.

### 6.11 `brain report`

| Item | Specification |
| --- | --- |
| Syntax | <code>brain report &lt;n&gt; &lt;result…&gt; [--level …]</code> |
| Steps | 1. Empty result → code 2. 2. Build the list as `brain assigned --level` does; a number outside it → code 2. 3. Change `- [ ]` to `- [x]` and append ` · done <today>`. 4. Append to the Inbox `(javis) Result "<task>": <result>`, where `<task>` is the line without the label and dates, and `javis` is `[assistant] result_channel` |
| Writes | Next Actions, Inbox |
| Output | `Done: <task>. The result is in the Inbox for clarifying.` |
| Exit code | 0; 2 bad number, missing result or unknown level |

Javis's results enter the Inbox without G1 but go no further than Fleeting when clarified, like a chat export. Facts Javis looked up must already have been submitted separately with `brain submit`.

### 6.12 The assistant loop

```mermaid
sequenceDiagram
  actor U as Owner
  participant J as Javis (auto loop)
  participant P as Plugin + hook
  participant C as brain CLI
  participant N as Next Actions
  participant I as Inbox
  U->>J: "capture: ask the accountant…" (Telegram)
  J->>P: brain_capture(channel=telegram)
  P->>C: brain capture … --channel telegram
  C->>I: (telegram) line
  U->>N: clarify into a next action
  U->>C: brain assign "accountant" auto
  C->>N: … · @javis:auto · assigned <date>
  J->>P: brain_assigned(max_level=auto)
  P->>C: brain assigned --level auto
  C-->>J: 1 · auto · …
  J->>J: do the work: drafts, research
  opt facts it looked up
    J->>P: brain_submit(record=…)
    P->>C: brain submit <temp file>
  end
  J->>P: javis_edit_file(Next Actions, add @javis:full)
  P-->>J: blocked: only the owner assigns
  J->>P: brain_report(number=1, result, max_level=auto)
  P->>C: brain report 1 "…" --level auto
  C->>N: - [x] … · done <date>
  C->>I: (javis) Result "…": …
  U->>I: clarify the result like any other item
```

The level on the label is the task's ceiling, and it has the same names as the three Javis OS permission modes, so each loop runs at one level and calls `brain_assigned` with `max_level` set to that level.

| Level | Javis may | Never, at any level |
| --- | --- | --- |
| `suggest` | Read the vault, research, submit through G1, propose, report | Assign or raise tasks, write permanent notes, delete data, skip G1, close or stop projects |
| `auto` | Also: write drafts, code in the 50–59 area, issues on the board | |
| `full` | Also: send messages, post, order, exactly as the task says | |

| Tool | Runs | `min_mode` |
| --- | --- | --- |
| `brain_capture` | `brain capture --channel` | `safe` |
| `brain_turn` | `brain turn` | `safe` |
| `brain_submit(record, name)` or `brain_submit(file)` | `brain submit` | `readonly`: the record is written to a temporary folder outside the vault; the only write to the brain is the CLI's, after G1 |
| `brain_check`, `brain_weekly` | `brain check`, `brain weekly` | `readonly` |
| `brain_assigned(max_level)` | `brain assigned --level` | `readonly` |
| `brain_report(number, result, max_level)` | `brain report --level` | `readonly`: the only write is the CLI's own bookkeeping |

### 6.13 `brain migrate`

| Item | Specification |
| --- | --- |
| Syntax | `brain migrate [--dry-run]` |
| Needs | Only `brain.toml` at the root; it does not open the brain with the 4.0 configuration first, because the old tables would not merge |
| Steps | 1. `brain.toml`: if it has a 3.0 table (`bo_nao`, `kiem_duyet`, `javis`…), rewrite it with the 4.0 tables and keys (`CONFIG_TABLES`) and the current version. 2. Rename files and folders (`RENAMES`: `_mau` → `_templates`, `phieu-nguon.md` → `source-record.md`, `Coding/50 He thong` → `Code/50 System`, `_log/k1.md` → `_log/rejected.md`; every `_mau-*.md` → `_template-*.md`), then remove folders left empty. 3. For every note: rename frontmatter keys (`FIELDS`) and the values `the` → `card`, `chua-kiem` → `unverified`, including commented-out keys in templates. 4. Convert line formats only in their own files (`LINE_RULES`): `giao`/`xong` dates in Next Actions; channels, result lines, reach names and the heading in the Inbox; turn types in the turn log; rejected lines in the rejected log. `Coding/` paths become `Code/` in every note |
| Leaves alone | The body text of notes, beyond the rules above; anything already converted. Running it again prints `Nothing to migrate` |
| Output | `Would change (n):` with `--dry-run`, else `Changed (n):`, one line per change, then a reminder to run `brain check` and commit |
| Exit code | 0; 1 no `brain.toml` |

## 7. Deployment view

```mermaid
flowchart LR
  subgraph PC["The owner's machine"]
    PY["Python 3.11+"] --- CLI2["brain CLI"]
    CLI2 --- VA["vault/ (git clone)"]
    ED["Editor: Obsidian, VS Code…"] --- VA
    AGT["Agents: Claude Code, Codex…"] --- CLI2
    JOS2["Javis OS<br/>brain-standard plugin"] --- CLI2
  end
  TG2["Telegram, voice"] --> JOS2
  VA -- "push / pull" --> GH["Private git remote"]
  GH --> CL["Cloud agent<br/>temporary clone"]
  GH --> M2["Second machine"]
```

### 7.1 Deployment nodes

| Node | Role | Needs |
| --- | --- | --- |
| Personal machine | Main place of work | Python 3.11+, git; no network to run the CLI |
| Private git remote | Backup, sync, history | One private repository |
| Second machine | Working elsewhere | Pull before working, push when done |
| Cloud agent | Works on a temporary clone | Must commit and push before the session ends |
| Javis OS | Captures from channels, runs follow-up loops | A laptop, mini PC or VPS with a checkout of the repository; Python 3.12 for Javis; background work on an API key |
| Docker (optional) | Runs the CLI where Python 3.11+ is missing | Docker; the image `dfat243/brain_standard` holds only `tools/brain/`, the brain is mounted at `/brain` at run time |

### 7.2 Install and upgrade

1. Create a private repository from the Brain_Standard package and clone it.
2. Run `bin/brain --version`; it must print `brain 4.0.1`. There is no build or install step. Without Python, run the image from the brain's folder instead: `docker run --rm -v "$PWD:/brain" dfat243/brain_standard --version`.
3. Copy `vault/AGENTS.md` to the root under the name your tool reads.
4. Upgrade: pull the new `tools/`, `bin/`, `docs/` and `integrations/`, and read the CHANGELOG. New parameters arrive with `tools/brain/defaults.toml`, so `brain.toml` only changes when you want to override something. Details: [getting-started.md](getting-started.md), section 11.
5. From 3.0 (or 2.2) to 4.0: after pulling, run `brain migrate --dry-run`, then `brain migrate`, `brain check`, review the diff and commit. Copy `vault/AGENTS.md` and the templates from the standard again if you want them in English. See [migration.md](migration.md).

### 7.3 Backup and restore

| Situation | What to do |
| --- | --- |
| Lost machine | Clone again from the remote |
| A mistaken edit, or an agent broke something | `git log`, `git restore` or `git revert` |
| Broken remote | Every clone is a full copy |
| A migration you don't want | `git restore .` before committing, or `git revert` the migration commit |
| Broken retrieval index **(proposed)** | Delete `.brain/`, run `brain index --rebuild` |
| Javis did something wrong | Disable the plugin on the Javis Plugins page; `git revert` Javis's commits |

### 7.4 Deploying Javis OS

A summary of [using-with-javis-os.md](using-with-javis-os.md), which has every step:

1. Install Javis OS; background work on an API key.
2. Point the brain at the repository root (the folder with `brain.toml`), not `vault/`; don't press "normalise structure".
3. Add Javis's logs and caches and `drafts/` to `.gitignore`.
4. Self-learning: Dry run or Suggest; Wiki, Skills and Curator off; no INGEST.
5. Paste the shared rule block into a Javis project's instructions; copy `AGENTS.md` and `CLAUDE.md` to the root.
6. Copy `integrations/javis/brain-standard/` to `plugins/`, read it, enable it.
7. Declare the `claude_write_guard.py` hook in `.claude/settings.json`.
8. Create the "Javis · suggest" loop; add "Javis · auto" after 2 stable weeks; switch "Javis · full" on only when there is work for it.

## 8. Cross-cutting concepts

### 8.1 Data model

Each note is a Markdown file. Frontmatter is optional and sits at the top of the file between two `---` lines. The "Check" column points to the rule codes in section 8.4.

**Source record** (items an agent brings in, template [`vault/_templates/source-record.md`](../vault/_templates/source-record.md)):

| Key | Type | Required | Meaning | Check |
| --- | --- | --- | --- | --- |
| `source` | URL or description | Yes | The page that was read | G1-01 |
| `original_source` | URL | No | The original document, if different | |
| `author` | String | No | | |
| `published` | Date | No | | |
| `retrieved` | Date | Yes | The day the agent fetched it | G1-01 |
| `valid_until` | Date or month | No | After this the fact needs rechecking | VD-01 |
| `archived` | URL | Yes | An archived copy, for example Wayback | G1-01 |
| `hash` | `sha256:…` | No | Fingerprint of the content | |
| `grade` | `[A-F][1-6]` | Yes | Admiralty grade | G1-01, G1-02, G1-03 |
| `verification` | String | Yes | How it was checked | G1-01 |
| `max_reach` | `card`, `literature`, `fleeting` | Added by the CLI | How far it may go | |
| `submitted` | Date | Added by the CLI | | |
| `label` | `unverified` | Added by the CLI for fleeting | | |

**Literature** (template `30-Knowledge/literature/_template-literature.md`): `type: literature`, `source`, `location`, `read_on`; with agent facts also `grade` and `archived`. G2 applies only when `grade` is present.

**Permanent** (template `30-Knowledge/permanent/_template-permanent.md`):

| Key | Required | Meaning | Check |
| --- | --- | --- | --- |
| `id` | Should | `YYYYMMDDHHMM`; also used as the date | KN-02 |
| `type` | Should | `permanent` | |
| `source` | Should | Link to the literature note | |
| `links` | One of the two | A list of links; or `[[…]]` links in the body | KN-01 |
| `cards` | No | Number of flashcards made from it | |
| `grade` | When it rests on agent facts | Credibility must be 1–2 | G3-01, G3-02 |

**Project** (template `10-Action/13-Projects/_template-project.md`):

| Key | Required | Meaning | Check |
| --- | --- | --- | --- |
| `type` | Should | `project` | |
| `status` | Yes | One of `[project] statuses`: `someday`, `active`, `done`, `stopped` | AC-01 |
| `started` | Should | Creation date | |
| `outcome`, `done_when`, `stop_when` | Yes when active (`[project] required_when_active`) | | AC-02 |
| `code` | No | Johnny Decimal category | |
| `repo`, `board`, `milestone` | No | The execution layer | EX-01, EX-02 |
| `due` | No | Project deadline | EX-03 |
| `people` | No | People involved (read as a string, R1) | |
| `stop_reason` | Should when stopped | | AC-03 |

**Next action assigned to Javis**: no frontmatter; the label is on the line, grammar in section 8.2. `@javis` without a valid level is error AS-01.

**Fleeting**: no required frontmatter; `date` recommended. **Area**: `type: area`, `standard`, `project_this_quarter`. **MOC**: `type: moc`, the body is a list of links.

### 8.2 Line grammar

The list-shaped files have a fixed line syntax so the CLI can count them.

```text
date         = YYYY "-" MM "-" DD
time         = HH ":" MM
stamp        = "- [" date [" " time] "]"

inbox_line   = stamp " (" channel ") " text
agent_line   = stamp " (agent) " title " · " grade " · up to " reach_name " → agent/" file_name
rejected_line = stamp " rejected · " grade " · " file_name " · " source
turn_line    = stamp " " turn_type " · " summary
task_line    = "- [" (" " | "x") "] " verb " …" [" · @" context] [" · ~" minutes "'"] [" · [[" project "]]"] [" · #" issue] [assignment]
assignment   = " · " label ":" level " · assigned " date [" · done " date]
result_line  = stamp " (" result_channel ") Result \"" task "\": " result
jdex_line    = "- " AC.ID " " name " · location: " path [" · project: [[…]]"] [" · repo: …"] [" · board: …"] " · status: " status

channel      = "hand" | "voice" | "telegram" | "mcp" | "export" | "javis" | …
label        = "@javis"                        ([assistant] label)
level        = "suggest" | "auto" | "full"     ([assistant] levels)
turn_type    = "task" | "idea" | "file" | "drop"   ([turn] types)
reach_name   = "flashcard" | "literature" | "fleeting (unverified)"   ([gates.reach_names])
result_channel = "javis"                       ([assistant] result_channel)
```

`notes.DATED_LINE_RE` (`^- \[(\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))?\]`) is shared by the Inbox, `rejected.md` and `turns.md` to read dates. A done task is `- [x]`. Internal links look like `[[note-name]]` (`notes.LINK_RE`).

### 8.3 Trust model and gates

A two-character grade from the Admiralty system: source A–F (A completely reliable … E unreliable, F cannot be judged) and credibility 1–6 (1 confirmed … 5 improbable, 6 cannot be judged). The two axes are graded independently.

`gates.reach(grade, gates)`, with thresholds from `[gates]`:

```text
if grade does not match ^[sources][credibility]$        → malformed
source, credibility = grade[0], int(grade[1:])
if source ∈ reject_sources or credibility ∈ reject_credibility → reject       (default E, 5)
if source ∈ fleeting_only_sources                       → fleeting           (default D, F)
if source ∈ literature_sources and credibility ∈ card_credibility → card      (default A–C, 1–2)
otherwise                                               → literature
```

Result with the defaults (rows are sources, columns credibility):

| | 1 | 2 | 3 | 4 | 5 | 6 |
| --- | --- | --- | --- | --- | --- | --- |
| A, B, C | card | card | literature | literature | reject | literature |
| D, F | fleeting | fleeting | fleeting | fleeting | reject | fleeting |
| E | reject | reject | reject | reject | reject | reject |

| Gate | Where | Applied by | Default condition |
| --- | --- | --- | --- |
| G1 | Before the Inbox | `brain submit`, `brain check` | All 5 fields; a well-formed grade; not rejected |
| G2 | Door to literature | `brain check` (when `grade` is present) | Source A–C, has `archived` |
| G3 | Door to permanent | `brain check` (when `grade` is present) | Credibility 1–2 |
| G4 | Door to the flashcard deck | The owner | Credibility 1–2; numbers carry a `valid_until` |

A chat export skips G1 on import (`brain capture --channel export`) but is treated as F6: unverified, no further than Fleeting. A fact from an export that should go to literature or beyond needs a source record and G1. The CLI does not check this yet, because the Inbox does not keep an item's channel once it moves into a lane (R3).

### 8.4 Rule catalogue

Every rule has a code that docs, tests, CLI messages and (later) the retrieval index refer to. Since 4.0 every `brain check` message starts with its code.

| Code | Level | Applies to | Condition | Message (shortened) | Configuration |
| --- | --- | --- | --- | --- | --- |
| G1-01 | Error | `inbox_agent` | A required field is missing or empty | `G1-01 · <f>: agent item is missing …` | `gates.required_fields` |
| G1-02 | Error | `inbox_agent` | Malformed grade | `G1-02 · <f>: grade '…' is malformed` | `gates.sources`, `gates.credibility` |
| G1-03 | Error | `inbox_agent` | The grade should have been rejected | `G1-03 · <f>: grade … should have been rejected but is in the Inbox` | `gates.reject_*` |
| G2-01 | Error | literature with `grade` | Malformed grade | `G2-01 · <f>: grade '…' is malformed` | |
| G2-02 | Error | literature with `grade` | Source outside `literature_sources` | `G2-02 · <f>: literature needs source A–C, has …` | `gates.literature_sources` |
| G2-03 | Error | literature with `grade` | No `archived` | `G2-03 · <f>: no archived copy (archived)` | |
| KN-01 | Error | permanent | No `[[…]]` in the body nor in a `[notes] link_keys` key | `KN-01 · <f>: permanent note links to no other note` | `notes.link_keys` |
| G3-01 | Error | permanent with `grade` | Malformed grade | `G3-01 · <f>: grade '…' is malformed` | |
| G3-02 | Error | permanent with `grade` | Credibility outside `permanent_credibility` | `G3-02 · <f>: permanent needs credibility 1–2, has …` | `gates.permanent_credibility` |
| KN-02 | Warning | permanent | No `id` | `KN-02 · <f>: permanent note has no id` | |
| KN-03 | Warning | fleeting | Age > `fleeting_max_days` | `KN-03 · <f>: fleeting note is n days old; …` | `clarify.fleeting_max_days` |
| VD-01 | Warning | literature, permanent, inbox_agent | Past `valid_until` | `VD-01 · <f>: past its valid_until date (…)` | |
| AC-01 | Error | project | `status` missing or not in `[project] statuses`; other project rules are skipped | `AC-01 · <f>: status must be one of …` | `project.statuses` |
| AC-02 | Error | active project | Missing `outcome`, `done_when` or `stop_when` (one error per field) | `AC-02 · <f>: missing …; set it when the project is created` | `project.required_when_active` |
| EX-01 | Warning | active project | Has a `milestone`, no `board` | `EX-01 · <f>: has a milestone but no board` | `execution.warn_milestone_without_board` |
| EX-02 | Warning | active project | No `board`, and Next Actions has no `[[<file name>]]` | `EX-02 · <f>: active project has no task in Next Actions or on a board` | `execution.warn_project_without_task` |
| EX-03 | Warning | active project | Past `due` | `EX-03 · <f>: past its due date …` | |
| AC-03 | Warning | stopped project | No `stop_reason` | `AC-03 · <f>: stopped project should record a stop_reason` | |
| AS-01 | Error | open labelled next action | No level, or a level outside `[assistant] levels` | `AS-01 · next action line n: @javis needs a level (…)` | `assistant.label`, `assistant.levels` |
| AS-02 | Warning | open labelled next action | `assigned` older than `stale_after_days` | `AS-02 · next action line n: assigned n days ago …` | `assistant.stale_after_days` |

Notes: G2 and G3 apply only when a note has a `grade`, because literature and permanent notes the owner writes from sources they read themselves don't go through the gates. The limits on projects and next actions were removed in 2.2.0. The 3.0 codes map to these as K1→G1, K2→G2, K3→G3, TT→KN, KD→VD, HD→AC, TH→EX, JV→AS ([glossary.md](glossary.md)).

### 8.5 Configuration reference

`tools/brain/defaults.toml` holds every parameter with a comment. `config.merge` merges `brain.toml` over it recursively: a key in `brain.toml` wins, tables are merged key by key, and tables the defaults don't know are kept. A typical `brain.toml` only has `[brain]`.

| Key | Type | Default | Used by |
| --- | --- | --- | --- |
| `brain.version` | String | `"4.0.1"` | `brain --version`, `migrate` |
| `brain.vault` | Path | `"vault"` | Every command |
| `paths.*` | Paths, relative to the vault | the standard layout (section 5.2) | Every command |
| `files.template_prefix` | String | `"_"` | Every check, the guard |
| `files.inbox_header`, `turn_log_header`, `rejected_log_header` | String | `# Inbox…`, `# Turns`, `# G1 · rejected items` | When a file is created |
| `files.weekly_title` | String with `{week}` | `# Weekly Review · {week}` | `weekly --save` |
| `capture.default_channel` | String | `"hand"` | `capture` |
| `clarify.fleeting_max_days` | Integer | 7 | KN-03, `weekly` |
| `clarify.moc_min_notes` | Integer | 7 | Not used; guidance for people |
| `rhythm.daily_pick_max` | Integer | 3 | Not used; guidance for people and AI |
| `turn.types` | List | `task`, `idea`, `file`, `drop` | `turn`, `weekly` |
| `project.statuses`, `active_status`, `done_status`, `stopped_status` | Strings | `someday`, `active`, `done`, `stopped` | AC-01, `weekly` |
| `project.required_when_active` | List | `outcome`, `done_when`, `stop_when` | AC-02 |
| `notes.date_keys` | List | `date`, `read_on`, `retrieved`, `started` | `note_date` |
| `notes.link_keys` | List | `links` | KN-01 |
| `gates.strict` | Boolean | `true` | `submit` (missing fields), `turn` (vault errors) |
| `gates.required_fields` | List | 5 fields | `submit`, G1-01, `weekly` |
| `gates.sources`, `gates.credibility` | String, list | `"ABCDEF"`, 1–6 | `grade_pattern` |
| `gates.reject_sources`, `reject_credibility` | Lists | `["E"]`, `[5]` | `reach` |
| `gates.fleeting_only_sources` | List | `["D", "F"]` | `reach` |
| `gates.literature_sources` | List | `["A", "B", "C"]` | `reach`, G2-02 |
| `gates.permanent_credibility` | List | `[1, 2]` | G3-02 |
| `gates.card_credibility` | List | `[1, 2]` | `reach` |
| `gates.unverified_label` | String | `"unverified"` | `submit` |
| `gates.reach_names.*` | Strings | `flashcard`, `literature`, `fleeting (unverified)` | Inbox lines, `submit` output |
| `execution.warn_milestone_without_board` | Boolean | `true` | EX-01 |
| `execution.warn_project_without_task` | Boolean | `true` | EX-02 |
| `johnny_decimal.area`, `max_categories` | String, integer | `"50-59"`, 10 | Not used yet (F10) |
| `assistant.name` | String | `"Javis"` | Messages, help |
| `assistant.label` | String | `"@javis"` | `assign`, `assigned`, `report`, AS-01, the guard |
| `assistant.levels` | List, lowest first | `suggest`, `auto`, `full` | `assign`, `assigned --level`, AS-01, the plugin |
| `assistant.stale_after_days` | Integer | 7 | AS-02, `weekly` |
| `assistant.result_channel` | String | `"javis"` | `report` |
| `assistant.plugin.timeout_seconds` | Integer | 60 | The plugin |
| `assistant.plugin.default_channel` | String | `"javis"` | `brain_capture` |
| `assistant.guard.protected` | List of `[paths]` keys | `permanent`, `inbox_agent` | The guard |
| `assistant.guard.label_file` | `[paths]` key | `next_actions` | The guard |
| `assistant.guard.write_tools` | List | Javis and Claude Code write tools | The guard |

### 8.6 Finding the brain's root

In order: the `--root` argument, then `BRAIN_ROOT`, then walking up from the current folder until a folder holds `brain.toml`. Not found: `No brain.toml found. Run inside a brain folder or pass --root.` (code 1). The vault is `<root>/<brain.vault>`.

### 8.7 Time and note dates

- `config.now()` returns local time without a time zone, without microseconds; if `BRAIN_NOW` (ISO 8601) is set, it uses that.
- `notes.note_date(p, fm, date_keys)` takes a note's date from the first key in `[notes] date_keys` present in the frontmatter (first 10 characters); then the first 8 digits of `id` or of the file name as `YYYYMMDD`; finally the file's modification time.
- `notes.expires_on(value)`: `YYYY-MM-DD` expires the next day; `YYYY-MM` expires on the 1st of the next month. Anything else, or an invalid date, returns `None`, meaning no expiry (R10).
- A fleeting note's age is the days between today and its date; the warning fires when it is greater than the threshold, so with 7 the warning starts on day 8.

### 8.8 Safe writes

| Operation | Where | How |
| --- | --- | --- |
| Append | `Inbox.md`, `_log/rejected.md`, `_log/turns.md` | Open in `a` mode, create the folder and header if missing |
| Create | `00-Inbox/agent/<time>-<slug>.md` | The name has the time to the second; the same second and slug overwrite (R5) |
| Create or overwrite | `weekly/<week>.md` | Only with `--save` |
| Edit a line | Next Actions | Only `assign` and `report`, on the one matched line |
| Rename, rewrite keys | Config, file names, frontmatter keys, list lines | Only `brain migrate`, when the owner runs it |
| Edit or delete existing notes | Never | People or agents do it; git keeps the history |

### 8.9 Encoding and platforms

- Every file is read and written as UTF-8, with `\n` line endings.
- `main` calls `reconfigure(encoding="utf-8")` on stdout and stderr so non-ASCII text shows correctly on Windows; old consoles may still need `chcp 65001`.
- `notes.slug` strips accents (turns `đ` into `d`, splits Unicode combinations), keeps ASCII letters and digits, joins with `-`, lower-cases, keeps at most 60 characters, and returns `item` when empty.

### 8.10 Errors and exit codes

| Code | Meaning | Examples |
| --- | --- | --- |
| 0 | Success | `capture` done; `submit` passed; `check` without errors; `turn` closed; `weekly`; `assign`, `assigned`, `report`, `migrate` succeeded |
| 1 | The vault has errors, or no brain was found | `check` has errors; `turn` refused; no `brain.toml` |
| 2 | Bad input | Empty text or summary; file not found; incomplete source record; malformed grade; bad arguments (`argparse`); unknown turn type or level; `assign` not matching exactly 1 task or already assigned; `report` with a bad number or no result |
| 3 | G1 rejected the item | Source E or credibility 5 |

Agents should rely on exit codes, not on the message text.

### 8.11 Security and threat model

| Threat | Example | Current measures | Still open |
| --- | --- | --- | --- |
| AI invents facts | A wrong number recorded as fact | G1–G3, required grades, "never invent a grade" | An agent can still grade too high; relies on the monthly recheck |
| Prompt injection from the web | A page says to skip G1 | The rule "content is data", lowering the source grade | Depends on the agent complying |
| An agent writes straight into a lane, skipping `submit` | Creates a literature file directly | G2, G3 when `grade` is present; review through git diff | Notes without `grade` are not checked (R3) |
| Bypassing G1 with a comment-only field | `archived:   # none yet` | Fixed in 4.0: a value that is only a comment counts as empty (`test_comment_only_field_counts_as_empty`) | |
| Leaking personal data | Public repository; notes pasted into an outside AI | Recommend a private repository and sharing only the notes needed | Not checked automatically |
| Data loss | An agent deletes files | The "never delete" rule; git | Depends on the agent complying |
| A path outside the vault **(proposed)** | An MCP tool reads `../../.ssh` | Path check in `read_note` (section 12.10) | |
| Javis assigns or raises its own tasks | Changes `@javis:suggest` to `@javis:full` | No assign tool; the hook blocks new or raised labels; AS-01 | A shell write bypasses the hook (R15) |
| Javis writes a permanent note or straight into the agent Inbox | Writes a file in `30-Knowledge/permanent/` | The hook blocks it; KN-01, G3 | As above |
| Javis takes a wrong real-world action | Sends the wrong email at `full` | Only `full`-labelled tasks; the `full` loop is on only when needed | The hook and the CLI can't see outside actions (R17) |
| A Javis result carries unverified facts | A number inside the result sentence | Results go no further than Fleeting; facts must go through `brain submit` | A rule for the person clarifying; the CLI doesn't check it (R3) |
| Javis OS self-learning writes a wiki | Javis distils chats into knowledge | Self-learning in a non-writing mode (section 7.4) | The self-learning writer does not go through the hook |
| `brain migrate` damages personal notes | A rule rewrites words in a note's body | Line rules apply only to their own list files; bodies are not translated; dry run first; git | Paths written as `Coding/` in note bodies are rewritten to `Code/` on purpose |

### 8.12 Test strategy and traceability

Run: `python3 -m unittest discover -s tests`. Each test copies `brain.toml`, `vault/` (and, for the plugin, `tools/`) to a temporary folder, sets `BRAIN_NOW=2026-10-20T21:30:00`, calls `brain.cli.main(["--root", tmp, …])`, and checks the exit code, the output and the files produced. The migrate tests start from `tests/fixtures/brain-3.0/`, a 3.0 brain kept in its original Vietnamese names on purpose.

CI (`.github/workflows/ci.yml`) runs the suite on every push to `main` and every pull request, on Linux and Windows with Python 3.11 and the newest 3.x; it also runs `brain check` through both wrappers and builds the Docker image, checking `--version`, `check` on the template brain, and that the image holds nothing but `tools/`. The release workflow (`release.yml`) runs CI again before publishing a `vX.Y.Z` tag. Both run only in the Brain_Standard repository.

| Test | Rule · requirement |
| --- | --- |
| `test_template_vault_is_clean` | The template vault has no errors or warnings |
| `test_capture_to_inbox` | F1, `inbox_line` |
| `test_config_override_beats_default`, `test_turn_type_from_config`, `test_assistant_name_and_label_from_config` | F19 |
| `test_missing_brain_toml` | 8.6, code 1 |
| `test_submit_without_full_record_is_returned` | F2, code 2, no file created |
| `test_comment_only_field_counts_as_empty` | R9 fixed |
| `test_malformed_grade` | `malformed`, code 2 |
| `test_rejected_grades_go_to_log` | F4, E1 and B5 rejected, code 3, `rejected_line` |
| `test_reach_and_inbox_line` | F3, table 8.3, `max_reach`, `label`, `agent_line` |
| `test_check_catches_agent_item_without_record` | G1-01 |
| `test_g2_literature` | G2-02, G2-03 |
| `test_g3_and_permanent_links` | KN-01, G3-02 |
| `test_old_fleeting_warns` | KN-03, `note_date` |
| `test_valid_until` | `expires_on`, VD-01 |
| `test_active_project_missing_criteria` | AC-02 |
| `test_milestone_without_board_warns` | EX-01, EX-02 |
| `test_no_limits` | ADR-06, `measure` |
| `test_turn_refused_while_errors` | F6, refusal on errors |
| `test_turn_log` | F6, `turn_line` |
| `test_weekly` | F7, `weekly --save` |
| `test_assign_adds_label_and_date`, `test_assign_needs_exactly_one_match` | F13, `assignment` |
| `test_assigned_filters_by_level` | F14 |
| `test_report_checks_off_and_writes_inbox` | F15, `result_line` |
| `test_check_assignment_rules` | F16, AS-01, AS-02 |
| `test_weekly_counts_assignments` | F17 |
| `tests/test_javis_plugin.py` (24 runs) | F18: tools run the right CLI command, `min_mode`, `brain_submit` from record text, the guard blocks permanent notes, agent items, templates and labels, guard paths from configuration; the Claude Code hook |
| `tests/test_migrate.py` (6) | F20: dry run changes nothing; config, files, frontmatter and lines converted; lines only in their own files; the migrated brain works; idempotent |

No tests yet for: G1-02 and G1-03 inside `check`; G2-01; G3-01; KN-02; AC-01; AC-03; EX-03; `strict = false`; finding the root through `BRAIN_ROOT`.

### 8.13 Versions and compatibility

- The version lives in `brain.version` in `tools/brain/defaults.toml` (what `brain --version` prints) and in the CHANGELOG; a brain's `brain.toml` may record the version it was created or migrated with.
- A z release never changes the data format. A y release may add frontmatter or configuration keys but keeps old keys working. An x release may change the shape of the flow or the names, and ships with a migration.
- New configuration keys always get a default in `defaults.toml`, so an older `brain.toml` keeps working.
- 3.0 raised x because the flow changed shape: Javis holds both ends. 2.2 data needed no conversion.
- 4.0 raises x because every name changes: commands, keys, codes, files. The flow is the same. 3.0 data is converted once by `brain migrate`; there are no Vietnamese aliases.

## 9. Architecture decisions

Each ADR records the context, the decision, the options considered and the consequences. Status: **Accepted**, **Proposed**, **Superseded by …**.

### ADR-01 · Markdown + git is the only source of truth

- **Status:** Accepted (2.0.0).
- **Context:** Personal data must live for decades, across many tools and many AIs.
- **Decision:** All data is Markdown files in a git repository. No database is a source of truth.
- **Options considered:** Notion or a cloud notes app (vendor lock-in); SQLite as the source (hard to read by hand, hard to diff).
- **Consequences:** Diffs and undo through git; opens in any editor. Complex queries and search by meaning need a separate index (ADR-08).

### ADR-02 · A single-file CLI, standard library only

- **Status:** Superseded by ADR-13 (4.0.0). Accepted in 2.0.0; the CLI existed from 2.2.0.
- **Context:** A personal user, many kinds of machine, including agents in temporary containers.
- **Decision:** One file, `tools/brain.py`, Python 3.11+, no outside libraries.
- **Options considered:** A pip package with dependencies (PyYAML, Click); Go or Rust for a ready-to-run binary.
- **Consequences:** Installed with one clone. A hand-written, limited frontmatter reader (R1). Heavy extensions such as embeddings must be optional. By 3.0 the file mixed every concern, and the plugin and the hook had to load the whole CLI to reuse one rule.

### ADR-03 · One Inbox, two questions, three lanes, seven links

- **Status:** Accepted (2.0.0; I7 added in 2.1.0).
- **Context:** Version 1.0 had two Inboxes synced by hand and one clarifying question; things slipped through.
- **Decision:** One single way in; the questions "Is it actionable?" then "Is it worth keeping?"; each item goes to exactly one lane; lanes exchange items through named links.
- **Consequences:** Everything has exactly one place. Changing the shape of the flow raises x.

### ADR-04 · Gate G1 blocks hard; two-axis Admiralty grades

- **Status:** Accepted (2.1.0).
- **Context:** AI is often confidently wrong; a wrong fact that reaches a flashcard gets memorised.
- **Decision:** Facts an agent brings in need a source record; source and credibility are graded separately; the grade decides how far the item goes; thresholds live in configuration.
- **Options considered:** A single 0–100 trust score (hard to explain); no checks (fast, but dirty data).
- **Consequences:** Agents take an extra step. Quality depends on honest grading; offset by the monthly recheck and I7.

### ADR-05 · One rule set for every AI

- **Status:** Accepted (2.2.1).
- **Context:** The owner uses several AIs; each tool reads an instruction file under a different name.
- **Decision:** The rules are written once in `vault/AGENTS.md` and the shared rule block, and copied under each tool's name.
- **Consequences:** No platform-specific features. The copies must be kept in sync by hand.

### ADR-06 · No quantity limits; measure instead

- **Status:** Accepted (2.2.0), replacing 2.0.0's limits of 3 projects, 1 next action per project and 20 next actions.
- **Context:** The limits blocked even capture, pushing the owner to write things down outside the system.
- **Decision:** Never block on quantity; `brain weekly` measures so the owner can see.
- **Consequences:** Nothing forces the load down; that relies on the Weekly Review.

### ADR-07 · Multi-step projects execute on a board outside the vault

- **Status:** Accepted (2.2.0).
- **Context:** Backlog, owners and deadlines are a board's strength; duplicating them in the vault is costly and drifts.
- **Decision:** The vault keeps the coordination (outcome, criteria, decisions, lessons); the board keeps the execution.
- **Consequences:** The brain only links, with no two-way sync. Collaborators never need the vault.

### ADR-08 · The retrieval index is derived data in SQLite

- **Status:** Proposed (4.1).
- **Context:** As the vault grows, notes can't be found by meaning; an AI only knows what is pasted into it.
- **Decision:** An index at `.brain/index.db` (SQLite, FTS5, sqlite-vec), never committed, always rebuildable; accessed through `brain search` and `brain mcp`.
- **Options considered:** A separate vector database such as Chroma or Qdrant (another server); a cloud service such as Pinecone (data leaves the machine); grep only (no search by meaning).
- **Consequences:** Optional dependencies. The index must be kept in step with the vault. Details in section 12.

### ADR-09 · Vietnamese names without diacritics

- **Status:** Superseded by ADR-14 (4.0.0). Accepted in 2.0.0.
- **Context:** The main user is Vietnamese; names with diacritics break easily in terminals and file systems.
- **Decision:** Commands, functions, configuration and frontmatter keys in Vietnamese without diacritics; content and messages with diacritics.
- **Consequences:** Easy for Vietnamese users; anyone else needed the glossary. It also kept the standard from being shared more widely.

### ADR-10 · Javis at both ends, the owner in the middle

- **Status:** Accepted (3.0.0).
- **Context:** Capture and follow-up are the most laborious parts and AI does them well; clarifying is where the owner decides which knowledge becomes theirs. Agents such as Javis OS distil wikis and create tasks on their own by default.
- **Decision:** Javis captures into the Inbox and follows up on assigned tasks; the owner clarifies. Javis's results return to the Inbox.
- **Options considered:** Javis clarifies on its own (fast, but bypasses the owner's decision and G1); no AI doing work for the owner (stay manual).
- **Consequences:** Nothing enters a lane without passing through a person. The Inbox gets result lines; the Weekly Review measures assignments.

### ADR-11 · Assign with a label on the line; only the owner adds it

- **Status:** Accepted (3.0.0).
- **Context:** We need a place that says which tasks an AI may do and how far, readable by eye and by machine.
- **Decision:** A `@javis:<suggest|auto|full>` label with the assignment date on the next action line itself; only `brain assign` adds it; the plugin has no assign tool; a hook blocks an AI from adding or raising a label.
- **Options considered:** A separate "Assigned to Javis" section (moving lines back and forth, losing the project link); two levels, yes or no (can't separate drafting from really sending); trusting the prompt (not a real barrier).
- **Consequences:** The three levels share the Javis OS permission-mode names, so a loop's mode is a natural ceiling. `brain report` uses the position in the filtered list (R14).

### ADR-12 · The CLI's bookkeeping tools run read-only

- **Status:** Accepted (3.0.0).
- **Context:** A Javis loop at `suggest` may not write files, so it could neither write a source record nor report; facts it found would then be squeezed into the result sentence, bypassing G1.
- **Decision:** `brain_submit` takes the record as text, writes it to a temporary folder outside the vault and runs the CLI; `brain_submit` and `brain_report` declare `min_mode: readonly`. The only write to the brain is the CLI's, after G1 or when marking done.
- **Options considered:** Keep `safe` and document `suggest` as read-only (research would need `auto`); let `suggest` write files in `drafts/` (widens the lowest level's write rights).
- **Consequences:** `suggest` keeps its meaning: read, research, submit through G1, propose, report. The plugin must keep its promise to write nothing else at that level.

### ADR-13 · A package of single-purpose modules, defaults in a TOML file

- **Status:** Accepted (4.0.0). Supersedes ADR-02.
- **Context:** The single file had grown to mix configuration, parsing, gates, checks, metrics, the assistant loop and argument parsing. The Javis plugin and the Claude Code hook needed one rule, the write guard, and had to import the whole CLI. Paths, thresholds, labels, levels, turn types and fixed message parts were constants scattered through the code.
- **Decision:** `tools/brain/` becomes a package of modules with one job each (`config`, `notes`, `gates`, `intake`, `checks`, `metrics`, `assistant`, `guard`, `migrate`, `cli`), run with `python -m brain`. Every parameter lives in `tools/brain/defaults.toml`; a brain's `brain.toml` overrides only what it changes; `config.merge` merges them recursively. Commands validate against the merged configuration, not lists fixed in the parser. The plugin and the hook import `brain.guard` from the repository they serve.
- **Options considered:** Keep one file and move constants to the top (still not reusable piecemeal); a pip-installable package (an install step, against Q3); configuration in Python (not editable by non-programmers).
- **Consequences:** Still standard library only and still no install step (`bin/brain` sets `PYTHONPATH`). A rule changes in one module and reaches the CLI, the plugin and the hook together. New parameters reach existing brains with `tools/`. A long-running Javis process serving several brains must load each repository's own package (`brain_package`).

### ADR-14 · English names, chosen for meaning

- **Status:** Accepted (4.0.0). Supersedes ADR-09.
- **Context:** Vietnamese names without diacritics are hard to read for anyone outside Vietnam, and even for Vietnamese readers they lose meaning (`ma`, `the`, `han` are ambiguous without accents). The owner wants the standard reusable and shareable.
- **Decision:** Commands, modules, functions, configuration keys, frontmatter keys, rule codes, file and folder names, messages and docs are in English. Names describe what a thing does rather than translating the old word: `nop` → `submit`, `k1_toi_da` → `max_reach`, `chan_cung` → `strict`, `javis` → `assigned`, `xong` → `report`. One language only, no translation layer. Old data is converted once by `brain migrate`; there are no Vietnamese aliases. The full mapping is in [glossary.md](glossary.md).
- **Options considered:** Aliases for both languages (twice the surface to test and document, ambiguous docs); an i18n layer for messages (more code than value for one user); keep Vietnamese (blocks sharing).
- **Consequences:** A breaking change, hence 4.0. Personal notes keep whatever language their owner writes in; only the structure is English. The archived 2.2.1 snapshot and the 3.0 test fixture keep their Vietnamese names on purpose.

## 10. Quality requirements

### 10.1 Quality tree

```mermaid
flowchart LR
  QL["Quality"] --> Q1["Q1 Durability"]
  QL --> Q2["Q2 Integrity"]
  QL --> Q3["Q3 Simplicity"]
  QL --> Q4["Q4 AI neutrality"]
  QL --> Q5["Q5 Verifiability"]
  Q1 --> S1["S1, S2, S14"]
  Q2 --> S3["S3, S4, S5, S11, S12"]
  Q3 --> S6["S6, S15"]
  Q4 --> S7["S7, S13"]
  Q5 --> S8["S8"]
```

### 10.2 Scenarios

| Code | Goal | Stimulus | Desired response | Measured by | Status |
| --- | --- | --- | --- | --- | --- |
| S1 | Q1 | Remove the CLI from the machine | The vault still reads and edits in any editor | Manual | Met |
| S2 | Q1 | An agent deletes a note by mistake | Restored with git within 1 minute | Manual | Met |
| S3 | Q2 | An agent submits an item without `archived` | Returned, code 2, no file in the Inbox | Test | Met |
| S4 | Q2 | An agent submits an E2 item | Logged in `_log/rejected.md`, code 3 | Test | Met |
| S5 | Q2 | A permanent note without a link | `turn` refuses to close | Test | Met |
| S6 | Q3 | A new machine with only Python 3.11 | `bin/brain --version` runs at once | Manual | Met |
| S7 | Q4 | Switching from Claude Code to Gemini CLI | Only copy `AGENTS.md` to `GEMINI.md` | Manual | Met |
| S8 | Q5 | Run the tests on two different days | Same results | `BRAIN_NOW` | Met |
| S9 | Performance | A 5,000-note vault | `brain check` under 2 seconds | No benchmark yet | Not measured |
| S10 | Portability | Running on Windows | Non-ASCII text shows correctly | Manual | Met with a UTF-8 console |
| S11 | Q2 | Javis edits Next Actions to give itself `@javis:full` | Refused by the hook, with the reason | Test, and with the real Javis OS 0.270.0 plugin loader (3.0) | Met |
| S12 | Q2 | A `suggest` loop finds a number | Submitted through G1 with `brain_submit` without writing a file, then reported | Test, and with real Javis OS (3.0) | Met |
| S13 | Q4 | Switching the Javis engine from Claude Code to an API engine | Still all 7 tools, same rules | The plugin serves every engine | Met by design, not yet run for real |
| S14 | Q1 | Upgrading a 3.0 brain | `brain migrate` converts it; `brain check` passes; personal note bodies unchanged | `tests/test_migrate.py` | Met |
| S15 | Q3 | Changing a threshold, a label or a path | One line in `brain.toml`, no code change | `test_config_override_beats_default` and the other F19 tests | Met |

## 11. Risks and technical debt

| # | Item | Impact | Likelihood | Response |
| --- | --- | --- | --- | --- |
| R1 | The frontmatter reader only understands one-line `key: value`; lists such as `people: [you]` are strings; multi-line values are dropped | Medium | High when editing in Obsidian | Keep the one-line convention in templates; consider a checked YAML subset |
| R2 | `check` and `measure` read some files more than once | Low on small vaults | Medium | Read each file once and share it; add the S9 benchmark |
| R3 | G4, Johnny Decimal, Waiting For, Someday, MOCs and I1–I7 are not checked; G2–G3 skip notes without `grade` | Medium | High | Add them to `check` gradually, as warnings |
| R4 | Appends don't lock the file; two processes writing at once can interleave lines | Low | Low | Add a file lock if agents run in parallel |
| R5 | Two `submit` runs in the same second with the same slug: the second overwrites the first | Low | Low | Add a suffix when the name exists |
| R6 | Times have no time zone; machines in different zones can disagree on the date | Low | Low | Add `brain.time_zone` if needed |
| R7 | **Fixed in 4.0.1.** No CI ran the tests on push in Brain_Standard | | | `.github/workflows/ci.yml` (section 8.12) |
| R8 | Notes can't be found by meaning; an AI only knows the notes pasted into it | High on large vaults | High | The retrieval layer, section 12 |
| R9 | **Fixed in 4.0.** A comment-only field such as `archived:   # none yet` was read as the value `"# none yet"` and counted as filled, so the item slipped through G1 | | | `notes._value` returns empty for a comment; `test_comment_only_field_counts_as_empty` |
| R10 | A mistyped `valid_until` or `due` is ignored silently | Low | Medium | Warn when a value is present but unreadable |
| R11 | `strict` covers both `submit` and `turn` | Low | Low | Split it into two flags if someone needs it |
| R12 | Frontmatter opened with `---` but never closed makes the whole file count as having no frontmatter, so every key-based rule skips it | Medium | Low | Report an error for unclosed frontmatter |
| R13 | A brain's recorded version is not compared with the CLI's; an old vault runs with a new CLI unnoticed | Low | Medium | `brain check` could warn when x or y differ, pointing to `brain migrate` |
| R14 | `brain report <n>` points at the wrong task if Next Actions changes between listing and reporting | Low | Low | `report` prints the task, the result goes to the Inbox, git can undo; stable task ids in 4.1 (the second-brain repository already has `n…` ids) |
| R15 | The hook only sees tools that go through the MCP Hub and Claude Code's file tools; shell writes bypass it; Javis OS hooks fail open on errors | Medium | Low | `brain check`, git review; give a shell only to engines that need it |
| R16 | Javis OS changes its plugin contract (`register_tool`, `pre_tool_call`) | Medium | Medium | The plugin is small and tested; retest with the real loader when upgrading Javis |
| R17 | Javis takes a wrong real-world action at `full` | High | Low | Only `full`-labelled tasks; approved content; the `full` loop off when idle |
| R18 | `brain migrate` misses a 3.0 name that a brain used outside the standard layout (custom `[paths]`, hand-made formats) | Low | Medium | Dry run first; `brain check` after; names are listed in the glossary for manual fixes |
| R19 | Vault templates in an existing brain keep their Vietnamese body text after migrating; only keys and file names change | Low | High | Copy the English templates and `AGENTS.md` from the standard after migrating ([migration.md](migration.md)) |

### 11.1 Open decisions

1. **The main channel** for talking to Javis. Proposed: Telegram.
2. **The model** for background work. Proposed: an API key for reasoning and writing; a local model for cheap work.
3. **Whether Cá Béo's brain** gets its own Javis. Proposed: its own, same plugin, separate repository.
4. **Javis clarifying obvious items** (read-later links, tasks under 2 minutes). Proposed: not in 4.0; review after 4 weeks of data.
5. **Stable task ids** instead of positions (R14). Proposed: 4.1.
6. **The paused agent infrastructure** (35 personas, Vault). Proposed: replace it with Javis, one tool-calling agent, one permission level per loop.

## 12. Future work · retrieval layer (proposed 4.1)

Status: **proposed**, not in the code. It adds a mechanism without changing the flow, so it is version 4.1.0 (this design was numbered 2.3 before 3.0, and 3.1 before 4.0).

### 12.1 Goals and non-goals

Goals:

- T1. Find notes by keyword, typed with or without diacritics.
- T2. Find notes by meaning, including Vietnamese text.
- T3. Let any MCP client read the brain without pasting notes.
- T4. Results respect the trust rules: show which items are unverified or out of date.
- T5. Writes from MCP go through gate G1.

Non-goals:

- Replacing Markdown as the source of truth.
- Letting AI edit, delete or write permanent notes over MCP.
- Requiring extra installs: when off, the CLI behaves exactly as in 4.0.
- Answering questions with an LLM inside the CLI in 4.1; the MCP client generates answers.

### 12.2 Requirements

| Code | Requirement | Phase |
| --- | --- | --- |
| R-T1 | `brain index` indexes changed files, based on a content hash | 1 |
| R-T2 | `brain index --rebuild` drops and rebuilds the whole index | 1 |
| R-T3 | `brain search` returns results with path, heading, excerpt, lane, grade and label | 1 |
| R-T4 | `brain turn` re-indexes what changed when the layer is on; index errors never block closing a turn | 1 |
| R-T5 | Combined keyword and vector search | 2 |
| R-T6 | Changing the embedding model rebuilds the vectors automatically | 2 |
| R-T7 | `brain mcp` offers the 6 tools in section 12.9 | 3 |
| R-T8 | Read tools never leave `vault/`; write tools call `intake.capture` and `intake.submit` | 3 |

### 12.3 Principles

1. **A derived index:** it lives at `.brain/index.db`; `.brain/` goes into `.gitignore`.
2. **Local by default:** embeddings are computed on the machine; an API is used only when switched on explicitly in `brain.toml`.
3. **Writes go through the gates:** MCP has no write path of its own.
4. **Optional dependencies:** phase 1 uses only the standard library (`sqlite3` ships with FTS5 in most Python builds); phases 2–3 install more when needed.
5. **Degrade gracefully:** without the vector library, `brain search` still works with FTS5 and says so.

### 12.4 Components

```mermaid
flowchart TB
  V2["vault/*.md"] --> SC["Scan files<br/>skip _log, 90-Archive, _*.md"]
  SC --> HS{"hash changed?"}
  HS -- "no" --> SKIP["skip"]
  HS -- "yes" --> CH["Split into chunks by heading"]
  CH --> FTS["Write chunk + chunk_fts"]
  CH --> EM["Embedding model<br/>(phase 2)"]
  EM --> VEC["Write chunk_vec"]
  FTS --> DB[(".brain/index.db")]
  VEC --> DB
  DB --> TK["brain search<br/>BM25 + vector → RRF → trust weights"]
  TK --> MCP["brain mcp<br/>stdio"]
  MCP --> CL2["MCP client"]
  MCP -- "capture, submit" --> CORE["intake.capture · intake.submit<br/>G1 as before"]
  TURN["brain turn"] -- "re-index changes" --> SC
```

| Component | Proposed technology | Why |
| --- | --- | --- |
| Index storage | SQLite through the standard `sqlite3` | One file, no server |
| Keyword search | FTS5, tokenizer `unicode61 remove_diacritics 2`, ranking with `bm25()` | Finds accented words typed without accents; needed for codes like `51.03` and names |
| Search by meaning | The `sqlite-vec` extension, a `vec0` table | Same file as FTS5, runs on every OS |
| Embeddings | A local multilingual model through `fastembed` (ONNX, no PyTorch); optionally an API | Understands Vietnamese; data stays on the machine |
| Merging results | Reciprocal Rank Fusion | No weights to tune between two different score scales |
| MCP server | The Python `mcp` SDK, `FastMCP`, stdio transport | Works with any MCP client |

The model is chosen in phase 2 after measuring on real Vietnamese notes (open question Q-1). Candidates: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions, light) and `intfloat/multilingual-e5-large` (1024 dimensions, more accurate, heavier). The e5 family needs the prefix `query: ` for questions and `passage: ` for passages.

### 12.5 Index schema

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE meta (
  key    TEXT PRIMARY KEY,   -- schema_version, model, dimensions, last_indexed
  value  TEXT NOT NULL
);

CREATE TABLE file (
  id           INTEGER PRIMARY KEY,
  path         TEXT NOT NULL UNIQUE,   -- relative to the vault, posix form
  hash         TEXT NOT NULL,          -- sha256 of the content
  mtime        REAL NOT NULL,
  lane         TEXT NOT NULL,          -- inbox | agent | action | fleeting | literature | permanent | moc | area | file | weekly | other
  type         TEXT,                   -- frontmatter type
  title        TEXT,
  grade        TEXT,                   -- Admiralty grade, if any
  label        TEXT,                   -- for example unverified
  valid_until  TEXT,
  expired      INTEGER NOT NULL DEFAULT 0,  -- 1 if valid_until had passed when indexed
  date         TEXT                    -- from note_date
);

CREATE TABLE chunk (
  id          INTEGER PRIMARY KEY,
  file_id     INTEGER NOT NULL REFERENCES file(id) ON DELETE CASCADE,
  position    INTEGER NOT NULL,
  heading     TEXT,                    -- parent headings, for example "Rules › Measure every week"
  content     TEXT NOT NULL,
  first_line  INTEGER NOT NULL,
  last_line   INTEGER NOT NULL
);

CREATE VIRTUAL TABLE chunk_fts USING fts5(
  heading, content,
  content = 'chunk', content_rowid = 'id',
  tokenize = 'unicode61 remove_diacritics 2'
);

-- phase 2; dimensions come from meta.dimensions
CREATE VIRTUAL TABLE chunk_vec USING vec0(embedding float[384]);  -- rowid = chunk.id

CREATE TABLE link (
  source  INTEGER NOT NULL REFERENCES file(id) ON DELETE CASCADE,
  target  TEXT NOT NULL                -- the name inside [[…]], unresolved
);
CREATE INDEX link_target ON link(target);
```

`chunk_fts` is an external-content FTS5 table, so it must be kept in sync by hand: when deleting a chunk, insert a `'delete'` command into `chunk_fts` before deleting it from `chunk`. `chunk_vec` has no foreign key, so it is also deleted by hand by `rowid`.

Lanes come from the path, using the `[paths]` keys in configuration; `areas` is `area`; `code` is `file`; everything else is `other`.

### 12.6 Indexing algorithm

```text
index(brain, rebuild=False):
  open .brain/index.db, create the schema if missing
  if rebuild or meta.schema_version differs: drop everything, recreate
  if meta.model differs from the configured model: drop chunk_vec, mark for re-embedding
  seen = {}
  for each p in vault/**/*.md, except skip and _*.md files:
    h = sha256(content)
    seen.add(p)
    if file(p).hash == h and no re-embedding needed: continue
    in one transaction:
      delete p's old chunks (chunk_fts, chunk_vec, chunk, link)
      fm, body = frontmatter(content)
      write file(p) with lane, type, title, grade, label, valid_until, expired, date
      for each chunk in split_chunks(body): write chunk, chunk_fts
      write links from LINK_RE on the body and the link_keys
      if vectors are on: embed the chunks in batches, write chunk_vec
  remove from the index every file not in seen
  write meta.last_indexed
```

`split_chunks(body)`:

1. Split on headings `#`…`######`; each part carries its parent headings.
2. A part longer than `chunk_words` words is cut at blank lines, then at sentences, with about 15% overlap.
3. A part shorter than about 20 words is merged with the next part under the same parent.
4. Code blocks longer than 200 lines are left out of the vectors (kept in FTS5).
5. Record the first and last line for citations.

### 12.7 Query and ranking

```mermaid
sequenceDiagram
  participant Q as brain search / search tool
  participant F as chunk_fts
  participant V as chunk_vec
  participant M as model
  Q->>Q: filter lanes, skip Archive unless asked
  Q->>F: MATCH the cleaned query, bm25, take 50
  opt vectors on
    Q->>M: embed("query: " + question)
    Q->>V: KNN 50
  end
  Q->>Q: RRF + trust weights → top k
  Q-->>Q: return chunk, path, lines, lane, grade, label
```

1. **Clean the FTS5 query:** split into words, wrap each in double quotes and join with spaces, so FTS5's special characters (`*`, `:`, `NEAR`, `-`) never become syntax.
2. **Merge:** `rrf_score(d) = Σ 1 / (60 + rank_i(d))` over the lists that contain `d`.
3. **Trust weights:** `score = rrf_score × w_lane × w_trust`.

| Lane | `w_lane` |
| --- | --- |
| permanent | 1.00 |
| moc | 0.95 |
| literature | 0.90 |
| action, area | 0.85 |
| file, weekly, other | 0.75 |
| fleeting | 0.65 |
| inbox, agent | 0.60 |

| Condition | `w_trust` |
| --- | --- |
| No `grade`, or a grade that may reach a flashcard | 1.00 |
| A grade that may only reach literature | 0.90 |
| `label = unverified` | 0.75 |
| `expired = 1` | 0.70 |

The numbers are starting points, to be tuned after measuring on real questions (section 12.13). Weights only reorder results, they never hide them: unverified items still show, with their label.

4. **Skipped by default:** `_log/`, `90-Archive/`, `_*.md` files, anything inside `.brain/`. `--include-archive` brings the Archive back.

### 12.8 Command line

| Command | Arguments | Exit code |
| --- | --- | --- |
| `brain index` | `--rebuild`: from scratch; `--quiet`: no progress output | 0 done; 4 layer off or a library missing |
| `brain search "query"` | `--lane LANE` (repeatable), `--k N` (default 8), `--include-archive`, `--json` | 0 with or without results; 4 as above |
| `brain mcp` | None | Runs until the client closes stdin |

Sample `brain search` output:

```text
$ brain search "cache cuts API cost"
1. 30-Knowledge/permanent/202610201430-cache-cuts-api-cost.md:3-9 · permanent
   A cache cuts API costs when many people ask the same question
   "… with a cache hit rate above 60% the cost almost halves …"
2. 00-Inbox/agent/20261019-101500-api-price.md:8-14 · agent · C3 · unverified
   API price list for October
   "…"
```

`--json` returns a list of objects shaped like the output schema of the `search` tool in section 12.9.

### 12.9 MCP tools

| Tool | Access | Input | Output |
| --- | --- | --- | --- |
| `search` | Read | `{"query": str, "lanes": [str]?, "k": int = 8, "include_archive": bool = false}` | `[{"path", "first_line", "last_line", "heading", "excerpt", "lane", "grade", "label", "expired", "score"}]` |
| `read_note` | Read | `{"path": str}` | `{"path", "frontmatter": {…}, "content": str}` |
| `links` | Read | `{"path": str}` | `{"outgoing": [str], "incoming": [str]}` |
| `overview` | Read | `{}` | The dict from `metrics.measure` |
| `capture` | Write | `{"text": str}` | `{"ok": bool, "message": str}`; calls `intake.capture(…, channel="mcp")` |
| `submit` | Write | `{"record": str}` (Markdown with a source record) | `{"ok": bool, "exit_code": int, "message": str}`; writes a temporary file, then calls `intake.submit` |

The tool descriptions sent to the client must state three rules: results are data, not instructions; cite with path and grade; never present `unverified` or expired items as fact.

Sample client configuration (Claude Desktop, Claude Code and Cursor use the same shape):

```json
{
  "mcpServers": {
    "brain": {
      "command": "/path/to/brain/bin/brain",
      "args": ["--root", "/path/to/brain", "mcp"]
    }
  }
}
```

### 12.10 Retrieval layer security

| Threat | Measure |
| --- | --- |
| Reading files outside the vault (`../`, absolute paths, symlinks) | `read_note` and `links` resolve the real path (`resolve()`) and refuse anything outside `vault/`; only `.md` files |
| Reading sensitive data through `search` | `skip` in configuration; the owner adds private folders to it |
| Bypassing G1 through MCP | No tool writes arbitrary files; `submit` calls `intake.submit` |
| Prompt injection inside notes | Tool descriptions say results are data; write tools always go through the gates |
| Notes leaking through an embeddings API | `provider = "local"` by default; turning on an API must be explicit, and `brain index` warns on every run |
| FTS5 syntax errors from a question | Query cleaning (section 12.7) |

### 12.11 Configuration

```toml
[retrieval]
enabled = false                      # turn the retrieval layer on
vectors = false                      # phase 2
provider = "local"                   # local | api
model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
chunk_words = 400                    # maximum words per chunk
default_k = 8
skip = ["_log", "90-Archive"]        # relative to the vault
index_on_turn = true
```

### 12.12 Performance budget

Measured on an ordinary personal machine with a vault of 1,000 notes, about 5,000 chunks.

| Operation | Budget |
| --- | --- |
| `brain index --rebuild`, FTS5 only | Under 5 seconds |
| `brain index`, under 10 files changed, FTS5 only | Under 1 second |
| `brain index --rebuild`, with vectors, small model, CPU | Under 3 minutes |
| `brain search`, FTS5 only | Under 200 ms |
| `brain search`, with vectors, model already loaded | Under 500 ms |
| Loading the model the first time in a process | A few seconds; `brain mcp` loads it once and keeps it |
| Size of `.brain/index.db` | Tens of MB |

### 12.13 Test plan

| Group | Cases |
| --- | --- |
| Index | New, edited, deleted and renamed files; skipping `_log`, Archive and templates; an unchanged hash writes nothing; `--rebuild` gives the same result |
| Chunking | Nested headings; long chunks cut with overlap; short chunks merged; correct line numbers |
| FTS5 | Typing without accents finds accented notes; the code `51.03`; special characters cause no error |
| Ranking | Permanent above fleeting at equal base score; `unverified` items still in the results, with their label |
| Vectors | Skipped when the library is missing; a model change re-embeds; synonyms without shared words are still found |
| MCP | `read_note("../brain.toml")` refused; `submit` without a record returns code 2 and creates no file; `capture` writes an `mcp` channel line |
| Quality | 30 real questions with their right notes; recall@8 and MRR for FTS5, vectors and combined |

### 12.14 Roadmap and acceptance criteria

| Phase | Content | Extra dependencies | Acceptance |
| --- | --- | --- | --- |
| 1 | `brain index`, `brain search` with FTS5 only; indexing on `turn`; `.brain/` in `.gitignore` | None | The Index, Chunking, FTS5 and Ranking tests pass; the FTS5 budget holds; the 4.0 tests still pass |
| 2 | Embeddings, sqlite-vec, RRF | `fastembed`, `sqlite-vec` (optional) | The Vectors tests pass; combined recall@8 beats FTS5 on the 30 questions |
| 3 | `brain mcp` with 6 tools; a guide in [using-with-ai.md](using-with-ai.md) | `mcp` (optional) | The MCP tests pass; works with at least two clients |

Each phase updates the CHANGELOG, this document (sections 1.2, 5, 8.5, 9, 12), and `AGENTS.md` if agents need to know the new commands. The retrieval code goes into its own module, `brain.retrieval`, and its parameters into a `[retrieval]` table in `defaults.toml`.

### 12.15 Open questions

| Code | Question | Needed to decide |
| --- | --- | --- |
| Q-1 | Which embedding model for Vietnamese? | Recall measured on the 30 questions |
| Q-2 | Index `Code/`, or only READMEs and the JDex index? | The real size of the 50–59 area |
| Q-3 | Is a `brain ask` command that calls an LLM directly needed? | Demand outside MCP clients |
| Q-4 | Should `brain mcp` be a separate package, so the core stays dependency-free? | Code size after phase 3 |

## 13. Glossary

The full list of terms, with their 3.0 names, is [glossary.md](glossary.md). The terms this document leans on:

| Term | Meaning |
| --- | --- |
| Vault | The `vault/` folder holding every note |
| Inbox | The one real place everything enters before it is clarified |
| Lane | One of three branches: action, knowledge, files and code |
| I1–I7 | The seven named links between lanes |
| G1–G4 | The four trust gates |
| Grade | Admiralty grade, two characters: source A–F, credibility 1–6, for example B2 |
| Reach | How far an item may go with its grade: flashcard, literature, fleeting |
| Source record | The required frontmatter of an item an agent brings in |
| Strict | `gates.strict = true`: G1 returns incomplete records, `turn` won't close while the vault has errors |
| Fleeting · literature · permanent | A passing thought · a summary of one source · a mature idea in your own words |
| MOC | Map of Content, a note that links a cluster of notes |
| AC.ID | A Johnny Decimal address, for example `51.03` |
| JDex | The Johnny Decimal index file, `50.00` |
| Board | Where a multi-step project executes: backlog, milestones, people |
| Turn | One session of work, closed with `brain turn` |
| Assistant loop | Javis captures, the owner clarifies, Javis follows up on assigned tasks |
| Label | The `@javis:<level>` mark on a next action saying Javis may do it |
| Level (`suggest`, `auto`, `full`) | The ceiling of an assignment: read and propose · also write drafts · also act outside |
| Loop | A recurring Javis job that runs at one level and takes tasks at or below it |
| DAB | This architecture design document |
| ADR | Architecture Decision Record |
| FTS5 | SQLite's full-text search |
| BM25 | A keyword ranking formula |
| Embedding | A vector of numbers representing a passage's meaning |
| RRF | Reciprocal Rank Fusion, a way to merge several ranked lists |
| RAG | Retrieve relevant passages, then give them to an AI to answer |
| MCP | Model Context Protocol, a protocol for AI to call tools and read data |

## 14. References

- arc42, architecture documentation template: <https://arc42.org/overview>
- ISO/IEC/IEEE 42010, architecture description: <https://www.iso.org/standard/74393.html>
- The C4 model: <https://c4model.com>
- Michael Nygard, Documenting Architecture Decisions: <https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>
- The Admiralty system: NATO STANAG 2511 · AJP-2.1
- Model Context Protocol: <https://modelcontextprotocol.io>
- Javis OS: <https://github.com/blogminhquy/javis-os> (version 0.270.0, checked 21/10/2026)
- SQLite FTS5: <https://sqlite.org/fts5.html> · sqlite-vec: <https://github.com/asg017/sqlite-vec>
- fastembed: <https://github.com/qdrant/fastembed>
- Cormack, Clarke, Büttcher (2009), Reciprocal Rank Fusion outperforms Condorcet and individual rank learning methods
- In this repository: [flow.md](flow.md), [lanes.md](lanes.md), [trust-gates.md](trust-gates.md), [execution-layer.md](execution-layer.md), [using-with-ai.md](using-with-ai.md), [using-with-javis-os.md](using-with-javis-os.md), [getting-started.md](getting-started.md), [migration.md](migration.md), [glossary.md](glossary.md)

## 15. Maintaining this document

| When | Update sections |
| --- | --- |
| A CLI command is added or changed | 1.2, 5.3, 6, 8.10, 8.12 |
| The Javis plugin, the hook or the levels change | 5.4, 6.12, 8.11, 9 (ADR-10–12), [using-with-javis-os.md](using-with-javis-os.md) |
| A check rule is added or changed | 8.4, 8.12, and the matching `docs/` page |
| A parameter is added | `tools/brain/defaults.toml` (with a comment), 8.5 |
| A frontmatter key or template is added | 8.1, 8.2, and `migrate.FIELDS` if it renames an old key |
| A name changes | [glossary.md](glossary.md), `brain migrate`, and an x release |
| A major decision | Add an ADR in section 9; never edit old ADRs; mark a replaced one "Superseded by …" |
| A risk is fixed | Mark it in section 11 with the release that fixed it |
| Every release | Section 0 (version, date, history) |

This document must match the code. When they differ, the code is the truth for current behaviour, and the document must be fixed in the same commit.
