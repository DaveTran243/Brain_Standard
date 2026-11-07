# Upgrading

## From 4.0 to 4.2

4.2 adds the knowledge graph and makes the assistant platform-neutral. Nothing in your notes changes.

1. Pull the new `tools/`, `integrations/` and `docs/`.
2. `bin/brain migrate --dry-run`, then `bin/brain migrate`: `@javis:<level>` labels in Next Actions become `@agent:<level>`, unless your `brain.toml` sets `[assistant] label = "@javis"` (then nothing changes and you keep the name).
3. `bin/brain kg build` once. From then on the hooks or the `brain_remember` tool keep it current; `brain check` warns (KG-01) when it lags.
4. Claude Code: replace the old hook path `integrations/javis/claude_write_guard.py` with the three hooks in [integrations/claude-code/README.md](../integrations/claude-code/README.md).
5. Javis OS: copy `integrations/javis/brain-standard/` to `plugins/` again and enable it; it now registers 10 tools, including `brain_recall` and `brain_remember`. Other platforms: [integrations/mcp/README.md](../integrations/mcp/README.md).

## From 3.0 to 4.0

Brain 4.0 renames everything in English: commands, configuration keys, frontmatter keys, rule codes, files and folders. The flow and the rules are the same as 3.0. An existing brain is converted once with `brain migrate`; there are no Vietnamese aliases, so old commands such as `brain ghi` stop working after the upgrade. Every old and new name is listed in [glossary.md](glossary.md).

## Before you start

- Commit or stash any work in progress, so the migration is one clean diff you can review or undo.
- Close Obsidian or any editor that might rewrite files while the migration runs.
- Stop Javis loops that use the plugin until you have updated it (step 5).

## Steps

1. **Pull the new code** (not `vault/` or `brain.toml`):

   ```sh
   git fetch standard
   git checkout standard/main -- tools bin integrations tests docs CHANGELOG.md
   ```

   The 3.0 single file `tools/brain.py` is replaced by the `tools/brain/` package. Delete the old file if git left it behind: `git rm tools/brain.py`.

2. **See what will change:**

   ```sh
   bin/brain migrate --dry-run
   ```

   It lists every change without writing anything.

3. **Migrate:**

   ```sh
   bin/brain migrate
   bin/brain check
   git diff --stat
   ```

   Running `brain migrate` again is safe; it prints `Nothing to migrate` once everything is converted.

4. **Refresh the rules for agents.** Copy the English `vault/AGENTS.md` and templates from the standard, then copy the rules to the root again:

   ```sh
   git checkout standard/main -- vault/AGENTS.md vault/_templates
   cp vault/AGENTS.md AGENTS.md      # and/or CLAUDE.md, GEMINI.md
   ```

   Paste the new [shared rule block](using-with-ai.md#the-shared-rule-block) into the chat AIs you use: the footer is now `Brain:`, and the prefixes are `capture:`, `today`, `weekly`.

5. **Update Javis OS**, if you use it: copy `integrations/javis/brain-standard/` to `plugins/` again, update the hook in `.claude/settings.json` to `write_guard.py`, and change the tool names in your loops and project instructions (`brain_ghi` → `brain_capture`, `brain_viec_javis` → `brain_assigned`, `brain_xong` → `brain_report`…). See [integrations/javis/README.md](../integrations/javis/README.md).

6. **Commit** the migration on its own: `git commit -am "Migrate to Brain 4.0"`.

## What `brain migrate` changes

| Where | Change |
| --- | --- |
| `brain.toml` | Tables and keys renamed (`[kiem_duyet]` → `[gates]`, `chan_cung` → `strict`, `[javis]` → `[assistant]`…), version set to the CLI's version (4.0.0 or later). Comments in the file are not kept; defaults now live in `tools/brain/defaults.toml` |
| Files and folders | `_mau/` → `_templates/` (`phieu-nguon.md` → `source-record.md`); every `_mau-*.md` → `_template-*.md`; `Coding/` → `Code/` and `50 He thong` → `50 System`; `_log/k1.md` → `_log/rejected.md` |
| Frontmatter, in every note | Keys renamed (`trang_thai` → `status`, `tieu_chi_xong` → `done_when`, `ma` → `grade`, `luu_tru` → `archived`…), including commented-out keys in templates. Values `the` → `card` and `chua-kiem` → `unverified` |
| Next Actions | `· giao <date>` → `· assigned <date>`, `· xong <date>` → `· done <date>` |
| Inbox | Channels `(tay)` → `(hand)`, `(noi)` → `(voice)`; `(javis) Kết quả` → `(javis) Result`; reach names in agent lines; the `## Mục` heading |
| Turn log | Turn types `viec`, `y`, `xoa` → `task`, `idea`, `drop` |
| Rejected log | `loại ·` → `rejected ·` and the file heading |
| Any note | Paths written as `Coding/…` → `Code/…` |

## What it leaves alone

- **The content of your notes.** Bodies, titles and tags stay in whatever language you wrote them. Line rules apply only to the list files they belong to, so a sentence in a note that happens to contain `xong` or `giao` is not touched.
- **The body text of templates already in your vault.** Their keys and file names are converted, but the explanations inside stay in Vietnamese until you copy the English templates (step 4).
- **Custom `[paths]`** you set yourself: the keys move to `[paths]` with your values unchanged.
- **Anything already in 4.0 form.**

## Undo

Before committing: `git restore .` and `git clean -fd vault` bring back the 3.0 files (check the list `git clean -n` shows first). After committing: `git revert <commit>`. The 3.0 CLI is in git history if you need to run it again.

## Name changes at a glance

| 3.0 | 4.0 |
| --- | --- |
| `brain ghi` · `--kenh` | `brain capture` · `--channel` |
| `brain nop` | `brain submit` |
| `brain kiem` | `brain check` |
| `brain turn viec / y / file / xoa` | `brain turn task / idea / file / drop` |
| `brain weekly --ghi` | `brain weekly --save` |
| `brain giao` | `brain assign` |
| `brain javis --muc` | `brain assigned --level` |
| `brain xong` | `brain report` |
| K1–K4 | G1–G4 |
| `Bộ não:` footer · `ghi:` · `hôm nay` | `Brain:` footer · `capture:` · `today` |

The full list, including every configuration key, frontmatter key and rule code, is in [glossary.md](glossary.md).
