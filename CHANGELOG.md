# Change log

Versions are x.y.z: x goes up when the main flow changes shape or a migration is needed, y when a mechanism is added without breaking the flow, z for fixes to numbers, labels and wording. The newest version is at the top. Entries before 4.0 use the names of their time; [docs/glossary.md](docs/glossary.md) maps them to the current ones.

## 4.0.1 · 29/10/2026

Packaging and automation. The brain package, the rules, the commands and the data format are the same as 4.0.0, so there is nothing to migrate.

### Added
- `Dockerfile` and `.dockerignore`: an image, `dfat243/brain_standard`, that runs the CLI without installing Python. It holds only `tools/brain/`; the brain is mounted at run time: `docker run --rm -v "$PWD:/brain" dfat243/brain_standard check`. The build context allow-lists `tools/`, so a vault, notes or keys can never end up in the image.
- `.github/workflows/ci.yml`: on every push to `main` and every pull request, the tests on Linux and Windows with Python 3.11 and the newest 3.x, `brain check` through `bin/brain` and `bin/brain.cmd`, and a build and smoke test of the image (`--version`, `check` on the template brain, nothing but `tools/` inside).
- `.github/workflows/release.yml`: on a `vX.Y.Z` tag, checks that the tag matches `brain.version` and has a CHANGELOG section, runs CI, publishes the image as `X.Y.Z`, `X.Y`, `latest` and `sha-<commit>` for linux/amd64 and linux/arm64, then creates the GitHub Release with the CHANGELOG section as its notes. Needs the repository secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`.
- Both workflows run only in the Brain_Standard repository, so a personal brain made from this package skips them.

### Changed
- `brain.version` is `4.0.1`. `tests/test_migrate.py` compares the migrated version with the CLI's version instead of a fixed string.
- README: running with Docker. `docs/architecture.md`: a Docker deployment node (7.1, 7.2), CI in the test strategy (8.12), R7 resolved. `docs/getting-started.md` and `docs/migration.md`: the version numbers.

### Fixed
- R7: no CI ran the tests on push.

## 4.0.0 · 22/10/2026

English and modular. The flow, the lanes, the gates and the assistant loop work exactly as in 3.0; every name changes, so this is a major version with a one-time migration. Version 3.0 is the last Vietnamese version and stays in git history.

### Added
- `brain migrate [--dry-run]`: converts a 3.0 brain once: `brain.toml` tables and keys, file and folder names, frontmatter keys and values, and the line formats of the list files. Personal note content is left alone. Safe to run again. See `docs/migration.md`.
- `tools/brain/defaults.toml`: every parameter with its default and a comment, including what used to be hardcoded: paths, file headers, the default channel, turn types, project statuses and required fields, date and link keys, grade alphabets, reach names, the assistant's name, label, levels and result channel, the plugin timeout, and the write guard's protected paths and tools. `brain.toml` now only lists what a brain changes; tables are merged key by key.
- Rule codes in every `brain check` message: G1-01…G3-02, KN-01…03, VD-01, AC-01…03, EX-01…03, AS-01…02.
- `docs/glossary.md`: every term, command, key, rule code and file, with its 3.0 name.
- `docs/migration.md`: the upgrade from 3.0.
- `tests/test_migrate.py` with a 3.0 fixture brain (`tests/fixtures/brain-3.0/`); tests for configuration overrides and the comment-only field fix. 58 tests in all.
- ADR-13 (a package of modules, defaults in TOML) and ADR-14 (English names, chosen for meaning) in the DAB.

### Changed
- Everything in English, named for meaning rather than translated word by word:
  - Commands: `ghi` → `capture` (`--kenh` → `--channel`), `nop` → `submit`, `kiem` → `check`, `giao` → `assign`, `javis` → `assigned` (`--muc` → `--level`), `xong` → `report`; `weekly --ghi` → `weekly --save`; turn types `viec`, `y`, `file`, `xoa` → `task`, `idea`, `file`, `drop`.
  - Gates K1–K4 → G1–G4; the `Bộ não:` footer → `Brain:`; chat prefixes `ghi:`, `hôm nay` → `capture:`, `today`.
  - Configuration tables: `[bo_nao]` → `[brain]`, `[duong_dan]` → `[paths]`, `[lam_ro]` → `[clarify]`, `[nhip]` → `[rhythm]`, `[kiem_duyet]` → `[gates]`, `[thuc_thi]` → `[execution]`, `[javis]` → `[assistant]`.
  - Frontmatter keys: `trang_thai` → `status`, `ket_qua` → `outcome`, `tieu_chi_xong` → `done_when`, `tieu_chi_dung` → `stop_when`, `nguon` → `source`, `ngay_lay` → `retrieved`, `luu_tru` → `archived`, `ma` → `grade`, `cach_kiem` → `verification`, `k1_toi_da` → `max_reach`, and the rest in the glossary.
  - Files: `_mau/phieu-nguon.md` → `_templates/source-record.md`, `_mau-*.md` → `_template-*.md`, `Coding/50 He thong` → `Code/50 System`, `_log/k1.md` → `_log/rejected.md`, `chan_ghi_claude.py` → `claude_write_guard.py`.
  - Docs: `huong-dan` → `getting-started`, `dong-chay` → `flow`, `ba-lan` → `lanes`, `kiem-duyet` → `trust-gates`, `tang-thuc-thi` → `execution-layer`, `dung-voi-ai` → `using-with-ai`, `dung-voi-javis` → `using-with-javis-os`, `kien-truc-he-thong` → `architecture` (DAB 4.0).
  - CLI messages, templates, `vault/AGENTS.md` and the shared rule block.
- `tools/brain.py` → the `tools/brain/` package, run with `python -m brain`: `config`, `notes`, `gates`, `intake`, `checks`, `metrics`, `assistant`, `guard`, `migrate`, `cli`. `bin/brain` and `bin/brain.cmd` set `PYTHONPATH` and run it; still no install step.
- Turn types and assistant levels are validated against the brain's configuration, so a brain can change them.
- Javis plugin 4.0.0: tools `brain_capture`, `brain_submit`, `brain_check`, `brain_turn`, `brain_weekly`, `brain_assigned`, `brain_report`. The hook and the Claude Code hook share `brain.guard` instead of a copy of the rule; the plugin loads each repository's own package, so one Javis process can serve several brains.
- The retrieval layer proposal moves from 3.1 to 4.1, with English table and command names (`brain search`, `--rebuild`).

### Fixed
- R9: a source-record field holding only a comment, such as `archived:   # none yet`, counted as filled and let the item through G1. It now counts as empty.

