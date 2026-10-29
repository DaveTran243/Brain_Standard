# Getting started with Brain 4.0

This guide is for someone opening the repository for the first time. Read it and follow "Your first day", and you will have a working brain on your machine in about 30 minutes. Using it with AI is in section 8. Terms are defined in [glossary.md](glossary.md).

## 1. What this brain is

A system for notes and work built on Markdown files in a git repository. Everything you think, read and do goes into one **Inbox**. Each Inbox item answers **two questions**, then goes into exactly one of **three lanes**:

| Lane | What it holds | Folder |
| --- | --- | --- |
| Action | Tasks, projects, things you are waiting on | `vault/10-Action/` |
| Knowledge | Notes, book summaries, your own ideas | `vault/30-Knowledge/`, `vault/40-Maps/` |
| Files and code | Scripts, logs, exported files, each with a fixed number | `vault/Code/` |

Information an AI or agent brings in needs a **source record** and a **grade** before it enters the brain. These checks are the trust gates G1–G4.

A small CLI called `brain` captures to the Inbox, submits agent items through the gates, checks the vault, closes each turn of work, and runs the assistant loop.

What problem the brain solves, who it suits and when it does not: see [What the brain is for](../README.md#what-the-brain-is-for) in the README.

## 2. What you need

- **Python 3.11 or newer.** Check with `python3 --version`, or `python --version` on Windows. No extra packages.
- **Git**, and a GitHub account or another git host, to keep the brain in a private repository.
- **A Markdown editor that understands `[[...]]` links**, such as Obsidian. Any editor works, but one that follows links makes moving between notes much faster.

## 3. Install

Your brain holds personal notes, so create a **private** repository from this standard; don't write into Brain_Standard itself.

macOS, Linux:

```sh
git clone https://github.com/DaveTran243/Brain_Standard.git my-brain
cd my-brain
rm -rf .git && git init -b main  # start your own history
git add -A && git commit -m "Start a brain from Brain_Standard 4.0"
```

Windows (PowerShell):

```powershell
git clone https://github.com/DaveTran243/Brain_Standard.git my-brain
cd my-brain
Remove-Item -Recurse -Force .git; git init -b main
git add -A; git commit -m "Start a brain from Brain_Standard 4.0"
```

Create an empty private repository on GitHub, then connect and push:

```sh
git remote add origin https://github.com/<you>/<private-repo>.git
git push -u origin main
```

Check that the CLI runs. `brain` works from anywhere inside the repository; it finds `brain.toml` at the root by itself.

```sh
bin/brain --version     # prints: brain 4.0.1
bin/brain check         # prints: Vault is clean.
```

On Windows use `bin\brain.cmd check`. The rest of this guide writes `brain` for short.

Open the `vault/` folder in your Markdown editor. Files whose names start with `_` are **templates**: copy them to use them, don't edit them directly. `brain check` skips them.

## 4. Your first day · about 30 minutes

### Step 1 · Empty your head into the Inbox (5 minutes)

Write down everything on your mind, one command each. Don't sort anything yet.

```sh
brain capture "Call Minh back about the contract"
brain capture "Read chapter 5 of Designing Data-Intensive Applications"
brain capture "Idea: use a cache to cut API costs"
brain capture "Build a website for the shop"
```

Each command adds a timestamped line to `vault/00-Inbox/Inbox.md`. You can also type straight into that file.

### Step 2 · Clarify each item with the two questions (10 minutes)

Take each Inbox line and ask:

**Question 1 · Is it actionable?**

| If | Put it in |
| --- | --- |
| It takes under 2 minutes | Do it now, then delete the line |
| One step finishes it | `10-Action/11-next-actions.md` |
| Several steps, within the next 3 months | A new project in `10-Action/13-Projects/` |
| Not now | `10-Action/14-someday.md` |
| You are waiting on someone | `10-Action/12-waiting-for.md` |

**Question 2 · Is it worth keeping?** (when question 1 is "no")

| If | Put it in |
| --- | --- |
| A passing thought | `30-Knowledge/fleeting/`, kept for at most 7 days |
| A summary of one source | `30-Knowledge/literature/` |
| A mature idea that stands on its own | `30-Knowledge/permanent/` |
| A file or code | `Code/`, under its Johnny Decimal number |
| No | Delete it |

Delete each line from the Inbox once it is handled. The goal is an empty Inbox.

A next action starts with a verb and fits in one sitting:

```markdown
- [ ] Call Minh back about the contract · @phone · ~10'
```

### Step 3 · Create your first project (5 minutes)

Copy `10-Action/13-Projects/_template-project.md` to a new file, for example `10-Action/13-Projects/shop-website.md`. Fill in the three required fields:

```yaml
status: active
outcome: "A shop website that takes orders online"
done_when: "10 real orders have come in through the website"
stop_when: "After 6 weeks there is still no home page"
```

If the project has only one or two steps, delete the `repo`, `board`, `milestone`, `due` and `people` lines, then add the first task to Next Actions with a link to the project:

```markdown
- [ ] Sketch the 3 main pages of the website · @computer · ~45' · [[shop-website]]
```

If the project has many steps, see section 7 to attach a board.

### Step 4 · Write a permanent note (5 minutes)

Copy `30-Knowledge/permanent/_template-permanent.md` to a new file. Set `id` to the time of writing as `YYYYMMDDHHMM`. The title is **a claim**, the body is in your own words, and it needs **at least one link** to another note:

```markdown
---
id: 202610201430
type: permanent
---

# A cache cuts API costs when many people ask the same question

If questions repeat often, storing the answer is cheaper than calling the API again. It is not worth it when questions almost never repeat.

Related: [[another-note]]
```

### Step 5 · Check and close the turn (2 minutes)

```sh
brain check
brain turn task "first Inbox clean-up, created the website project"
git add -A && git commit -m "First day" && git push
```

`brain check` reports an **error** when something breaks a rule, for example a permanent note with no link or a project missing its criteria. It reports a **warning** for things worth a second look, such as a fleeting note older than 7 days. Each message starts with a rule code, for example `KN-01`; the codes are listed in [glossary.md](glossary.md). `brain turn` records the turn in `_log/turns.md`, but it will not close a turn while the vault has errors.

The first argument of `turn` says what the turn mainly produced: `task`, `idea`, `file` or `drop`.

## 5. Every day · 30–45 minutes

1. Open Next Actions and pick **at most 3 tasks** for today.
2. Do **at least 1** of them.
3. Review 15–20 flashcards, if you use them (FSRS, for example in Anki).
4. Capture new ideas with `brain capture`.
5. Finish with `brain turn <type> "summary"`, then commit.

## 6. Every Sunday · a 30-minute Weekly Review

```sh
brain weekly --save
```

This prints a table of metrics and saves it to `vault/weekly/<year>-W<week>.md`. Then go through the checklist in `vault/weekly/_template-weekly.md`:

- Empty the Inbox. Move fleeting notes older than 7 days to literature, or delete them.
- Go over each project and board: which project has nothing in progress, which milestone is late.
- Go over Someday, Areas and Waiting For. Compare the index in `Code/` with the real folders.
- Write down the week's decisions.

There is no limit on projects or next actions. The numbers in the Weekly Review are there so you notice when you are carrying too much.

Once a month, pick 10 claims at random from your permanent notes and recheck them. If one is wrong, create a next action to fix it.

## 7. Multi-step projects · a board in the repository

Since 2.2, a multi-step project keeps its execution on a board. The brain keeps only the coordination.

1. Add a line to `Code/50 System/50.00 Index (JDex).md` **first**, for example `51 Shop website`.
2. Create the folder `Code/51 Shop website/` and a repository for the project's code.
3. Create a board, for example GitHub Projects, linked to that repository. Break down the first milestone.
4. Fill in the project file: `code: 51`, `repo`, `board`, `milestone`, `due`, `people`.
5. The backlog, issues, bugs and owners live on the board. Next Actions keeps only the tasks **you** do next, with their issue number:

```markdown
- [ ] Fix the cart bug · ~60' · [[shop-website]] · #12
```

6. After each milestone, write 1 lesson as a permanent note and put the next milestone in the project file.
7. When the project is done or stopped, set `status` to `done` or `stopped`. If stopped, add a `stop_reason`. Then move the file to `vault/90-Archive/`.

Details: [execution-layer.md](execution-layer.md).

## 8. Using it with AI

The brain works with any AI: Claude, ChatGPT, Gemini, local models and coding agents. [Using the brain with AI](using-with-ai.md) covers setup per platform, sample workflows and prompts. The short version:

1. **Paste the shared rule block** from [using-with-ai.md](using-with-ai.md#the-shared-rule-block) wherever your AI takes instructions: personal preferences, Project instructions, a Gem, or the system prompt.
2. **For agents working in the repository**, copy `vault/AGENTS.md` to the root. Codex, Cursor, GitHub Copilot and Claude Code read it; Gemini CLI needs one line of configuration.
3. From then on, every AI answer ends with a "Brain:" line saying which lane the item goes to. You can type:

| Type | The AI does |
| --- | --- |
| `capture: …` | Only captures it to the Inbox |
| `today` | Runs the daily loop |
| `weekly` | Runs the Weekly Review with metrics |

**When the AI brings in facts:** the agent writes a file with a source record following `vault/_templates/source-record.md`, then submits it through gate G1:

```sh
brain submit research-result.md
```

| Result | Meaning |
| --- | --- |
| `G1 passed` (exit code 0) | The item goes to `00-Inbox/agent/`, with a note of how far it may go |
| `G1 returned` (exit code 2) | A required field is missing or the grade is malformed; complete it and submit again |
| `G1 rejected` (exit code 3) | Source E or credibility 5; only logged to `_log/rejected.md` |

A grade is one letter for how reliable the source is (A best, F not yet judged) and one digit for how credible the information is (1 confirmed, 6 not yet judged). For example, an original document read first-hand is A1; a blog post not cross-checked is C3. The full table: [trust-gates.md](trust-gates.md).

Your own words, spoken or typed, don't go through this gate.

**Assigning tasks to Javis (since 3.0).** After clarifying, label the next actions that Javis or another agent may do for you:

```sh
brain assign "accountant" auto    # finds exactly 1 open task containing "accountant", adds @javis:auto · assigned <today>
brain assigned                    # lists assigned tasks
brain report 1 "drafted in drafts/email.md"   # the agent reports done; the result goes to the Inbox
```

`suggest` only reads and proposes, `auto` also writes drafts and code in the repository, `full` also acts outside. Agents never label tasks themselves. Details: [flow.md](flow.md#the-assistant-loop); setup with Javis OS: [using-with-javis-os.md](using-with-javis-os.md).

## 9. Configuration in `brain.toml`

Every parameter has a default in `tools/brain/defaults.toml`. Your `brain.toml` only lists what you change; keys you leave out keep their defaults.

| Key | Default | Change it when |
| --- | --- | --- |
| `clarify.fleeting_max_days` | 7 | You want to keep passing thoughts longer or shorter |
| `gates.strict` | `true` | Set `false` to make G1 and `brain turn` warn instead of block |
| `gates.required_fields` | 5 fields | You want different required fields in a source record |
| `paths.*` | the standard layout | You rename or move folders |
| `brain.vault` | `vault` | The vault lives in another folder |
| `assistant.name`, `assistant.label` | `Javis`, `@javis` | Your assistant has another name |
| `assistant.stale_after_days` | 7 | `brain check` warns about assigned tasks not done after this many days |
| `turn.types` | task, idea, file, drop | You want other turn types |

Thresholds such as 7 days or 7 notes for a MOC are only starting points. Adjust them after about 4 weeks of real use.

## 10. Common problems

| You see | What to do |
| --- | --- |
| `No brain.toml found` | Run the command inside the brain repository, or add `--root <path>`. |
| `ModuleNotFoundError: No module named 'tomllib'` | Python is older than 3.11. Install a newer version. |
| `Turn not closed: fix N error(s)` | Run `brain check`, fix each error it lists, then run `brain turn` again. |
| `KN-01 · …: permanent note links to no other note` | Add at least one `[[link]]` to the note. |
| `AC-02 · …: missing done_when` | An active project needs `outcome`, `done_when` and `stop_when`. |
| `AS-01 · …: @javis needs a level` | The label has no level. Change it to `@javis:<level>`, or remove the label and run `brain assign`. |
| Unicode characters look wrong on Windows | Use Windows Terminal, or run `chcp 65001` first. |

## 11. Updating to a new version

See [CHANGELOG.md](../CHANGELOG.md) for what each version changes. To pull the new `docs/`, `tools/` and `bin/` without touching your notes:

```sh
git remote add standard https://github.com/DaveTran243/Brain_Standard.git   # first time only
git fetch standard
git checkout standard/main -- docs tools bin tests CHANGELOG.md
```

Don't pull `vault/` or `brain.toml` this way: they would overwrite your data and settings. Because defaults live in `tools/brain/defaults.toml`, new settings reach you with `tools/` and your `brain.toml` rarely needs changes.

**Upgrading from 3.0 or earlier:** the 4.0 names are English. After pulling `tools/` and `bin/`, run `brain migrate --dry-run` to see what will change, then `brain migrate`, and copy `vault/AGENTS.md` to the root again. Details: [migration.md](migration.md).

## Further reading

- [flow.md](flow.md) · the Inbox, the two questions, the 7 links between lanes, the rhythm, the assistant loop
- [lanes.md](lanes.md) · rules, metrics and warning signs for each lane
- [trust-gates.md](trust-gates.md) · gates G1–G4, the grade table, the 10 research steps
- [execution-layer.md](execution-layer.md) · boards, milestones, owners
- [using-with-ai.md](using-with-ai.md) · using the brain with AI on any platform
- [glossary.md](glossary.md) · every term, and its 3.0 name
