# Glossary

Brain_Standard 4.0 uses English for every name in the system: commands, configuration keys, frontmatter keys, rule codes, file and folder names. This page defines each term and lists the name it had up to 3.0, so that older notes, logs and conversations stay readable. `brain migrate` performs exactly the renames listed here (see [migration.md](migration.md)).

## Core concepts

| Term | Meaning | Up to 3.0 |
| --- | --- | --- |
| Brain | Your second brain: Markdown files in a git repository, plus the rules and the `brain` CLI | Bộ não |
| Vault | The `vault/` folder that holds every note | vault |
| Inbox | The single place where everything lands before it is clarified | Inbox |
| Clarify | Answering the two questions for an Inbox item and moving it to its destination | Làm rõ |
| Is it actionable? | First clarifying question | Cần làm gì không? |
| Is it worth keeping? | Second clarifying question, asked when the answer to the first is no | Có đáng giữ không? |
| Lane | One of the three streams an item can flow into: action, knowledge, files and code | Làn |
| Action lane | Next actions, projects, someday, areas, waiting for, archive (GTD + PARA) | Làn hành động |
| Knowledge lane | Fleeting, literature and permanent notes, maps of content, flashcards (Zettelkasten + LYT + FSRS) | Làn tri thức |
| Files and code lane | The 50–59 area numbered with Johnny Decimal | Làn file và code |
| Link I1–I7 | The seven named links that carry items between lanes | Đường nối I1–I7 |
| Execution layer | The board (for example GitHub Projects) that holds backlog, milestones and owners of a multi-step project | Tầng thực thi |
| Turn | One working session with an agent, closed with `brain turn` | Lượt |
| Daily loop | Pick up to 3 tasks, do at least 1, review cards, capture new ideas | Vòng ngày |
| Weekly Review | The Sunday review, with metrics from `brain weekly` | Weekly Review |
| DAB | Design Authority Board document: the architecture document in [architecture.md](architecture.md) | DAB |

## Trust gates and source records

| Term | Meaning | Up to 3.0 |
| --- | --- | --- |
| Trust gate G1–G4 | The four checks that decide how far a fact brought in by an AI may travel | Cổng kiểm duyệt K1–K4 |
| G1 · intake gate | Before the Inbox: the fact needs a complete source record | K1 |
| G2 · literature gate | Source grade A–C and an archived copy | K2 |
| G3 · permanent gate | Credibility 1–2 | K3 |
| G4 · flashcard gate | Credibility 1–2; numbers carry an expiry date | K4 |
| Source record | The frontmatter an agent attaches to a fact it brings in | Phiếu nguồn |
| Grade | Two-character Admiralty code: source reliability A–F and information credibility 1–6, for example `B2` | Mã (Admiralty) |
| Reach | How far a fact may travel after G1: `card` (flashcard), `literature`, `fleeting` | Đi tối đa tới |
| Strict mode | `gates.strict = true`: G1 returns incomplete records and `brain turn` refuses to close while the vault has errors | Chặn cứng (`chan_cung`) |
| Unverified | Label on a fact graded D or F; it may go no further than Fleeting | Chưa kiểm (`chua-kiem`) |

## The assistant (Javis)

| Term | Meaning | Up to 3.0 |
| --- | --- | --- |
| Assistant | An operator that runs on top of the brain, for example Javis OS. It captures into the Inbox and follows up on assigned tasks | Javis |
| Capture (assistant) | The assistant writes your words, or a fact through G1, into the Inbox | Thu |
| Assign | You mark a next action as one the assistant may do, at a given level | Giao |
| Follow up | The assistant does an assigned task and reports the result | Làm tiếp |
| Report | The assistant marks the task done; a result line goes back to the Inbox | Trả kết quả (`brain xong`) |
| Level | The ceiling for an assigned task: `suggest` (read, research, propose), `auto` (also write drafts, code, issues), `full` (also act outside: send, post, order) | Mức |
| Assignment label | `@javis:<level>` on a next action, followed by `assigned YYYY-MM-DD` and, once done, `done YYYY-MM-DD` | Nhãn `@javis` · `giao` · `xong` |
| Stale assignment | An assigned task still open after `assistant.stale_after_days` | Việc giao treo |

