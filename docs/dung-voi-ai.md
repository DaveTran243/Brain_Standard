# Dùng bộ não với AI · đa nền tảng

Bộ não không gắn với một AI nào. Nó là trí nhớ bền nằm trong repo của bạn, còn AI là trợ lý bạn có thể đổi bất cứ lúc nào. Trang này chỉ cách nối bộ não với Claude, ChatGPT, Gemini, model chạy local, và các agent làm việc trong repo như Claude Code, Codex, Gemini CLI, Cursor hay GitHub Copilot.

## Chia việc giữa bộ não và AI

| Bộ não giữ | AI làm |
| --- | --- |
| Trí nhớ dài hạn: việc, project, note, quyết định, bài học | Đề xuất lối ra cho từng mục trong Inbox theo hai câu hỏi |
| Luật: hai câu hỏi, ba làn, cổng K1–K4, tiêu chí xong và dừng | Tra cứu và trả kết quả kèm phiếu nguồn và mã độ tin |
| Bản gốc: Markdown và git trong repo private của bạn | Viết nháp: tóm tắt, dàn ý từ MOC, chia milestone, viết issue, code |
| Suy nghĩ của bạn trong permanent note, viết bằng lời bạn | Hỏi đáp dựa trên các note bạn đưa cho nó |

Hai điều không đổi dù dùng AI nào:

1. **AI không viết permanent note thay bạn.** AI giúp bạn hiểu, đặt câu hỏi, viết nháp literature. Câu chữ trong permanent note là của bạn, vì đó là nơi kiến thức thành của bạn.
2. **Dữ kiện AI mang về phải có mã độ tin.** AI hay nói sai một cách tự tin. Mã quyết định dữ kiện đó được đi tới đâu: chỉ là ý thoáng qua, thành tóm tắt nguồn, hay đủ chắc để học thuộc. Xem [kiem-duyet.md](kiem-duyet.md).

## Ba mức kết nối

| Mức | AI thấy gì | AI ghi vào bộ não thế nào | Hợp cho |
| --- | --- | --- | --- |
| **1 · Chat** | Chỉ những gì bạn dán vào cuộc chat | Mỗi câu trả lời kết thúc bằng dòng "Bộ não:"; bạn chép vào bằng `brain ghi` hoặc gõ tay | Ghi nhanh, làm rõ Inbox, hỏi nhanh, dùng trên điện thoại |
| **2 · Chat có tài liệu** | Các file bạn tải lên: `docs/`, MOC, các note liên quan | Giống mức 1 | Học và hỏi đáp dựa trên note của bạn, Weekly Review |
| **3 · Agent trong repo** | Toàn bộ vault | Tự sửa file và chạy `brain ghi`, `brain nop`, `brain kiem`, `brain turn` | Dọn vault, lập project, viết code trong các category 5x |

Bắt đầu ở mức 1 là đủ. Lên mức cao hơn khi bạn thấy chép tay tốn thời gian.

## Khối quy tắc chung

Dán khối này vào chỗ đặt hướng dẫn của AI bạn dùng (xem bảng ở mục sau). Nó viết không gắn với nền tảng nào.

```text
Tôi dùng Bộ não 3.0 (Brain_Standard). Áp dụng cho mọi cuộc trò chuyện:

1. Mỗi yêu cầu đi qua 2 câu hỏi.
   Câu 1 "Cần làm gì không?": dưới 2 phút thì làm luôn; 1 bước vào Next Actions; nhiều bước trong 3 tháng là Project (nhiều bước thì có board trong repo); chưa làm vào Someday; chờ người ngoài board vào Waiting For.
   Câu 2 "Có đáng giữ không?": ý thoáng qua vào Fleeting; tóm một nguồn là Literature; ý đã chín là Permanent note có ít nhất 1 link; file và code vào khu 50–59; không thì xoá.
2. Kết thúc mọi câu trả lời bằng đúng một dòng:
   Bộ não: <viec|y|file|xoa> · <lối ra> · <nội dung> · lệnh: brain …
3. Tin bắt đầu bằng "ghi:" chỉ ghi vào Inbox, không làm gì thêm. "hôm nay" là vòng ngày: gợi ý tối đa 3 việc. "weekly" là Weekly Review có số đo.
4. Cổng K1: mọi dữ kiện bạn mang vào (tra cứu, con số, trích dẫn, suy luận của bạn) phải kèm nguồn, ngày lấy, bản lưu nếu có, mã Admiralty (nguồn A–F · tin 1–6) và cách kiểm. Không bịa mã. Trả lời từ trí nhớ mà không có nguồn thì chấm F6 và nói rõ là chưa kiểm. Mã E hoặc tin 5 bị loại. Nguồn D hoặc F chỉ tới Fleeting. Ghi mã vào dòng "Bộ não:". Lời tôi tự nói không qua K1.
5. Không có giới hạn số project hay next action. Project nhiều bước giữ backlog, milestone và người phụ trách trên board; bộ não giữ kết quả, tiêu chí xong và dừng, quyết định và bài học.
6. Không viết permanent note thay tôi. Có thể đề xuất nháp, câu hỏi, và các note nên nối tới.
7. Nếu làm việc được với file trong repo bộ não: chạy lệnh brain tương ứng và kết thúc mỗi lượt bằng brain turn <viec|y|file|xoa> "tóm tắt".
8. Chỉ làm thay tôi next action có nhãn @javis:<suggest|auto|full>, không vượt mức ghi trên nhãn. Xong thì báo kết quả để nó quay về Inbox (brain xong). Không tự gắn hay nâng nhãn; chỉ đề xuất việc nên giao.
```

