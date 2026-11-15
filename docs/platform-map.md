# The platform root and its map

Brain_Standard · proposed for the next version · terms: [glossary.md](glossary.md) · related: [knowledge-graph.md](knowledge-graph.md).

A brain may keep its whole platform on one disk or folder, the **platform root**: its functions (the `brain` CLI, hooks, tools), its memory (the vault, the knowledge graph, this map, exports from chat apps), its library and its archive. The **platform map** is a graph of every folder and file under that root. The knowledge graph says what the brain knows; the map says where everything is. Agents read both before they act and add to the map whatever they write.

| Item | Value |
| --- | --- |
| Code | `tools/brain/drive.py`, `tools/brain/drawing.py`, `brain kg drive · draw`, `brain where`, `brain hook prompt · stop` |
| Data | `vault/_kg/drive-state.json`, `vault/_kg/drive.jsonl` (machine-local; `.gitignore` keeps them out of git) |
| Configuration | `[drive]` in `tools/brain/defaults.toml`, off by default |
| Agent tools | `brain_where` (readonly), `brain_map_update` (safe) |
| Tests | `tests/test_drive.py` |

## 1 · Turning it on

```toml
[drive]
enabled = true
root = "D:/"                       # the disk or folder that holds the whole platform
inbox = "D:/Brain/00-Inbox"        # where a result with no home yet is saved
```

Then `brain kg drive` once. With Claude Code the hooks in `integrations/claude-code/` keep the map current.

## 2 · Rules for agents

The rules are in `vault/AGENTS.md`, "Platform root":

1. **Write to the root**: every result an agent produces goes under the root, in its Johnny Decimal folder or in `[drive] inbox`.
2. **Map what you write**: the Stop hook, or `brain kg drive` / `brain_map_update`.
3. **Read the map before the disk**: `[Brain Drive]` lines from the prompt hook, `brain where` / `brain_where`; search the disk only when the map has nothing.
4. **Names, not contents**: the map never carries a file's contents into the knowledge graph.

Rule 1 is followed, not forced. A guard that refused every write outside the root would also break scratch files and tools that need another disk; the Weekly Review can look for results left elsewhere.

## 3 · How the map is built

**Scan.** `brain kg drive` walks the root, skipping `[drive] skip` (`.git`, `node_modules`, build output, recycle bins) and `skip_files` (`pagefile.sys` …). It reads names, sizes and dates; the one file it opens is `.git/config`, for a repository's remote. A folder with more than `bulk_files` (200) files is a **dataset**: one node with its count, size and extensions, no file nodes. Each folder's mtime is kept and an update re-reads only folders whose mtime changed, which is what adding, removing or renaming a file does. On a reference disk with 757 folders and 51,600 files a full scan took 0.55 s and an update 0.28 s, so the Stop hook can run it after every turn.

**Graph.** Triples in the knowledge graph's shape with `kind: location`, `trust: system`, `src: drive`:

| Triple | From |
| --- | --- |
| folder `contains` folder or file | the scan |
| file `is a` document · code · data · media · archive · program · other | the extension |
| folder `is a` dataset · git repository; `holds` "N files (…)"; `repo` URL | the scan |
| "51.01 invoice-bot" `located at` folder; `for project`; `repo` | the JDex (`[drive] jd_index`): its `location:` and any absolute path in its `note:` |
| note title `stored at` file | the knowledge graph's documents |

The two graphs stay in two files so that tens of thousands of locations never crowd the facts an agent reads before answering. They meet at the notes: a note's title is an entity in the knowledge graph and is `stored at` its file in the map.

**Read.** `brain where "<words>"` folds diacritics (`Thư viện` matches `thu-vien`), drops stop words, and scores each location: 3 per word in its own name or labels (JD number, note title, project), 1 per word only in a parent folder, +2 when every word matched, +3 per pair of words side by side in order, −3 under `[drive] demote` (`90-Archive`), so a live copy ranks above an archived one. The prompt hook shows hits scoring at least `min_score` (4).

**Draw.** `brain kg draw <file.html>` writes one self-contained page: folders sized by file count, datasets, repositories, JD numbers and the knowledge graph's concepts, with search, layers, a depth slider and an archive toggle. `--files` adds a node per file; `--fragment` leaves out the document wrapper for hosts that add their own.

## 4 · Decisions

- **Off by default.** A brain opts in; the standard never scans a disk it was not given.
- **Machine-local.** The map describes one machine's disk, so it is not committed and a cloud session sees none.
- **Standard library only.** The scan, the graph and `where` need nothing beyond Python; the drawing loads d3 from cdnjs in the browser.
