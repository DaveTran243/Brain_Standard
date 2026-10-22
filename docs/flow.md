# The flow

Everything goes into one Inbox, through two questions, then into exactly one of three lanes. The lanes exchange items only through 7 named links; there are no shortcuts.

Since 3.0 an assistant (Javis) sits at both ends of the flow: it **captures** at the start and **follows up** at the end. The middle, the two questions and the choice of lane, stays yours. See [the assistant loop](#the-assistant-loop).

```text
assistant CAPTURES ──► Inbox ──► you CLARIFY ──► destination ──► assistant FOLLOWS UP ──► result back to Inbox
   (capture, submit)        (2 questions, 3 lanes)   (assign)        (assigned, report)
```

## What comes in

| Source | Through G1? |
| --- | --- |
| Your own words: handwritten, spoken, typed, the `capture:` command, including messages sent through the assistant | No |
| Agent research: web, papers, APIs, facts Claude or the assistant looked up | Yes, strictly |
| The result of a task the assistant finished (`brain report`) | No, but it goes no further than Fleeting; facts it looked up must have been submitted through G1 separately |
| A weekly chat export, only when there is new data | No on intake, but it is labelled unverified and goes no further than Fleeting |

A chat export mixes your words with the AI's answers, so the export as a whole gets no source record. It enters the Inbox with `brain capture --channel export` and is treated like grade F6: unverified, at most Fleeting. A fact in it that should reach literature, a permanent note or a flashcard needs its own source record and must be submitted through G1 with `brain submit`. Your own words copied from an export are still your words and skip G1.

Machine status and routines write to `_log`, never to the Inbox.

## The two clarifying questions

**Question 1 · Is it actionable?**

| Answer | Destination |
| --- | --- |
| Under 2 minutes | Do it now |
| One step | Next Actions |
| Several steps within the next 3 months | Project (with a board when it has several steps, see [the execution layer](execution-layer.md)) |
| Not now | Someday/Maybe |
| Waiting on someone outside any board | Waiting For |

**Question 2 · Is it worth keeping?** (when the answer to question 1 is no)

| Answer | Destination |
| --- | --- |
| A passing thought | Fleeting, kept for at most 7 days |
| A summary of one source | Literature note |
| A mature idea that stands on its own | Permanent note, with at least 1 link |
| A file or code | Files and code lane, area 50–59 |
| No | Delete |

## The three lanes

| Lane | Model | Core question | Stores |
| --- | --- | --- | --- |
| Action | GTD + PARA | What is the next concrete step? | Next Actions, Projects, Someday, Areas, Waiting For, Archive, boards |
| Knowledge | Zettelkasten + LYT + FSRS | Which idea I already have does this connect to? | Fleeting, literature, permanent, maps of content, flashcards |
| Files and code | Johnny Decimal | Which number does this live at? | Index 50.00, 5x.xx folders, repositories |

Rules of each lane: [lanes.md](lanes.md).

## The seven links

| Code | From → to | When | Carries |
| --- | --- | --- | --- |
| I1 | action → knowledge | A milestone, an important task or a project is finished | 1 lesson as a permanent note, linked back to the project |
| I2 | knowledge → action | A note suggests something you could do | 1 Someday item, linked back to the note |
| I3 | action → files | A multi-step project is created | A category in area 50–59, a repository and a board |
| I4 | knowledge → action | A card was forgotten 3 times or more | Next action "reread <source>" |
| I5 | files → knowledge | A run produces new figures | A literature note whose source is the log's AC.ID |
| I6 | files → action | An issue assigned to you, or an error that blocks the whole project | A next action pointing to the issue. Ordinary bugs stay on the board. |
| I7 | knowledge → action | A recheck finds a claim false | A task to fix the note, card or map node |

## The assistant loop

The assistant is an operator that runs on top of the brain, for example [Javis OS](using-with-javis-os.md). It has no knowledge memory of its own: everything it knows lives in the brain.

| Step | Who | Does | Command |
| --- | --- | --- | --- |
| 1 · Capture | Assistant | Receives from Telegram, voice, the web, email. Your words are copied verbatim; facts it looks up come with a source record | `brain capture`, `brain submit` |
| 2 · Clarify | You | Answer the two questions and pick a lane. The assistant may only suggest a destination | |
| 3 · Assign | You | Label the next actions the assistant may do, with a level | `brain assign "…" <level>` |
| 4 · Follow up | Assistant | Takes tasks whose level is no higher than the level of the current run, does them, puts the result in the repository or on the board | `brain assigned --level <level>` |
| 5 · Report | Assistant | Checks the task off; one result line goes to the Inbox | `brain report <n> "…"` |

The result comes back to step 2, so nothing reaches a lane without passing through your hands.

**The label.** On a next action, as `@javis:<level>` with the date it was assigned. `brain assign` adds both:

```text
- [ ] Draft an email to the accountant · @computer · ~20' · @javis:auto · assigned 2026-10-21
```

| Level | The assistant may | Example |
| --- | --- | --- |
| `suggest` | Read, research through G1, propose. No file writes | Compare the prices of three printers |
| `auto` | Also write drafts, code and issues in the repository | Draft an email, write a script in area 5x |
| `full` | Also act outside: send messages, post, order | Send an email you approved |

**Rules of the loop.**

1. Only you assign tasks. The assistant never adds or raises a label; the plugin and the hook block it.
2. At every level, the assistant never writes a permanent note, deletes data, skips G1, or closes or stops a project.
3. A task still open after `assistant.stale_after_days` (default 7) raises a warning in `brain check`. A label without a valid level is an error.
4. The Weekly Review counts assigned tasks that are open, done this week and stale.

The label text, the assistant's name and the levels are set in `[assistant]` in `brain.toml`.

## Rhythm

| Rhythm | What |
| --- | --- |
| Every day, 30–45 minutes | Pick at most 3 tasks from Next Actions, finish at least 1 real one, review 15–20 cards, capture new ideas; assign the assistant what it can do |
| Every turn | End with `brain turn <task\|idea\|file\|drop> "summary"` |
| Sunday, 30 minutes | Weekly Review: clear the Inbox; review projects and boards, Someday, Areas, Waiting For; compare the Index; review tasks assigned to the assistant; read the `brain weekly` metrics |
| Every month | Recheck 10 random claims in permanent notes and knowledge maps |
| Every quarter | Each Area gives rise to one project; merge categories if needed |

## In the background, outside the flow

- `_log`: machine logs, items rejected by G1, the `brain turn` log.
- Archive: finished or stopped projects, with the reason they stopped.
