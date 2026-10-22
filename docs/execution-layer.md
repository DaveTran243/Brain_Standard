# The execution layer

The brain coordinates: the outcome you want, the done and stop criteria, the decisions and the lessons. The execution of a multi-step project happens on the board in its category's repository, which holds the backlog, milestones, due dates and the owner of each task.

## What lives where

| Thing | Place |
| --- | --- |
| Outcome, done criteria and stop criteria | Project file |
| Major decisions and their reasons | Project file, `## Decisions` section |
| The main task you do next | Next Actions |
| Backlog, issues, ordinary bugs | Board |
| Milestones and due dates | Board |
| Owner of each task | Board |
| Waiting on someone outside any board | Waiting For |
| A lesson after each milestone | Permanent note, through I1 |
| A task the assistant may do for you | Next Actions, with an assignment label (since 3.0) |

## The project file

Template: [`vault/10-Action/13-Projects/_template-project.md`](../vault/10-Action/13-Projects/_template-project.md). The execution fields are `repo`, `board`, `milestone`, `due`, `people`, plus the `## Decisions` section.

```yaml
---
type: project
status: active            # someday | active | done | stopped
started: 2026-10-20
outcome: "…"
done_when: "…"
stop_when: "…"
code: 51                  # category under Code/
repo: owner/repo-name
board: https://github.com/users/owner/projects/1
milestone: "M1 · …"
due: 2026-12-31           # empty if there is no deadline
people: [you, …]
---
```

## How a task flows

1. **A 1–2 step project:** no board needed; its tasks go straight to Next Actions.
2. **A multi-step project:** open the category, repository and board as soon as you create it (I3), then split the first milestone.
3. **Every morning:** tasks on the board that you are next to work on are pulled into Next Actions with their issue number.
4. **A log shows an error:** it becomes an issue on the board. Only an error that blocks the whole project goes up to Next Actions through I6.
5. **A milestone is done:** draw 1 lesson (I1) and record the next milestone in the project file.
6. **Handing work to someone:** assign an owner on the board. Waiting For is left for things outside any board.

## Measuring instead of limiting

Since 2.2.0 no number blocks capture: `brain turn` does not complain about many projects or many next actions. `brain weekly` only measures, so you can see for yourself: active projects, open next actions, projects past their due date.

`brain check` still warns (without blocking) when:
- an active project has a milestone but no board (EX-01);
- an active project has no task in Next Actions and no board (EX-02);
- an active project is past its `due` date (EX-03).
