# Dashboard

`brain dashboard` serves a read-only page on `http://127.0.0.1:7799/` that shows how the brain is running, at a glance. Decision: ADR-20 in [architecture.md](architecture.md). Standard library only; nothing to install.

```
brain dashboard              # serve the page; Ctrl+C stops it
brain dashboard --open       # and open it in the default browser
brain dashboard --json       # print the numbers once (schema 1) and exit
```

## What the page shows

One screen, light or dark with the system.

**The four golden signals.** Google's SRE book names four signals every service dashboard should show: latency, traffic, errors, saturation. The brain is a service too: things come in (capture), are worked (turns, clarification) and go out (tasks done, notes). The top row shows these symptoms; the causes are below.

| Signal | In the brain | Coloured when |
|---|---|---|
| Traffic | captured items still in the Inbox, turns by type, next actions done (`· done YYYY-MM-DD`), last 7 days, with 30-day sparklines | never: a quiet week is not a fault |
| Latency | age of the oldest Inbox item and fleeting note, days since the newest `weekly/YYYY-Www.md` | over `[dashboard] inbox_max_age_days`, `[clarify] fleeting_max_days`, `[dashboard] weekly_max_gap_days` |
| Errors | `brain check` errors and warnings, items rejected at G1 in 7 days | any error (red) or warning (amber) |
| Saturation | Inbox, fleeting notes, stale assignments, documents the knowledge graph has not read | over the Inbox limit or `[kg] max_stale_documents` |

Below them:

- **To do, with the command to copy**: each rule code broken, how many times, examples, and the command (`brain check`, `brain kg build`, `brain assigned`).
- **Active projects**: open next actions per project (`[[project]]`), board, due date (past due in red).
- **Activity**: per day, items captured and still in the Inbox, turns by type, next actions done. Blank days are blank, not red.
- **Knowledge**: literature and permanent notes, open next actions, the knowledge graph and the platform map when they exist.
- **Turns**: the last entries of `_log/turns.md`.

The vault keeps no event log, so the activity rows come from dated lines: the Inbox only holds items not yet clarified, and done next actions count only when the line carries `· done YYYY-MM-DD`.

## What it never does

- **It never writes.** There is no route but `GET`; anything else answers 405. Every change still goes through the `brain` commands and the trust gates, so the page shows the command and you run it.
- **It shows no note content**: counts, ages, rule messages (which name files), project titles, turn summaries. Inbox lines are counted, never shown.
- **It listens on `127.0.0.1` only** unless `--host` says otherwise, and then it prints a warning.
- **It keeps no state.** Stop it and the brain has lost nothing (ADR-01). It reads the brain at most once per `cache_s`.
- **No score, no target, no streak.**

## Why it looks like this

| Finding | Source | On the page |
|---|---|---|
| A dashboard is the most important information for one or more goals, on one screen, to monitor at a glance | Few, *Information Dashboard Design* (2006) | one screen; four cards on top |
| Dashboards come in kinds by goal and interaction; choose the kind first | Sarikaya et al., IEEE TVCG 2019, doi:10.1109/TVCG.2018.2864903 | operational awareness, little interaction |
| Common design patterns: a single value with its trend, overview first | Bach et al., IEEE TVCG 2023, doi:10.1109/TVCG.2022.3209448 | a number and a sparkline per signal |
| Four golden signals; catch symptoms rather than causes; every alert must be actionable; sub-critical problems belong on a dashboard | Google, *Site Reliability Engineering*, "Monitoring Distributed Systems" | the top row; each rule with its command; no push alerts |
| Personal informatics has five stages; reflection is where systems fall short | Li, Dey, Forlizzi, CHI 2010 | the page serves reflection and points to action |
| People who track themselves stop and come back | Epstein et al., UbiComp 2015, doi:10.1145/2750858.2804250 | quiet days are blank, no streaks |
| A measure that becomes a target stops measuring | Goodhart (1975), Campbell (1976) | no score, no target; ratios over totals |
| Word-sized, data-intense graphics | Tufte, *Beautiful Evidence* (2006) | sparklines next to the numbers |
| Ambient displays: notification level is a design choice | Pousman and Stasko, AVI 2006 | low: the page waits to be looked at |

## Settings

`[dashboard]` in `tools/brain/defaults.toml`; change them in `brain.toml`:

```toml
[dashboard]
port = 7799
refresh_s = 30
cache_s = 10
days = 30
timeline_n = 20
inbox_max_age_days = 7
weekly_max_gap_days = 8
name = ""                 # the label in the brain picker
brains = []               # other brain folders for the picker, e.g. ["../family-brain"]
```

## The JSON contract

`GET /api/state?brain=<slug>` (and `brain dashboard --json`) returns `schema: 1`, a presentation-neutral shape so the page carries no field names of its own:

- `signals`: `traffic`, `latency`, `errors`, `saturation`, each with `level` (ok, warn, fail), `headline`, `caption`, `rows` (`label`, `value`, `limit`, `unit`, `level`) and `sparks` (`label`, `tone`, `values`);
- `series`: `days` and `rows` (`key`, `label`, `tone`, `values` per day);
- `rules` (`code`, `level`, `count`, `examples`, `command`), `projects`, `knowledge` (`label`, `value`), `timeline`;
- `errors_reading`: a source that cannot be read leaves its part empty and is named here; the rest of the page still works.

Other routes: `GET /api/brains` (the picker) and `GET /healthz`.
