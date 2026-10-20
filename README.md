# Brain_Standard · Bộ não 2.2

Một bộ não thứ hai bạn tự sở hữu: các file Markdown trong một repo git, một bộ luật để mọi thứ có chỗ của nó, và một bộ quy tắc để bất kỳ AI nào cũng làm việc được với nó.

**Phiên bản 2.2.1** · 20/10/2026 · [Change log](CHANGELOG.md)

**Mới tới đây? Đọc [Hướng dẫn dùng bộ não](docs/huong-dan.md)**: cài đặt, ngày đầu tiên trong 30 phút, nhịp ngày và tuần. Muốn dùng với AI thì đọc [Dùng bộ não với AI](docs/dung-voi-ai.md).

## Bộ não dùng để làm gì

Đầu óc là chỗ để nghĩ, không phải chỗ để chứa. Bộ não này nhận phần chứa, để đầu bạn rảnh cho phần nghĩ. Nó giải quyết năm vấn đề quen thuộc:

| Vấn đề | Bộ não xử lý thế nào |
| --- | --- |
| Việc, ý và link rơi rớt khắp nơi: chat, ghi chú điện thoại, tab trình duyệt, trong đầu | Mọi thứ vào **một Inbox duy nhất**. Mỗi mục được trả lời hai câu hỏi rồi đi vào đúng một chỗ. Không gì bị bỏ quên. |
| Đọc nhiều mà không nhớ, kiến thức không thành của mình | **Làn tri thức**: tóm nguồn bằng lời mình, chưng thành note một ý, nối các note với nhau, rồi ôn bằng thẻ để nhớ lâu. |
| Nhiều dự án dở dang, không rõ bước tiếp theo, không biết khi nào nên dừng | **Làn hành động**: mỗi project có kết quả, tiêu chí xong và tiêu chí dừng; mỗi việc là một bước cụ thể. Project nhiều bước có board riêng với milestone và người phụ trách. |
| File, script, log nằm lung tung, tìm lại không ra | **Làn file và code**: mỗi thứ một địa chỉ số cố định, ví dụ `51.03`, ghi chú chỉ cần trỏ tới số. |
| Dùng AI nhiều nhưng AI quên giữa các cuộc chat, đôi khi bịa, và mỗi nền tảng một kiểu | Bộ não là **trí nhớ bền nằm ở chỗ của bạn**, không khoá vào hãng nào. **Cổng kiểm duyệt** buộc mọi dữ kiện AI mang về có nguồn và mã độ tin. Một bộ quy tắc dùng cho mọi AI. |

### Hợp với ai

- **Người tự học dài hạn**, như học một ngoại ngữ hay một chuyên ngành trong nhiều năm: đọc thành literature note, nghĩ thành permanent note, ôn bằng thẻ.
- **Người làm nhiều project cá nhân hoặc side project**: thấy rõ project nào đang chạy, project nào đang treo, và rút được bài học khi xong.
- **Người nghiên cứu cần thông tin có kiểm chứng**: mỗi khẳng định có phiếu nguồn, mã độ tin, hạn dùng, và được kiểm lại hằng tháng.
- **Người làm việc với nhiều AI**, như Claude, ChatGPT, Gemini, hay các agent viết code: một trí nhớ chung, đổi AI không mất gì.

### Chưa hợp khi

- Bạn cần một không gian ghi chú cho cả nhóm cùng sửa theo thời gian thực. Bộ não này thiết kế cho một người; phần làm nhóm nằm ở board của từng project.
- Bạn không muốn đụng tới git hay dòng lệnh. Vẫn dùng tay được với các file Markdown, nhưng bạn sẽ mất phần CLI tự kiểm lỗi và đóng lượt.

### Nguyên tắc

1. **Bạn sở hữu dữ liệu.** Chỉ là Markdown và git: mở bằng trình soạn nào cũng được, sao lưu ở đâu cũng được.
2. **AI là trợ lý, không phải tác giả.** AI giúp làm rõ, tra cứu, viết nháp. Permanent note, nơi giữ suy nghĩ của bạn, luôn do bạn viết bằng lời mình.
3. **Không tin AI vô điều kiện.** Dữ kiện AI mang về phải qua cổng K1. Mã độ tin quyết định nó được đi tới đâu: chỉ là ý thoáng qua, thành tóm tắt nguồn, hay đủ chắc để học thuộc.
4. **Đo thay vì cấm.** Không giới hạn số project hay số việc. Weekly Review đo để bạn tự thấy khi mình ôm quá nhiều.

## Dùng với AI

Bộ não có một khối quy tắc chung, dán được vào bất kỳ AI nào. Từ đó, AI làm việc theo cùng một cách dù bạn đang ở nền tảng nào:

- Mỗi yêu cầu được đi qua hai câu hỏi, và mỗi câu trả lời kết thúc bằng một dòng `Bộ não: …` cho biết mục đó đi vào làn nào.
- Tin nhắn bắt đầu bằng `ghi:` chỉ để ghi; `hôm nay` chạy vòng ngày; `weekly` chạy Weekly Review.
- Dữ kiện AI tự tra hay tự suy ra phải kèm mã độ tin. AI không được bịa mã.