### Kept
- `archive/2.2.1/` and the test fixture stay in Vietnamese, as historical snapshots.
- No Vietnamese aliases and no translation layer: one language, English.

## 3.0.0 · 21/10/2026

The brain gets an operator. The flow changes shape: Javis holds both ends, **capturing** at the entry and **following up** at the exit; the brain, meaning you, **clarifies** in the middle. The three lanes, I1–I7, K1–K4 and the 2.2 execution layer stay as they were. Version 2.2.1 is snapshotted in `archive/2.2.1/`.

### Added
- The Javis loop in `docs/dong-chay.md`: capture → clarify → assign → follow up → result back to the Inbox.
- The `@javis:<suggest|auto|full>` label on a next action, with `giao YYYY-MM-DD`. The level on the label is the ceiling for what Javis may do.
- CLI: `brain giao "…" <level>` (owner only), `brain javis [--muc]`, `brain xong <n> "result"`. `brain xong` marks the task done and writes a `(javis) Kết quả …` line to the Inbox.
- `brain kiem`: an error when an `@javis` label has no level; a warning when an assigned task is older than `treo_toi_da_ngay` and not done.
- `brain weekly`: Javis tasks open, done in 7 days, and stale.
- A `[javis]` table in `brain.toml`: `nhan`, `treo_toi_da_ngay`.
- `docs/kien-truc-he-thong.md` raised to DAB 3.0, keeping the arc42 layout: requirements, use cases, building blocks, command specifications, deployment, grammar, check rules, configuration, exit codes, threats, tests and risks gained the Javis parts; ADR-10 to ADR-12. DAB 1.1 is kept at `archive/2.2.1/docs/kien-truc-he-thong.md`.
- `docs/kien-truc-he-thong.md` (DAB 1.1, before 3.0): an architecture document in arc42 form, 9 ADRs, 13 risks; a proposed retrieval layer design (SQLite FTS5 + sqlite-vec index, `brain index`, `brain tim`, `brain mcp`), now moved to 3.1.
- `docs/dung-voi-javis.md`: using the brain with Javis OS, with a concept map, the conflicts, step-by-step setup and sample workflows, including follow-up loops per level.
- `integrations/javis/brain-standard/` (plugin 3.0.0): tools `brain_ghi`, `brain_nop`, `brain_kiem`, `brain_turn`, `brain_weekly`, `brain_viec_javis`, `brain_xong` for every engine; a hook stopping the AI from writing permanent notes, `00-Inbox/agent` or templates, and from adding or raising `@javis` labels. `brain_nop` takes the record as text and runs at `suggest`, so a read-only loop can still submit facts through K1.
- `integrations/javis/chan_ghi_claude.py`: a PreToolUse hook for Claude Code with the same guard.
- `archive/`: snapshots of older versions.

