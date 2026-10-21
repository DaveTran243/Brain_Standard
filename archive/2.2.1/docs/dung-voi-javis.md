# Dùng bộ não với Javis OS

[Javis OS](https://github.com/blogminhquy/javis-os) là một agent AI tự host: chạy trên laptop hoặc VPS, đổi được model (Claude Code, Codex, Grok, Antigravity, OpenRouter, Gemini, Ollama…), nói chuyện qua dashboard, giọng nói, Telegram, Zalo, Slack, và làm việc nền bằng loop, nhắc hẹn, hàng việc Kanban. Nó có một "Second Brain" riêng là một thư mục Markdown.

Trang này chỉ cách cho Javis làm việc trên bộ não 2.2 mà không phá luật của bộ não. Đọc [dung-voi-ai.md](dung-voi-ai.md) trước nếu bạn chưa quen ba mức kết nối và khối quy tắc chung.

Khảo sát trên Javis OS bản 0.270.0, ngày 21/10/2026. Javis ra bản mới rất nhanh, nên đối chiếu lại các mục đánh dấu "kiểm lại khi nâng bản".

## Vì sao hợp nhau

Hai bên cùng một ý: **thuê model, giữ bộ não**. Bộ não là Markdown và git của bạn; Javis là lớp chạy AI, đổi model không mất gì. Javis lấp đúng những chỗ bộ não 2.2 cố ý để trống:

| Bộ não 2.2 đang thiếu | Javis cho |
| --- | --- |
| Ghi nhanh khi xa máy tính | Telegram, Zalo, Slack, giọng nói, tất cả đổ về cùng một chỗ |
| Nhịp ngày và Weekly Review phải tự nhớ chạy | Nhắc hẹn theo giờ hoặc cron, gửi kết quả về Telegram |
| Mức 3 chỉ có với agent có shell | Mọi engine, kể cả engine API, gọi được lệnh `brain` qua plugin |
| Xem mạng note | Đồ thị tri thức vẽ từ link `[[...]]`, chạy offline |

Bù lại, Javis có những thói quen ngược với luật của bộ não. Phần dưới nói rõ từng chỗ và cách tắt.

## Bản đồ khái niệm

| Javis | Bộ não 2.2 | Ghi chú |
| --- | --- | --- |
| `sources/` | `30-Knowledge/literature/` | Javis lưu nguồn thô không cần phiếu nguồn |
| `wiki/` | `30-Knowledge/permanent/`, `40-Maps/` | Javis tự viết wiki. Bộ não cấm AI viết permanent note |
| `memory/MEMORY.md`, `memory/facts/` | Không có | Trí nhớ làm việc của Javis về bạn. Để nó nằm ngoài `vault/` |
| INGEST ("lưu vào source") | `brain nop` qua K1 | Javis bỏ qua K1 |
| Tự học sau mỗi cuộc chat | Không có | Mặc định bật, chế độ tự ghi |
| Curator, LINT wiki | `brain kiem` | LINT của Javis chỉ gợi ý; `brain kiem` là luật |
| Kanban task | Next Actions, board của project | Việc nền do bạn giao, không thay Next Actions |
| Loop, nhắc hẹn | Nhịp ngày, tuần, tháng | Dùng để chạy nhịp, ở mức chỉ đọc |
| Skill, plugin | `AGENTS.md`, CLI `brain` | Plugin trong gói này nối hai bên |

## Chỗ xung đột cần biết trước

1. **Tự học mặc định bật ở chế độ tự ghi.** Sau mỗi vài lượt chat, Javis chưng cất hội thoại thành `memory/facts/`, trang `wiki/` và skill mới, rồi commit với tiền tố `learn:`. Trang wiki do AI viết là đúng thứ nguyên tắc 2 cấm, và dữ kiện trong đó không có phiếu nguồn.
2. **INGEST đi vòng qua K1.** Thả file vào chat rồi nói "lưu vào source" thì Javis ghi thẳng vào `sources/` và `wiki/`.
3. **Javis tự tạo thư mục trong brain.** Ngay lượt chat đầu, Javis tạo `memory/`, `skills/` (các skill hệ thống), `.claude/skills/`, `Javis/` và một số file quản lý. Nếu bạn bấm "tạo cấu trúc chuẩn" hay "chuẩn hoá cấu trúc" trong Cài đặt, nó còn tạo `sources/`, `wiki/`, `agents/`, `workflows/`, `attachments/`, `00 - Dashboard/`, `01 - Daily Log/`… Không xoá gì của bạn, nhưng làm rối cây thư mục nếu trỏ vào `vault/`.
4. **Git của repo bị đụng tới khi bật tự học.** Brain đã là repo git thì Javis gộp một khối vào `.gitignore` theo kiểu "chặn tất cả, chỉ cho đuôi file chữ" rồi commit `chore:`. File mới không có đuôi chữ (ví dụ một script như `bin/brain`) sẽ bị bỏ qua khi `git add`. File đã theo dõi thì không sao.
5. **Chỉ engine Claude Code đọc `CLAUDE.md` của repo.** Javis chạy Claude Code với thư mục làm việc là brain và nạp cấu hình project, nên `CLAUDE.md` ở gốc brain có hiệu lực. Các engine API chỉ nhận prompt của Javis, `MEMORY.md` và hướng dẫn của project trong Javis.
6. **Hook của plugin chỉ thấy tool đi qua MCP Hub.** Claude Code ghi file bằng tool Write, Edit riêng của nó, không qua hub. Cần thêm hook của Claude Code (bước 7).
7. **Loop tạo từ chat mặc định ở mức `full`**, tức được làm hành động thật bên ngoài. Với bộ não, chọn `suggest` (chỉ đọc) cho mọi việc nhịp.

## Cài đặt từng bước

### 1. Cài Javis

Theo [Quick start của Javis](https://github.com/blogminhquy/javis-os#-quick-start). Đọc cảnh báo của Javis về việc chạy nền bằng gói thuê bao Claude Pro/Max: việc nền 24/7 hay chạy trên VPS nằm ngoài phạm vi dùng cá nhân. Cho việc nền, dùng API key hoặc trỏ "model việc nền" sang nhà cung cấp khác.

### 2. Trỏ brain vào gốc repo bộ não

Ở góc trái thanh trên, bấm 📁 và chọn **thư mục gốc repo**, tức thư mục có `brain.toml`, không phải `vault/`.

Lý do: thư mục Javis tự tạo sẽ nằm cạnh `vault/`, ngoài vùng `brain kiem` rà; plugin tìm được `brain.toml` và `tools/brain.py`. Đồ thị tri thức vẫn vẽ được các note trong `vault/`.

**Không bấm** "tạo cấu trúc chuẩn" hay "chuẩn hoá cấu trúc" cho brain này. Banner "cấu trúc chưa chuẩn" thì bỏ qua.

### 3. Thêm vào `.gitignore` của repo

```gitignore
# Javis OS: log thô, cache và trạng thái chạy
memory/conversations/
attachments/
inbox/
.javis-learn.lock
Javis/learn-staging/
Javis/learn-log/
Javis/loop-log/
Javis/skill-usage.json
nhap/
```

`memory/conversations/` là hội thoại thô, có thể chứa thứ bạn lỡ dán. `attachments/` và `inbox/` là vùng cache Javis tự dọn sau 30 ngày (khác `vault/00-Inbox/`). `nhap/` là chỗ Javis viết phiếu nguồn trước khi nộp (bước 5).

### 4. Hạ tự học xuống mức không ghi

Vào **Tự học** (nhóm Brain). Ô **Chế độ ghi** có ba nút: chạy thử (Dry run), gợi ý (Suggest) và tự ghi (Write automatically). Bản cài mới để tự ghi.

- **Nên chọn:** chạy thử hoặc gợi ý. Cả hai không tạo file nào, chỉ ghi vào nhật ký học "định học gì", để bạn đọc và tự quyết.
- **Nếu vẫn muốn Javis nhớ về bạn:** để tự ghi, nhưng trong ô **Học cái gì** chỉ bật Memories, tắt Wiki và Skill. Ký ức nằm trong `memory/` ở gốc repo, ngoài `vault/`, và mỗi lượt học là một commit `learn:` trong repo của bạn.
- **Curator**: để tắt. Dùng `brain kiem` thay cho LINT wiki.
- Bấm **Lưu**. Chế độ và các công tắc chỉ có hiệu lực sau khi lưu.

Bộ ghi của tự học là code Python của Javis, không đi qua tool, nên hook của plugin không chặn được nó. Chỉ có cấu hình ở đây giữ nó ngoài `vault/`.

Không dùng INGEST. Muốn đưa một tài liệu vào bộ não, làm theo quy trình "Tra cứu có kiểm chứng" ở dưới.

### 5. Đặt quy tắc cho mọi engine

- **Engine Claude Code, Codex:** chép quy tắc ra gốc repo như ở [dung-voi-ai.md](dung-voi-ai.md):

  ```sh
  cp vault/AGENTS.md AGENTS.md
  cp vault/AGENTS.md CLAUDE.md
  ```

- **Mọi engine:** tạo một project trong Javis, ví dụ "Bộ não", mở bảng của project (tab **Hướng dẫn**) và dán [khối quy tắc chung](dung-voi-ai.md#khối-quy-tắc-chung) vào, thêm ba dòng:

  ```text
  8. Trong Javis: dùng tool brain_ghi, brain_nop, brain_kiem, brain_turn, brain_weekly thay cho lệnh shell.
  9. Phiếu nguồn viết vào thư mục nhap/ ở gốc repo, rồi nộp bằng brain_nop. Không ghi vào vault/00-Inbox/agent.
  10. Không dùng INGEST, không ghi vào sources/ hay wiki/.
  ```

  Hướng dẫn của project đi vào mọi lượt chat trong project đó, với mọi engine, tối đa 4.000 ký tự. Chat ngoài project thì không có, nên làm việc với bộ não trong project này.

### 6. Cài plugin `brain-standard`

Gói này có sẵn plugin ở `integrations/javis/brain-standard/`. Plugin làm hai việc:

- Đưa năm lệnh thành tool cho mọi engine: `brain_ghi`, `brain_nop`, `brain_kiem`, `brain_turn`, `brain_weekly`. `brain_kiem` và `brain_weekly` chỉ đọc, chạy được cả ở mức `suggest`; ba tool còn lại ghi file nên cần mức `auto` trở lên.
- Hook `pre_tool_call` chặn AI ghi bằng `javis_write_file`, `javis_edit_file` vào `30-Knowledge/permanent/`, `00-Inbox/agent/` và mọi file hay thư mục bắt đầu bằng `_` trong `vault/`. AI nhận lại câu giải thích và cách làm đúng.

Chép vào brain (gốc repo):

```sh
mkdir -p plugins
cp -r integrations/javis/brain-standard plugins/
```

Muốn mọi brain trong Javis đều có thì chép vào `<JAVIS_STATE_DIR>/plugins/` thay vì `plugins/` trong repo. Plugin để `enabled: false`; đọc `plugin.py` rồi bật nó trên trang **Plugins** của Javis, hoặc sửa thành `enabled: true`.

Plugin chỉ dùng thư viện chuẩn và gọi lại `tools/brain.py` của repo, nên luật nằm một chỗ. Nếu brain trong Javis không phải repo bộ não, tool báo lỗi và hook không chặn gì.

### 7. Hook cho Claude Code

Thêm vào `.claude/settings.json` ở gốc repo (Javis nạp file này khi chạy engine Claude Code; Claude Code chạy thẳng trong repo cũng vậy):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|NotebookEdit",
        "hooks": [
          { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/integrations/javis/chan_ghi_claude.py\"" }
        ]
      }
    ]
  }
}
```

Script dùng đúng luật chặn của plugin. Trên Windows đổi `python3` thành `python`. Hook này có ích cả khi bạn dùng Claude Code mà không có Javis.

## Quy trình mẫu

### Ghi nhanh từ điện thoại

Nhắn Javis qua Telegram:

> ghi: hỏi lại bên kế toán về hoá đơn tháng 10

Javis gọi `brain_ghi` với kênh `telegram`. Mục vào `vault/00-Inbox/Inbox.md`, đúng như gõ `brain ghi` trên máy.

### Vòng ngày

Tạo một nhắc hẹn trên trang **Việc định kỳ**, hoặc nói trong chat:

> Tạo nhắc hẹn 7:00 mỗi ngày, mức chỉ đọc: đọc vault/10-Action/11-next-actions.md, gợi ý tối đa 3 việc cho hôm nay, chạy brain_kiem và báo lỗi nếu có. Gửi kết quả qua Telegram.

Mức `suggest` đọc được file và gọi `brain_kiem`, không ghi gì. Bạn chọn việc.

### Weekly Review

> Tạo nhắc hẹn 17:00 Chủ nhật, mức chỉ đọc: chạy brain_weekly, rồi đi qua vault/weekly/_mau-weekly.md và chỉ ra project treo, mục Inbox quá 7 ngày, milestone trễ. Gửi qua Telegram.

Bạn ngồi xuống, quyết định, rồi tự lưu số đo bằng `brain weekly --ghi`.

### Tra cứu có kiểm chứng

> Tra giúp tôi: <câu hỏi>. Tách thành các khẳng định đơn. Mỗi khẳng định viết thành một file trong nhap/ theo mẫu vault/_mau/phieu-nguon.md, rồi nộp bằng brain_nop.

Engine CLI có web sẵn; engine API dùng `javis_web_search`, `javis_web_fetch`. Mục thiếu phiếu bị K1 trả lại, mục mã E hoặc tin 5 vào `_log/k1.md`. Xong thì xoá các file trong `nhap/`.

### Làm rõ Inbox

Một loop mức `suggest` hợp với Inbox dày:

> Tạo loop 60 phút, mức chỉ đọc: mỗi chu kỳ đọc vault/00-Inbox/Inbox.md, chọn một mục chưa làm rõ, trả lời 2 câu hỏi và đề xuất lối ra. Không tự chuyển mục.

Loop chỉ gợi ý, bạn chuyển mục. Đừng dùng loop "tiêu hoá sources" mẫu của Javis.

### Đóng lượt

Cuối mỗi lượt làm việc trong project "Bộ não", Javis gọi `brain_kiem`, sửa lỗi nếu được, rồi `brain_turn`. Commit vẫn là việc của bạn hoặc của engine có shell.

## Giữ an toàn

- **Javis chạy AI với toàn quyền trên máy.** Khi chạy trên VPS, Javis bắt đăng nhập; vẫn nên để repo bộ não private và không để Javis mở ra internet nếu không cần.
- **Loop và nhắc hẹn cho bộ não dùng mức `suggest`.** Chỉ nâng lên `auto` cho việc cần ghi, như `brain_ghi`. Không cần `full`.
- **Sao lưu bằng git của chính repo bộ não.** Không cần bật "sao lưu GitHub" của Javis cho brain này.
- **Plugin chạy code Python thật trong server Javis.** Đọc `plugin.py` trước khi bật.
- **Hook không thay được luật.** Nó chặn đường ghi phổ biến nhất, không chặn được mọi cách ghi, ví dụ một lệnh shell. `brain kiem` và review của bạn vẫn là cổng cuối.

## Nguồn

Kiểm ngày 21/10/2026 trên Javis OS 0.270.0. Kiểm lại khi nâng bản.

- Cấu trúc brain, trí nhớ, INGEST, thư mục cache: [docs/en/13-second-brain.md](https://github.com/blogminhquy/javis-os/blob/main/docs/en/13-second-brain.md)
- Tự học mặc định bật, chế độ tự ghi, học memory, wiki, skill: [docs/en/22-self-learning.md](https://github.com/blogminhquy/javis-os/blob/main/docs/en/22-self-learning.md), `server/learn.py`, `LearnFeature.DEFAULT`
- Thư mục Javis tự tạo: `server/main.py`, `STANDARD_STRUCTURE`, `_ensure_brain_scaffold`; `server/system_sync.py`, `sync_brain`
- Gộp `.gitignore` và commit trên repo có sẵn: `server/git_brain.py`, `ensure_git_repo`
- Claude Code chạy với thư mục brain và nạp cấu hình project: `server/claude_sdk_engine.py`, `setting_sources`
- Plugin, tool, hook `pre_tool_call` chặn được bằng `{"deny": …}`: `server/plugins_host.py`, `register_tool`, `register_hook`, `wrap_with_hooks`
- Hướng dẫn của project đi vào mọi lượt chat, trần 4.000 ký tự: `server/main.py`, `build_system_prompt`, `_project_block`; `server/sessions.py`, `PROJECT_INSTRUCTIONS_MAX`
- Bật, tắt plugin trên trang Plugins: [docs/en/20-plugins.md](https://github.com/blogminhquy/javis-os/blob/main/docs/en/20-plugins.md)