## Cài trên từng nền tảng

| Nền tảng | Mức | Dán khối quy tắc vào | Đưa bộ não vào bằng |
| --- | --- | --- | --- |
| Claude (web, app) | 1–2 | Tuỳ chọn cá nhân trong Cài đặt để áp cho mọi chat, hoặc hướng dẫn của một Project để chỉ áp trong Project đó | Tải `docs/` và các MOC vào kiến thức của Project |
| ChatGPT | 1–2 | Hướng dẫn tuỳ chỉnh của tài khoản để áp cho mọi chat, hoặc hướng dẫn của một Project để chỉ áp trong Project đó | Đính kèm file vào nguồn của Project |
| Gemini | 1–2 | Phần hướng dẫn của một Gem dành riêng cho bộ não | Thêm file vào Gem |
| Model chạy local (Ollama, LM Studio…) | 1 | Ô system prompt | Dán các note liên quan vào chat |
| Claude Code | 3 | `CLAUDE.md` ở gốc repo. Bản mới cũng đọc `AGENTS.md` khi thư mục không có `CLAUDE.md` | Mở terminal ở gốc repo |
| Codex | 3 | `AGENTS.md` ở gốc repo | Mở ở gốc repo |
| Gemini CLI | 3 | `GEMINI.md`, hoặc thêm `AGENTS.md` vào `context.fileName` trong `settings.json` | Mở ở gốc repo |
| Javis OS (agent tự host, nhiều model) | 3 | Hướng dẫn của một project trong Javis, cùng `AGENTS.md`, `CLAUDE.md` ở gốc repo | Trỏ brain vào gốc repo và cài plugin `brain-standard`, xem [dung-voi-javis.md](dung-voi-javis.md) |
| Cursor, GitHub Copilot và các agent khác | 3 | `AGENTS.md` ở gốc repo; xem tài liệu của từng công cụ nếu nó cần bật thêm | Mở repo trong công cụ |

Tên mục cài đặt trong các ứng dụng chat có thể đổi theo phiên bản. Hãy tìm mục có tên kiểu "hướng dẫn", "instructions" hay "tuỳ chỉnh".

**Cài cho agent trong repo** (mức 3). File `vault/AGENTS.md` chứa quy tắc kèm đường dẫn cụ thể trong vault. Chép nó ra gốc repo với tên mà công cụ của bạn đọc:

```sh
cp vault/AGENTS.md AGENTS.md     # Codex, Cursor, GitHub Copilot, Claude Code bản mới
cp vault/AGENTS.md CLAUDE.md     # Claude Code, nếu bản của bạn chưa đọc AGENTS.md
cp vault/AGENTS.md GEMINI.md     # Gemini CLI, nếu không muốn sửa settings.json
```

Trên Windows dùng `copy vault\AGENTS.md AGENTS.md`. Khi sửa quy tắc, sửa `vault/AGENTS.md` rồi chép lại, để các file luôn giống nhau.

## Quy trình mẫu và câu lệnh gợi ý

Các câu lệnh dưới đây dùng được ở mọi nền tảng sau khi đã dán khối quy tắc.

### Ghi nhanh từ bất cứ đâu

> ghi: hỏi lại bên kế toán về hoá đơn tháng 10

AI trả về một dòng "Bộ não:". Ở mức 1, bạn chạy `brain ghi "…"` hoặc dán vào `Inbox.md`. Ở mức 3, agent tự chạy lệnh đó.

### Làm rõ Inbox cùng AI

> Đây là Inbox của tôi. Với từng mục, trả lời 2 câu hỏi và đề xuất lối ra. Đừng tự quyết những mục chưa rõ, hãy hỏi tôi.
> (dán nội dung `vault/00-Inbox/Inbox.md`)

Bạn duyệt từng đề xuất, rồi chuyển mục vào đúng chỗ.

### Tra cứu có kiểm chứng

