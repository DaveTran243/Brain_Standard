# Change log

Số phiên bản theo dạng x.y.z: x tăng khi dòng chảy chính đổi hình, y tăng khi thêm cơ chế mà không phá dòng chảy, z cho sửa số liệu, nhãn và câu chữ. Bản mới nhất ở trên cùng.

## Chưa phát hành

Tài liệu. Luật và CLI không đổi cách chạy.

### Thêm
- `docs/kien-truc-he-thong.md`: tài liệu kiến trúc hệ thống (DAB) chuẩn hoá theo arc42, gồm yêu cầu và ca sử dụng, mục tiêu chất lượng, ràng buộc, bối cảnh, khối xây dựng, đặc tả từng lệnh, triển khai, mô hình dữ liệu, ngữ pháp các dòng, danh mục luật kiểm có mã, tham chiếu cấu hình, mã thoát, mô hình mối đe doạ, ma trận truy vết test, 9 ADR, kịch bản chất lượng, 13 rủi ro và nợ kỹ thuật.
- Thiết kế đề xuất cho 2.3: tầng truy hồi với chỉ mục SQLite (FTS5 + sqlite-vec), embeddings local, lệnh `brain index`, `brain tim`, `brain mcp` và MCP server chỉ ghi qua cổng K1; kèm lược đồ SQL, thuật toán index và xếp hạng theo độ tin, schema tool MCP, ngân sách hiệu năng, kế hoạch kiểm thử và tiêu chí nghiệm thu.

## 2.2.1 · 20/10/2026

Tài liệu. Luật và CLI không đổi cách chạy.

### Thêm
- README có mục "Bộ não dùng để làm gì": vấn đề giải quyết, hợp với ai, chưa hợp khi nào, nguyên tắc.
- `docs/dung-voi-ai.md`: dùng bộ não với AI trên nhiều nền tảng, gồm ba mức kết nối, khối quy tắc chung, cách cài trên Claude, ChatGPT, Gemini, model local và các agent trong repo, quy trình mẫu kèm câu lệnh gợi ý.
- `docs/huong-dan.md`: hướng dẫn từng bước cho người mới.

### Đổi
- `docs/quy-uoc-claude.md` → `docs/dung-voi-ai.md`, viết lại cho mọi nền tảng.
- `vault/CLAUDE.md` → `vault/AGENTS.md`, viết lại cho mọi agent. Chép ra gốc repo với tên `AGENTS.md`, `CLAUDE.md` hoặc `GEMINI.md` tuỳ công cụ.

## 2.2.0 · 20/10/2026

Tầng thực thi, bỏ giới hạn. Bộ não giữ vai điều phối, còn phần thực thi của project nhiều bước chuyển xuống board trong repo. Dòng chảy chính không đổi.

### Thêm
- Tầng thực thi: mỗi project nhiều bước có một board (ví dụ GitHub Projects) trong repo của category, giữ backlog, issue, milestone, hạn và người phụ trách.
- Project file thêm các trường `repo`, `board`, `milestone`, `han`, `nguoi` và mục `## Quyết định`.
- Weekly Review đo thêm số project active, issue mở và đóng theo board, milestone trễ hạn. Chỉ đo, không chặn.
- CLI `brain` với các lệnh `ghi`, `nop`, `kiem`, `turn`, `weekly`.

### Đổi
- I1: xong việc hoặc đóng project → thêm mỗi lần xong milestone.
- I3: project có file đầu tiên thì mở category → lập project nhiều bước thì mở category, repo và board ngay.
- I6: mọi lỗi trong log thành next action → lỗi thường thành issue trên board; chỉ issue giao cho bạn hoặc lỗi chặn cả project mới thành next action.
- Waiting For: mọi việc chờ người khác → chỉ việc chờ bên ngoài board.
- Làn file: repo GitHub một repo mỗi category → repo kèm board.

### Bỏ
- Tối đa 3 project active, cùng bước "Còn chỗ?" khi lập project.
- Đúng 1 next action cho mỗi project.
- Tối đa 20 next action.
- Mục `[gioi_han]` trong `brain.toml` và phần kiểm tra các giới hạn này trong `brain turn`.

### Giữ
- Vòng ngày chọn tối đa 3 việc mỗi sáng. Đây là nhịp làm việc, không chặn việc ghi.
- Fleeting giữ tối đa 7 ngày; MOC khi một cụm có khoảng 7 note; tối đa 10 category trong khu 50–59.

## 2.1.0 · 01/10/2026