| Mức | AI làm được gì | Ví dụ nền tảng |
| --- | --- | --- |
| 1 · Chat | Trả lời và đề xuất; bạn chép vào bộ não | Claude, ChatGPT, Gemini, model chạy local |
| 2 · Chat có tài liệu | Trả lời dựa trên các note bạn đưa vào | Project của Claude hoặc ChatGPT, Gem của Gemini |
| 3 · Agent trong repo | Đọc, ghi file và tự chạy lệnh `brain` | Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot |

Cách cài trên từng nền tảng, quy trình mẫu và câu lệnh gợi ý: [docs/dung-voi-ai.md](docs/dung-voi-ai.md).

## Dòng chảy

```mermaid
flowchart TD
  T["Lời bạn: ghi tay, nói, gõ"] --> IN["Inbox · nơi thật duy nhất"]
  AG["AI hoặc agent tra cứu: web, paper, API"] --> K1{{"K1 · phiếu nguồn, mã A–F · 1–6"}}
  K1 -- "đạt" --> IN
  K1 -- "nguồn E hoặc tin 5" --> LOG["_log"]
  IN --> Q1{"Cần làm gì không?"}
  Q1 -- "có" --> HD["Làn hành động · GTD + PARA"]
  Q1 -- "không" --> Q2{"Có đáng giữ không?"}
  Q2 -- "ý" --> TT["Làn tri thức · Zettelkasten + LYT + FSRS"]
  Q2 -- "file, code" --> FC["Làn file và code · Johnny Decimal"]
  Q2 -- "không" --> X["Xoá"]
  HD -- "project nhiều bước" --> BD["Board trong repo · backlog, milestone, người"]
  HD --> TR["Tạo ra: sản phẩm, quyết định, code"]
  TT --> TR
  FC --> TR
```

Ba làn trao đổi với nhau qua 7 đường I1–I7, mô tả ở [docs/dong-chay.md](docs/dong-chay.md).

## Trong gói có gì

| Đường dẫn | Là gì |
| --- | --- |
| `docs/huong-dan.md` | Hướng dẫn từng bước cho người mới |
| `docs/dung-voi-ai.md` | Dùng bộ não với AI trên nhiều nền tảng |
| `docs/dong-chay.md` | Inbox, hai câu hỏi, ba làn, 7 đường nối, nhịp ngày, tuần, tháng |
| `docs/ba-lan.md` | Luật, số đo và dấu hiệu hỏng của từng làn |
| `docs/kiem-duyet.md` | Cổng K1–K4, hệ mã Admiralty, phiếu nguồn, 10 bước tra cứu |
| `docs/tang-thuc-thi.md` | Tầng thực thi 2.2: board, milestone, người phụ trách |
| `vault/` | Khung thư mục và mẫu file để bắt đầu một bộ não mới |
| `vault/AGENTS.md` | Quy tắc cho agent làm việc trong repo |
| `brain.toml` | Cấu hình chuẩn 2.2 |
| `tools/brain.py`, `bin/brain` | CLI: `ghi`, `nop`, `kiem`, `turn`, `weekly` |
| `tests/` | Test cho CLI |

## Bắt đầu nhanh

Cần Python 3.11 trở lên và git. Bộ não chứa ghi chú cá nhân, nên hãy tạo một repo **private** từ gói này. Các bước đầy đủ nằm trong [hướng dẫn](docs/huong-dan.md).

```sh
git clone https://github.com/DaveTran243/Brain_Standard.git bo-nao-cua-toi
cd bo-nao-cua-toi
bin/brain kiem                                   # Windows: bin\brain.cmd kiem
bin/brain ghi "Đọc chương 5 sách DDIA"
bin/brain turn y "ghi ý đầu tiên vào Inbox"
```

## Lệnh

| Lệnh | Việc |
| --- | --- |
| `brain ghi "…"` | Ghi lời bạn vào Inbox. Lời bạn không đi qua K1. |
| `brain nop file.md` | Nộp một mục do AI hoặc agent mang về qua cổng K1. Thiếu phiếu nguồn thì bị trả lại. |
| `brain kiem` | Rà vault theo luật 2.2 và các cổng K2–K3. |
| `brain turn <viec\|y\|file\|xoa> "tóm tắt"` | Đóng một lượt làm việc. Vault còn lỗi thì lượt không đóng được. |
| `brain weekly [--ghi]` | Tính số đo cho Weekly Review. |

## Luật cốt lõi

- Mọi thứ vào một Inbox trước khi phân loại. Mỗi mục đi vào đúng một làn.
- Permanent note chỉ chứa một ý, viết bằng lời của bạn, và nối tới ít nhất một note cũ.
- Mỗi project ghi tiêu chí xong và tiêu chí dừng ngay khi lập. Project nhiều bước có board riêng.
- Dữ kiện do AI hoặc agent mang về phải có phiếu nguồn và mã độ tin. Mã quyết định nó được đi xa tới đâu.
- Mỗi lượt làm việc kết thúc bằng `brain turn`.
- Không có giới hạn số project hay next action. Weekly Review đo để bạn tự nhìn thấy khi ôm quá nhiều.