## Commands

| Command | Does | Up to 3.0 |
| --- | --- | --- |
| `brain capture "…" [--channel C]` | Write your words to the Inbox | `brain ghi "…" [--kenh K]` |
| `brain submit <file>` | Submit a fact with its source record through G1 | `brain nop <file>` |
| `brain check` | Check the vault against the rules and gates | `brain kiem` |
| `brain turn <task\|idea\|file\|drop> "summary"` | Close a turn | `brain turn <viec\|y\|file\|xoa> "…"` |
| `brain weekly [--save]` | Weekly Review metrics | `brain weekly [--ghi]` |
| `brain assign "<match>" <level>` | Assign a next action to the assistant (you only) | `brain giao "…" <mức>` |
| `brain assigned [--level L]` | List open assigned tasks | `brain javis [--muc M]` |
| `brain report <n> "result" [--level L]` | Mark an assigned task done and send the result to the Inbox | `brain xong <số> "…" [--muc M]` |
| `brain migrate [--dry-run]` | Convert a 3.0 brain to 4.0 names | (new) |

Turn types: `task` (produced a task), `idea` (produced an idea or note), `file` (produced a file or code), `drop` (nothing kept). Up to 3.0: `viec`, `y`, `file`, `xoa`.

The line every AI answer ends with is now `Brain: <task|idea|file|drop> · <destination> · <content> · cmd: brain …` (was `Bộ não: …`).

Destinations: Do now, Next Actions, Project, Someday, Waiting For, Fleeting, Literature, Permanent, Code (50–59), Delete.

Capture channels: `hand` (typed or written, was `tay`), `voice` (was `noi`), `telegram`, `mcp`, `export`, `javis`.

## Configuration (`brain.toml`)

| 4.0 | Up to 3.0 |
| --- | --- |
| `[brain]` `version`, `vault` | `[bo_nao]` `phien_ban`, `vault` |
| `[paths]` | `[duong_dan]` |
| `paths.inbox_agent`, `paths.next_actions`, `paths.waiting_for`, `paths.projects`, `paths.someday`, `paths.fleeting`, `paths.literature`, `paths.permanent`, `paths.maps`, `paths.weekly`, `paths.log` | same keys |
| `paths.inbox` | same |
| `paths.code` · `paths.templates` · `paths.turn_log` · `paths.rejected_log` | (new; were fixed in code: `Coding`, `_mau`, `_log/turns.md`, `_log/k1.md`) |
| `[clarify]` `fleeting_max_days`, `moc_min_notes` | `[lam_ro]` `fleeting_toi_da_ngay`, `moc_khi_du_note` |
| `[rhythm]` `daily_pick_max` | `[nhip]` `vong_ngay_chon_toi_da` |
| `[gates]` | `[kiem_duyet]` |
| `gates.strict` | `chan_cung` |
| `gates.required_fields` | `truong_bat_buoc` |
| `gates.reject_sources`, `gates.reject_credibility` | `loai_nguon`, `loai_tin` |
| `gates.fleeting_only_sources` | `chi_toi_fleeting` |
| `gates.literature_sources` | `literature_nguon` |
| `gates.permanent_credibility` | `permanent_tin` |
| `gates.card_credibility` | `the_tin` |
| `[execution]` `warn_milestone_without_board`, `warn_project_without_task` | `[thuc_thi]` `canh_bao_milestone_khong_board`, `canh_bao_project_khong_viec` |
| `[johnny_decimal]` `area`, `max_categories` | `[johnny_decimal]` `khu`, `toi_da_category` |
| `[assistant]` `name`, `label`, `levels`, `stale_after_days` | `[javis]` `nhan`, `treo_toi_da_ngay` |
| `[assistant.plugin]` `timeout_seconds` · `[assistant.guard]` | (new; were fixed in code) |

## Frontmatter keys