Cổng kiểm duyệt. Thông tin do agent mang về phải có nguồn và được chấm độ tin trước khi thành ghi chú hay thẻ ôn. Dòng chảy chính không đổi.

### Thêm
- Nguồn vào "Agent tra cứu": mọi dữ kiện agent mang về từ web, paper, API, kể cả dữ kiện Claude ghi theo lệnh "ghi:".
- Cổng K1 trước Inbox, chặn cứng: mục từ agent phải có phiếu nguồn. Thiếu phiếu thì trả lại agent. Ý bạn tự ghi không đi qua K1.
- Chấm hai trục theo hệ Admiralty: nguồn A–F, thông tin 1–6. Nguồn E hoặc tin 5 bị loại và ghi vào `_log`; nguồn D hoặc F chỉ đi tới Fleeting.
- Quy trình tra cứu 10 bước cho agent, dựa trên SIFT và đọc ngang.
- Cổng K2 (literature cần nguồn A–C và bản lưu), K3 (permanent cần tin 1–2), K4 (thẻ ôn cần tin 1–2, thêm hạn dùng nếu là số liệu).
- Kiểm lại mỗi tháng 10 khẳng định ngẫu nhiên trong permanent và bản đồ tri thức.
- Đường I7 · đính chính: khẳng định sai thành việc sửa note, thẻ hoặc node bản đồ.
- Weekly Review đo thêm: % mục thiếu phiếu, số khẳng định bị bác, số link chết, số mục quá hạn dùng.

### Đổi
- Nhãn độ tin cũ đổi sang mã: `web` → B2, `solid` → C2, `verify` → C3.

### Tạm dừng
- Ôn các thẻ mã C3 cho tới khi kiểm lại từng thẻ. Thẻ đạt tin 1–2 thì ôn tiếp; thẻ không đạt rời bộ thẻ, khẳng định sai đi đường I7.

## 2.0.0 · 30/09/2026

Inbox → 2 câu hỏi → 3 làn. Dòng chảy chính đổi hình nên đây là bản lớn.

### Thêm
- Bộ não thành code và CLI trong một repo riêng chứa cả mã lẫn dữ liệu.
- Mỗi lượt làm việc với Claude kết thúc bằng `brain turn`.
- Câu hỏi thứ hai "Có đáng giữ không?" và lối Xoá.
- Vòng ngày 30–45 phút: chọn tối đa 3 việc, làm ít nhất 1 việc, ôn 15–20 thẻ, ghi ý mới vào Inbox.
- Fleeting (giữ tối đa 7 ngày), literature note, và MOC khi một cụm có khoảng 7 note.
- Sáu đường I1–I6 nối ba làn.
- Tiêu chí xong và tiêu chí dừng cho mỗi project; Archive ghi lý do dừng.
- Quy ước tin nhắn "ghi:", "hôm nay", "weekly", và dòng "Bộ não:" cuối mỗi câu trả lời của Claude.
- Giới hạn: tối đa 3 project active, đúng 1 next action mỗi project, tối đa 20 next action (bỏ ở 2.2.0).

### Đổi
- Inbox: hai nơi đồng bộ tay → một nơi thật duy nhất; Inbox đám mây chảy một chiều mỗi tuần.
- Làm rõ: một câu hỏi "Có hành động được không?" → hai câu hỏi.
- Areas sinh một project mỗi quý; Someday được rà mỗi tuần.
- Routine export chạy mỗi tuần, chỉ ghi khi có dữ liệu mới; trạng thái máy ghi vào `_log`.
- Johnny Decimal chỉ dùng cho code và file, ở khu 50–59; tên ghi chú không mang mã AC.ID.
- Weekly Review: 30 phút, đo thẻ đã ôn, việc xong, note mới và tỉ lệ sửa hệ thống : nội dung = 1:3.
- Resources.md đổi thành literature notes.

### Bỏ
- Memory của Claude khỏi nguồn vào, vì nó chỉ rút lại từ chat.

### Tạm dừng
- Hạ tầng agent nhiều persona: mở lại khi một project cần tool hoặc quyền thật.

## 1.0.0 · 28/09/2026

Hiện trạng ban đầu. Sáu bước: nguồn vào → capture → làm rõ → tổ chức → chưng cất và nhớ → tạo ra. Một câu hỏi làm rõ "Có hành động được không?". Ba làn: hành động (GTD + PARA), tri thức (Zettelkasten + LYT + FSRS), file và code (Johnny Decimal). Inbox ở hai nơi, đồng bộ bằng tay.