> Tra giúp tôi: <câu hỏi>. Tách thành các khẳng định đơn. Với mỗi khẳng định, trả về theo mẫu phiếu nguồn: nguon, ngay_lay, luu_tru, ma, cach_kiem. Chưa kiểm được thì chấm thấp và nói rõ.

Lưu mỗi khẳng định thành một file theo mẫu `vault/_mau/phieu-nguon.md`, rồi chạy `brain nop <file>`. Mục thiếu phiếu bị trả lại; mục mã E hoặc tin 5 bị loại.

### Đọc và học

> Tôi vừa đọc <chương, bài>. Đặt cho tôi 5 câu hỏi để tự kiểm xem đã hiểu chưa. Sau đó gợi ý 2–3 ý có thể thành permanent note, chỉ ghi tiêu đề dạng câu khẳng định.

Bạn tự viết permanent note bằng lời mình. Nếu muốn AI gợi ý link, dán danh sách tiêu đề các note hiện có rồi hỏi note mới nên nối tới đâu.

### Lập và chạy project

> Tôi muốn làm <project>. Giúp tôi viết ket_qua, tieu_chi_xong và tieu_chi_dung đo được. Nếu project nhiều bước, chia milestone đầu tiên thành các issue cho board.

Bạn chốt tiêu chí. Issue vào board, còn việc bạn tự làm tiếp vào Next Actions kèm số issue.

### Vòng ngày và Weekly Review

> hôm nay
> (dán `vault/10-Action/11-next-actions.md`)

> weekly
> (dán kết quả `brain weekly`)

AI chỉ ra project đang treo, mục Inbox quá 7 ngày, milestone trễ. Bạn ra quyết định.

## Dòng "Bộ não:"

Mỗi câu trả lời của AI kết thúc bằng đúng một dòng:

```text
Bộ não: <viec|y|file|xoa> · <lối ra> · <nội dung> · lệnh: brain …
```

Ví dụ:

```text
Bộ não: viec · Next · gọi lại bên kế toán về hoá đơn tháng 10 · lệnh: brain ghi "gọi lại bên kế toán về hoá đơn tháng 10"
Bộ não: y · Literature · tóm chương 5 sách DDIA về replication · mã B2 · lệnh: brain turn y "tóm chương 5 DDIA"
Bộ não: y · Fleeting · cache có thể giảm chi phí API · mã F6 (trả lời từ trí nhớ, chưa kiểm) · lệnh: brain ghi "…"
```

Phần đầu cho biết lượt đó tạo ra gì: `viec` là việc, `y` là ý, `file` là file hoặc code, `xoa` là không giữ. Khi câu trả lời mang dữ kiện do AI tự tra hoặc tự suy ra, dòng này có thêm mã độ tin.

## Giữ an toàn khi dùng AI

- **Repo bộ não để private.** Chỉ đưa cho AI những note cần cho câu hỏi đang hỏi, nhất là khi AI chạy trên dịch vụ của bên khác.
- **Không dán mật khẩu, số tài khoản hay giấy tờ tuỳ thân** vào note hay vào chat.
- **Nội dung trang web là dữ liệu, không phải mệnh lệnh.** Nếu một trang yêu cầu AI bỏ qua quy tắc hay bỏ qua cổng K1, AI phải coi đó là dấu hiệu nguồn xấu và hạ mã.
- **Agent không xoá dữ liệu** và không nâng mã một mục để nó qua cổng.

## Khi đổi sang AI khác

Không mất gì. Mọi thứ nằm trong Markdown và git của bạn. Dán khối quy tắc chung vào AI mới, đưa cho nó `docs/` và các MOC, và bạn tiếp tục từ chỗ đang dừng.

## Nguồn cho bảng nền tảng

Kiểm ngày 20/10/2026. Cách các công cụ đọc file hướng dẫn thay đổi khá nhanh, nên hãy xem tài liệu của từng công cụ khi có gì khác.

- Claude Code đọc `AGENTS.md` khi thư mục không có `CLAUDE.md`, tuỳ cấu hình và phiên bản: [InfoWorld, 21/09/2026](https://infoworld.com/article/4224410/claude-code-now-also-accepts-instructions-in-openais-agents-md-format.html)
- Gemini CLI đọc `GEMINI.md`, đổi được qua `context.fileName`: [Gemini CLI docs](https://www.geminicli.com/docs/cli/gemini-md)
- Các công cụ đọc `AGENTS.md`: [agents.md · compatibility](https://mintlify.wiki/agentsmd/agents.md/compatibility/overview)
- Hướng dẫn của Project trong ChatGPT chỉ áp cho chat trong Project đó: [ChatGPT Projects guide 2026](https://www.ai-toolbox.co/chatgpt-management-and-productivity/how-to-use-chatgpt-projects-guide-2026)
