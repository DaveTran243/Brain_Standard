# Ba làn

Sau bước làm rõ, mỗi mục chỉ đi vào đúng một làn. Mỗi làn trả lời một câu hỏi khác nhau và giữ kho riêng. Dữ liệu sang làn khác qua một trong 7 đường I1–I7.

## 1 · Làn hành động · GTD + PARA

Biến ý định thành việc đã làm xong. GTD lo chuỗi quyết định (một bước hay nhiều bước, làm ngay, để sau hay giao đi) và vòng làm hằng ngày. PARA lo ranh giới: cái gì có điểm kết thúc (Projects), cái gì phải duy trì mãi (Areas), và khi nào cất vào Archive.

- **Câu hỏi lõi:** Bước tiếp theo, cụ thể, là gì?
- **Vào:** việc từ Inbox, I2 ý thành việc, I4 toa đọc, I6 issue của bạn, I7 đính chính, Area sinh project mỗi quý.
- **Ra:** việc xong, Archive có ghi lý do, I1 bài học, I3 mở category và board.
- **Vòng đời project:** Someday → Active → Xong hoặc Dừng → Archive.

### Quy tắc
1. Tiêu chí xong và tiêu chí dừng ghi ngay khi lập project.
2. Project nhiều bước có board trong repo của nó; backlog, milestone, hạn và người phụ trách nằm trên board. Xem [tầng thực thi](tang-thuc-thi.md).
3. Next action bắt đầu bằng động từ và làm xong trong một lần ngồi, tối đa 90 phút.
4. Next action của project ghi kèm `[[project]]` và số issue nếu có.
5. Waiting For chỉ cho việc chờ bên ngoài board. Việc giao trong project thì gán người phụ trách trên board.
6. Không giới hạn số project hay số next action (từ 2.2.0).

### Đo mỗi tuần
- Số việc đã xong, số project active, số next action đang mở.
- Issue mở và đóng theo từng board, milestone trễ hạn.
- Tuổi của mục cũ nhất trong Inbox, nên dưới 7 ngày.

### Dấu hiệu hỏng
- Project active không có việc nào đang làm, cả trên board lẫn trong Next Actions.
- Next Actions dài tới mức sáng mở ra không biết chọn việc nào.
- Someday không bao giờ được rà, thành bãi rác thứ hai.
- Bạn làm những việc không có trong danh sách: hệ thống đang bị đi vòng qua.

## 2 · Làn tri thức · Zettelkasten + LYT + FSRS

Biến thứ bạn đọc và thứ bạn làm thành hiểu biết của riêng bạn, rồi giữ nó trong trí nhớ. Zettelkasten chưng cất thành note một ý và nối các note với nhau, LYT vẽ bản đồ khi một cụm note đã đủ dày, FSRS lên lịch ôn.

- **Câu hỏi lõi:** Ý này nối với ý nào tôi đã có?
- **Vào:** ý từ Inbox, nguồn đọc, I1 bài học, I5 kết quả chạy thử.
- **Ra:** bài viết và quyết định, I2 ý thành việc, I4 toa đọc, I7 đính chính.
- **Vòng đời một ý:** Fleeting → Literature → Permanent → nằm trong MOC → có thẻ → nhớ thuộc, hoặc xoá sau 7 ngày.

### Quy tắc
1. Viết bằng lời mình, không copy-paste.
2. Mỗi permanent note chỉ chứa 1 ý, tiêu đề là một câu khẳng định.
3. Mỗi permanent note mới nối tới ít nhất 1 note cũ ngay lúc viết.
4. Chỉ tạo MOC khi một cụm có khoảng 7 note.
5. Thẻ ôn chỉ sinh từ permanent note hoặc bản đồ tri thức, không lấy từ nguồn thô.
6. Bản đồ tri thức do AI viết là **nguồn đọc**, không phải permanent note của bạn. Kiến thức chỉ thành của bạn khi bạn tự viết lại.
7. Cổng K2–K4 áp ở cửa literature, permanent và bộ thẻ. Xem [kiểm duyệt](kiem-duyet.md).

### Đo mỗi tuần
- Số permanent note mới, khởi đầu với khoảng 3 note mỗi tuần.
- Số thẻ đã ôn và tỉ lệ nhớ; FSRS mặc định nhắm khoảng 90%.
- Số thẻ quá hạn, nên dưới khoảng 100.

### Dấu hiệu hỏng
- Literature thì nhiều mà permanent thì ít: bạn đang sưu tầm chứ chưa nghĩ.
- Thẻ quá hạn dồn lên hàng trăm.
- Note không có link nào: làn này thành thùng chứa.
- Đọc bản đồ tri thức mà không sinh ra note nào: kiến thức vẫn chưa thành của bạn.

## 3 · Làn file và code · Johnny Decimal

Giữ những thứ không phải ghi chú: script, prompt, config, log chạy, video, file export. Johnny Decimal cấp cho mỗi thứ một địa chỉ số cố định, nên ghi chú và việc chỉ cần viết "xem 51.03".

- **Câu hỏi lõi:** Thứ này nằm ở số nào?
- **Vào:** file từ Inbox, file do công cụ sinh ra, I3 project cần chỗ chứa.
- **Ra:** repo kèm board, I5 số liệu mới, I6 issue và lỗi chặn.
- **Vòng đời một file:** chưa có số → có dòng Index → có thư mục → đang dùng → đã đóng, giữ số.

### Quy tắc
1. Ghi dòng vào Index trước, rồi mới tạo thư mục.
2. Không dùng lại số. Category đã đóng thì đánh dấu và giữ nguyên số.
3. Không lồng thư mục sâu hơn mức AC.ID; 51.03 là tầng cuối có tên.
4. Ghi chú không nằm ở làn này. Note chỉ ghi số để trỏ tới.
5. Mỗi category có code ứng với 1 repo, và repo đó có board nếu project nhiều bước.
6. Khu 50–59, tối đa 10 category; số 10/20/30/40 dành cho thư mục của vault.

### Đo mỗi tuần
- Số file còn nằm ngoài hệ thống (Downloads, Desktop).
- Index có khớp với thư mục thật không.
- Số category đã dùng trên tổng 10.

### Dấu hiệu hỏng
- File vẫn nằm ở Downloads.
- Mở category cho dự án chưa có file thật.
- Index lệch với thư mục: có số trên giấy nhưng không trỏ tới đâu.

Các ngưỡng (7 note, 3 lần quên, 7 ngày, 90 phút) là điểm bắt đầu, nên chỉnh lại sau 4 tuần đo.