| 4.0 | Up to 3.0 | Used in |
| --- | --- | --- |
| `type` | `loai` | every note |
| `source` | `nguon` | source record, literature, permanent |
| `original_source` | `nguon_goc` | source record |
| `author` | `tac_gia` | source record |
| `published` | `ngay_dang` | source record |
| `retrieved` | `ngay_lay` | source record |
| `valid_until` | `han_dung` | source record, literature, permanent |
| `archived` | `luu_tru` | source record, literature |
| `hash` | `hash` | source record |
| `grade` | `ma` | source record, literature, permanent |
| `verification` | `cach_kiem` | source record |
| `max_reach` (`card`, `literature`, `fleeting`) | `k1_toi_da` (`the`, …) | added by G1 |
| `submitted` | `ngay_nop` | added by G1 |
| `label: unverified` | `nhan: chua-kiem` | added by G1 |
| `location` | `vi_tri` | literature |
| `read_on` | `doc_ngay` | literature |
| `links` | `lien_ket` | permanent |
| `cards` | `the` | permanent |
| `status` | `trang_thai` | project |
| `started` | `bat_dau` | project |
| `outcome` | `ket_qua` | project |
| `done_when` | `tieu_chi_xong` | project |
| `stop_when` | `tieu_chi_dung` | project |
| `due` | `han` | project |
| `people` | `nguoi` | project |
| `stop_reason` | `ly_do_dung` | project |
| `standard` | `tieu_chuan` | area |
| `project_this_quarter` | `project_quy_nay` | area |
| `date` | `ngay` | fleeting |

## Rule codes (`brain check`)

| 4.0 | Up to 3.0 | Rule |
| --- | --- | --- |
| G1-01 · G1-02 · G1-03 | K1-01 · K1-02 · K1-03 | Agent item: missing field, malformed grade, grade that should have been rejected |
| G2-01 · G2-02 · G2-03 | K2-01 · K2-02 · K2-03 | Literature with a grade: malformed, source outside A–C, no archived copy |
| G3-01 · G3-02 | K3-01 · K3-02 | Permanent with a grade: malformed, credibility outside 1–2 |
| KN-01 · KN-02 · KN-03 | TT-01 · TT-02 · TT-03 | Permanent without a link · permanent without an id · fleeting too old |
| VD-01 | KD-01 | Past its `valid_until` date |
| AC-01 · AC-02 · AC-03 | HD-01 · HD-02 · HD-03 | Project status invalid · active project missing outcome or criteria · stopped project without a reason |
| EX-01 · EX-02 · EX-03 | TH-01 · TH-02 · TH-03 | Milestone without a board · active project without any task · project past its due date |
| AS-01 · AS-02 | JV-01 · JV-02 | Assignment label without a valid level · stale assignment |

## Files and folders

| 4.0 | Up to 3.0 |
| --- | --- |
| `vault/_templates/source-record.md` | `vault/_mau/phieu-nguon.md` |
| `_template-project.md`, `_template-area.md`, `_template-literature.md`, `_template-permanent.md`, `_template-moc.md`, `_template-weekly.md` | `_mau-project.md`, `_mau-area.md`, `_mau-literature.md`, `_mau-permanent.md`, `_mau-moc.md`, `_mau-weekly.md` |
| `vault/Code/50 System/50.00 Index (JDex).md` | `vault/Coding/50 He thong/50.00 Index (JDex).md` |
| `vault/_log/rejected.md` | `vault/_log/k1.md` |
| `tools/brain/` (package) | `tools/brain.py` |
| `integrations/javis/claude_write_guard.py` | `integrations/javis/chan_ghi_claude.py` |
| `docs/getting-started.md` | `docs/huong-dan.md` |
| `docs/flow.md` | `docs/dong-chay.md` |
| `docs/lanes.md` | `docs/ba-lan.md` |
| `docs/trust-gates.md` | `docs/kiem-duyet.md` |
| `docs/execution-layer.md` | `docs/tang-thuc-thi.md` |
| `docs/using-with-ai.md` | `docs/dung-voi-ai.md` |
| `docs/using-with-javis-os.md` | `docs/dung-voi-javis.md` |
| `docs/architecture.md` | `docs/kien-truc-he-thong.md` |