### Changed
- `vault/AGENTS.md` and the shared rule block: added the Javis loop rule (rule 8).
- Entry points: your words sent through Javis still skip K1; facts Javis looks up go through K1; `brain xong` results go to the Inbox.
- Daily loop and Weekly Review: added steps to assign tasks and review assignments.
- Chat exports: skip K1 on import, but carry the unverified label and go no further than Fleeting, like grade F6; facts in them that should go further need a source record and K1. `docs/dong-chay.md` used to say exports went through K1, which contradicted how the second-brain core worked.

### Kept
- Permanent notes are written only by you. At every level, Javis never deletes data, skips K1, or closes or stops projects.

## 2.2.1 · 20/10/2026

Docs only. The rules and the CLI behave the same.

### Added
- A "What the brain is for" section in the README: the problems it solves, who it suits, when it doesn't, the principles.
- `docs/dung-voi-ai.md`: using the brain with AI on any platform, with three connection levels, the shared rule block, setup on Claude, ChatGPT, Gemini, local models and agents in the repository, and sample workflows with prompts.
- `docs/huong-dan.md`: a step-by-step guide for newcomers.

### Changed
- `docs/quy-uoc-claude.md` → `docs/dung-voi-ai.md`, rewritten for every platform.
- `vault/CLAUDE.md` → `vault/AGENTS.md`, rewritten for every agent. Copy it to the root as `AGENTS.md`, `CLAUDE.md` or `GEMINI.md` depending on the tool.

## 2.2.0 · 20/10/2026

The execution layer, and no more limits. The brain keeps the coordination; the execution of multi-step projects moves to a board in the repository. The main flow is unchanged.

### Added
- The execution layer: each multi-step project has a board (for example GitHub Projects) in its category's repository, holding the backlog, issues, milestones, deadlines and owners.
- Project files gain `repo`, `board`, `milestone`, `han`, `nguoi` and a `## Quyết định` section.
- The Weekly Review also measures active projects, issues opened and closed on boards, and late milestones. Measure only, never block.
- The `brain` CLI with the commands `ghi`, `nop`, `kiem`, `turn`, `weekly`.

### Changed
- I1: when a task or project is done → also every time a milestone is done.
- I3: open a category when a project gets its first file → open the category, repository and board as soon as a multi-step project is created.
- I6: every error in a log becomes a next action → ordinary bugs become issues on the board; only issues assigned to you, or bugs blocking the whole project, become next actions.
- Waiting For: everything waiting on someone else → only what waits outside a board.
- Files lane: one GitHub repository per category → a repository with a board.

### Removed
- At most 3 active projects, and the "Is there room?" step when creating a project.
- Exactly 1 next action per project.
- At most 20 next actions.
- The `[gioi_han]` table in `brain.toml` and the checks of these limits in `brain turn`.

### Kept
- The daily loop picks at most 3 tasks each morning. This is a rhythm, and never blocks capture.
- Fleeting notes kept at most 7 days; a MOC once a cluster has about 7 notes; at most 10 categories in the 50–59 area.

## 2.1.0 · 01/10/2026

Trust gates. Information an agent brings in must have a source and a trust grade before it becomes a note or a flashcard. The main flow is unchanged.

### Added
- The "agent research" entry point: every fact an agent brings in from the web, papers or APIs, including facts Claude captured on a "ghi:" message.
- Gate K1 before the Inbox, blocking hard: agent items need a source record. Without one they go back to the agent. Ideas you write yourself skip K1.
- Two-axis grading from the Admiralty system: source A–F, information 1–6. Source E or information 5 is rejected and logged to `_log`; source D or F goes no further than Fleeting.
- A 10-step research procedure for agents, based on SIFT and lateral reading.
- Gates K2 (literature needs source A–C and an archived copy), K3 (permanent needs credibility 1–2), K4 (flashcards need credibility 1–2, plus a valid-until date for numbers).
- A monthly recheck of 10 random claims in permanent notes and knowledge maps.
- Link I7 · correction: a wrong claim becomes a task to fix the note, the card or the map node.
- The Weekly Review also measures: % of items without a source record, claims refuted, dead links, items past their valid-until date.

### Changed
- Old trust labels became grades: `web` → B2, `solid` → C2, `verify` → C3.

### Paused
- Reviewing C3 cards until each is rechecked. Cards reaching credibility 1–2 continue; the others leave the deck, and wrong claims go through I7.

## 2.0.0 · 30/09/2026

Inbox → 2 questions → 3 lanes. The main flow changed shape, so this is a major version.

### Added
- The brain becomes code and a CLI in its own repository, holding both code and data.
- Every turn of work with Claude ends with `brain turn`.
- The second question, "Is it worth keeping?", and the Delete exit.
- A 30–45 minute daily loop: pick at most 3 tasks, do at least 1, review 15–20 cards, capture new ideas into the Inbox.
- Fleeting notes (kept at most 7 days), literature notes, and a MOC once a cluster has about 7 notes.
- Six links, I1–I6, between the three lanes.
- Done and stop conditions for every project; the Archive records why a project stopped.
- The message conventions "ghi:", "hôm nay", "weekly", and a "Bộ não:" line at the end of every Claude answer.
- Limits: at most 3 active projects, exactly 1 next action per project, at most 20 next actions (removed in 2.2.0).

### Changed
- Inbox: two places synced by hand → one real place; the cloud Inbox flows one way each week.
- Clarifying: one question, "Is it actionable?" → two questions.
- Areas spawn one project per quarter; Someday is reviewed every week.
- The export routine runs weekly and writes only when there is new data; machine state goes to `_log`.
- Johnny Decimal only for code and files, in the 50–59 area; note names carry no AC.ID.
- Weekly Review: 30 minutes, measuring cards reviewed, tasks done, new notes, and a system-to-content time ratio of 1:3.
- Resources.md became literature notes.

### Removed
- Claude's memory as an entry point, since it only draws from the chats.

### Paused
- The multi-persona agent infrastructure: to be reopened when a project needs real tools or permissions.

## 1.0.0 · 28/09/2026

The starting point. Six steps: entry points → capture → clarify → organise → distil and remember → create. One clarifying question, "Is it actionable?". Three lanes: action (GTD + PARA), knowledge (Zettelkasten + LYT + FSRS), files and code (Johnny Decimal). The Inbox in two places, synced by hand.
