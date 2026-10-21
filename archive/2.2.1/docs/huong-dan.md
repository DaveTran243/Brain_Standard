# Hướng dẫn dùng Bộ não 2.2

Hướng dẫn này dành cho người mới mở repo. Đọc xong và làm theo phần "Ngày đầu tiên", bạn sẽ có một bộ não chạy được trên máy mình trong khoảng 30 phút. Phần dùng với AI nằm ở mục 8.

## 1. Bộ não này là gì

Một hệ thống ghi chép và làm việc dựng trên các file Markdown trong một repo git. Mọi thứ bạn nghĩ, đọc, làm đều vào một **Inbox**. Mỗi mục trong Inbox được trả lời **hai câu hỏi**, rồi đi vào đúng một trong **ba làn**:

| Làn | Chứa gì | Thư mục |
| --- | --- | --- |
| Hành động | Việc cần làm, project, việc chờ người khác | `vault/10-Action/` |
| Tri thức | Ghi chú, tóm tắt sách, ý của riêng bạn | `vault/30-Knowledge/`, `vault/40-Maps/` |
| File và code | Script, log, file xuất ra, mỗi thứ một số cố định | `vault/Coding/` |

Thông tin do AI hay agent tìm về phải có **phiếu nguồn** và **mã độ tin** trước khi vào bộ não. Phần này gọi là cổng kiểm duyệt K1–K4.

Một CLI nhỏ tên `brain` làm bốn việc: ghi nhanh vào Inbox, nộp mục từ agent qua cổng, rà lỗi trong vault, và đóng mỗi lượt làm việc.

Bộ não giải quyết vấn đề gì, hợp với ai và chưa hợp khi nào: xem mục [Bộ não dùng để làm gì](../README.md#bộ-não-dùng-để-làm-gì) trong README.

## 2. Cần chuẩn bị

- **Python 3.11 trở lên.** Kiểm tra bằng `python3 --version`, hoặc `python --version` trên Windows. Không cần cài thêm thư viện nào.
- **Git** và một tài khoản GitHub hoặc nơi lưu git khác, để giữ bộ não ở một repo riêng tư.
- **Một trình soạn Markdown hiểu link `[[...]]`**, ví dụ Obsidian. Trình soạn nào cũng dùng được, nhưng loại hiểu link sẽ giúp bạn đi giữa các ghi chú nhanh hơn.

## 3. Cài đặt

Bộ não của bạn chứa ghi chú cá nhân, nên hãy tạo một repo **riêng tư** từ bộ chuẩn này, đừng ghi thẳng vào Brain_Standard.

macOS, Linux:

```sh
git clone https://github.com/DaveTran243/Brain_Standard.git bo-nao-cua-toi
cd bo-nao-cua-toi
rm -rf .git && git init -b main  # bắt đầu lịch sử của riêng bạn
git add -A && git commit -m "Khởi tạo bộ não từ Brain_Standard 2.2"
```

Windows (PowerShell):

```powershell
git clone https://github.com/DaveTran243/Brain_Standard.git bo-nao-cua-toi
cd bo-nao-cua-toi
Remove-Item -Recurse -Force .git; git init -b main
git add -A; git commit -m "Khởi tạo bộ não từ Brain_Standard 2.2"
```

Tạo một repo private trống trên GitHub, rồi nối và đẩy lên:

```sh
git remote add origin https://github.com/<tên-bạn>/<repo-private>.git
git push -u origin main
```

Kiểm tra CLI chạy được. Lệnh `brain` chạy ở bất kỳ đâu trong repo; nó tự tìm file `brain.toml` ở thư mục gốc.

```sh
bin/brain --version     # in ra: brain 2.2.1
bin/brain kiem          # in ra: Vault sạch.
```

Trên Windows dùng `bin\brain.cmd kiem` hoặc `python tools\brain.py kiem`. Phần còn lại của hướng dẫn viết `brain` cho gọn.

Mở thư mục `vault/` bằng trình soạn Markdown của bạn. Các file có tên bắt đầu bằng `_` là **mẫu**: chép ra để dùng, đừng sửa thẳng. `brain kiem` bỏ qua các file này.

## 4. Ngày đầu tiên · khoảng 30 phút

### Bước 1 · Đổ hết vào Inbox (5 phút)

Ghi ra mọi thứ đang nằm trong đầu, mỗi thứ một lệnh. Đừng phân loại vội.

```sh
brain ghi "Gọi lại cho anh Minh về hợp đồng"
brain ghi "Đọc chương 5 sách Designing Data-Intensive Applications"
brain ghi "Ý tưởng: dùng cache để giảm chi phí gọi API"
brain ghi "Làm website cho cửa hàng"
```

Mỗi lệnh thêm một dòng có ngày giờ vào `vault/00-Inbox/Inbox.md`. Bạn cũng có thể gõ thẳng vào file đó.

### Bước 2 · Làm rõ từng mục bằng hai câu hỏi (10 phút)

Lấy từng dòng trong Inbox và hỏi:

**Câu 1 · Cần làm gì không?**

| Nếu | Thì đưa vào |
| --- | --- |
| Làm xong dưới 2 phút | Làm luôn, rồi xoá dòng |
| Một bước là xong | `10-Action/11-next-actions.md` |
| Nhiều bước, làm trong 3 tháng tới | Một project mới trong `10-Action/13-Projects/` |
| Chưa làm bây giờ | `10-Action/14-someday.md` |
| Đang chờ người khác | `10-Action/12-waiting-for.md` |

**Câu 2 · Có đáng giữ không?** (khi câu 1 là "không")

| Nếu | Thì đưa vào |
| --- | --- |
| Một ý thoáng qua | `30-Knowledge/fleeting/`, giữ tối đa 7 ngày |
| Tóm tắt một nguồn đọc | `30-Knowledge/literature/` |
| Một ý đã chín, đứng một mình được | `30-Knowledge/permanent/` |
| File hoặc code | `Coding/`, theo số Johnny Decimal |
| Không | Xoá |

Xong mục nào thì xoá dòng đó khỏi Inbox. Mục tiêu là Inbox về 0.

Một next action viết theo dạng bắt đầu bằng động từ, làm xong trong một lần ngồi:

```markdown
- [ ] Gọi lại cho anh Minh về hợp đồng · @điện-thoại · ~10'
```

### Bước 3 · Lập project đầu tiên (5 phút)

Chép `10-Action/13-Projects/_mau-project.md` thành một file mới, ví dụ `10-Action/13-Projects/website-cua-hang.md`. Điền ba trường bắt buộc:

```yaml
trang_thai: active
ket_qua: "Website bán hàng chạy được, nhận đơn online"
tieu_chi_xong: "Có 10 đơn thật qua website"
tieu_chi_dung: "Sau 6 tuần vẫn chưa có trang chủ"
```

Nếu project chỉ một hai bước, xoá các dòng `repo`, `board`, `milestone`, `han`, `nguoi`, rồi thêm việc đầu tiên vào Next Actions, kèm link tới project:

```markdown
- [ ] Phác 3 trang chính của website · @máy · ~45' · [[website-cua-hang]]
```

Nếu project nhiều bước, xem phần 7 để gắn board.

### Bước 4 · Viết một permanent note (5 phút)

Chép `30-Knowledge/permanent/_mau-permanent.md` thành một file mới. Đặt `id` là thời điểm viết theo dạng `YYYYMMDDHHMM`. Tiêu đề là **một câu khẳng định**, phần thân viết bằng lời của bạn, và phải có **ít nhất một link** tới note khác:

```markdown
---
id: 202610201430
loai: permanent
---

# Cache làm giảm chi phí API khi nhiều người hỏi cùng một câu

Nếu câu hỏi lặp lại nhiều, lưu sẵn câu trả lời rẻ hơn gọi lại API. Không đáng làm khi câu hỏi gần như không bao giờ trùng.

Liên quan: [[ten-note-khac]]
```

### Bước 5 · Kiểm tra và đóng lượt (2 phút)

```sh
brain kiem
brain turn viec "dọn Inbox lần đầu, lập project website"
git add -A && git commit -m "Ngày đầu" && git push
```

`brain kiem` báo **lỗi** khi có thứ sai luật, ví dụ permanent note chưa có link hay project thiếu tiêu chí. Nó báo **cảnh báo** khi có thứ nên xem lại, ví dụ fleeting đã quá 7 ngày. `brain turn` ghi lượt vào `_log/turns.md`, nhưng sẽ không đóng lượt khi vault còn lỗi.

Phần `viec` trong lệnh `turn` cho biết lượt này chủ yếu tạo ra gì: `viec` (việc), `y` (ý), `file`, hoặc `xoa`.

## 5. Mỗi ngày · 30–45 phút

1. Mở Next Actions, chọn **tối đa 3 việc** cho hôm nay.
2. Làm **ít nhất 1 việc** thật.
3. Ôn 15–20 thẻ, nếu bạn dùng thẻ ôn (FSRS, ví dụ Anki).
4. Ghi ý mới vào Inbox bằng `brain ghi`.
5. Kết thúc bằng `brain turn <loại> "tóm tắt"`, rồi commit.

## 6. Mỗi Chủ nhật · Weekly Review 30 phút

```sh
brain weekly --ghi
```

Lệnh này in bảng số đo và lưu vào `vault/weekly/<năm>-W<tuần>.md`. Sau đó đi qua danh sách trong `vault/weekly/_mau-weekly.md`:

- Dọn Inbox về 0. Fleeting quá 7 ngày thì nâng lên literature hoặc xoá.
- Rà từng project và board: project nào không có việc gì đang làm, milestone nào trễ.
- Rà Someday, Areas, Waiting For. Đối chiếu Index trong `Coding/` với thư mục thật.
- Ghi lại các quyết định trong tuần.

Không có giới hạn số project hay next action. Các con số trong Weekly chỉ để bạn tự thấy khi mình đang ôm quá nhiều.

Mỗi tháng, lấy ngẫu nhiên 10 khẳng định trong permanent note để kiểm lại. Thấy sai thì tạo một next action để sửa.

## 7. Project nhiều bước · board trong repo

Từ bản 2.2, project nhiều bước giữ phần thực thi trên một board. Bộ não chỉ giữ phần điều phối.

1. Ghi một dòng vào `Coding/50 He thong/50.00 Index (JDex).md` **trước**, ví dụ `51 Website cua hang`.
2. Tạo thư mục `Coding/51 Website cua hang/` và một repo cho code của project.
3. Tạo một board, ví dụ GitHub Projects, gắn với repo đó. Chia milestone đầu tiên.
4. Điền vào project file: `code: 51`, `repo`, `board`, `milestone`, `han`, `nguoi`.
5. Backlog, issue, lỗi và người phụ trách nằm trên board. Next Actions chỉ giữ việc **bạn** làm tiếp, kèm số issue:

```markdown
- [ ] Sửa lỗi giỏ hàng · ~60' · [[website-cua-hang]] · #12
```

6. Xong mỗi milestone, viết 1 bài học thành permanent note và ghi milestone kế tiếp vào project file.
7. Xong hoặc dừng project: đổi `trang_thai` thành `done` hoặc `stopped`. Nếu dừng thì thêm `ly_do_dung`. Sau đó chuyển file vào `vault/90-Archive/`.

Chi tiết: [tang-thuc-thi.md](tang-thuc-thi.md).

## 8. Dùng với AI

Bộ não dùng được với mọi AI: Claude, ChatGPT, Gemini, model chạy local, và các agent viết code. Trang [Dùng bộ não với AI](dung-voi-ai.md) có cách cài trên từng nền tảng, quy trình mẫu và câu lệnh gợi ý. Bản ngắn:

1. **Dán khối quy tắc chung** trong [dung-voi-ai.md](dung-voi-ai.md#khối-quy-tắc-chung) vào chỗ đặt hướng dẫn của AI bạn dùng: tuỳ chọn cá nhân, hướng dẫn của Project, Gem, hay ô system prompt.
2. **Với agent làm việc trong repo**, chép `vault/AGENTS.md` ra thư mục gốc. Codex, Cursor, GitHub Copilot và Claude Code đọc được file này; Gemini CLI cần chỉnh một dòng cấu hình.
3. Từ đó, mỗi câu trả lời của AI kết thúc bằng một dòng "Bộ não:" cho biết mục đó đi vào làn nào. Bạn dùng được các lệnh:

| Gõ | AI làm |
| --- | --- |
| `ghi: …` | Chỉ ghi vào Inbox |
| `hôm nay` | Chạy vòng ngày |
| `weekly` | Weekly Review có số đo |

**Khi AI mang dữ kiện về:** agent viết một file có phiếu nguồn theo mẫu `vault/_mau/phieu-nguon.md`, rồi nộp qua cổng K1:

```sh
brain nop ket-qua-tra-cuu.md
```

| Kết quả | Nghĩa |
| --- | --- |
| `K1 đạt` (mã thoát 0) | Mục vào `00-Inbox/agent/`, kèm giới hạn nó được đi tới đâu |
| `K1 trả lại` (mã thoát 2) | Thiếu trường bắt buộc hoặc mã sai dạng; bổ sung rồi nộp lại |
| `K1 loại` (mã thoát 3) | Nguồn E hoặc tin 5; chỉ ghi vào `_log/k1.md` |

Mã gồm một chữ cho độ tin của nguồn (A tốt nhất, F chưa đánh giá) và một số cho độ tin của thông tin (1 đã xác nhận, 6 chưa đánh giá). Ví dụ: văn bản gốc đọc trực tiếp là A1, blog chưa đối chiếu là C3. Bảng đầy đủ: [kiem-duyet.md](kiem-duyet.md).

Lời bạn tự nói hay tự gõ không cần qua cổng này.

## 9. Tuỳ chỉnh trong `brain.toml`

| Khoá | Mặc định | Dùng khi |
| --- | --- | --- |
| `lam_ro.fleeting_toi_da_ngay` | 7 | Muốn giữ ý thoáng qua lâu hơn hay ngắn hơn |
| `kiem_duyet.chan_cung` | `true` | Đặt `false` để K1 và `brain turn` chỉ cảnh báo, không chặn |
| `kiem_duyet.truong_bat_buoc` | 5 trường | Đổi các trường bắt buộc của phiếu nguồn |
| `duong_dan.*` | theo khung mẫu | Bạn đổi tên hoặc chỗ các thư mục |
| `bo_nao.vault` | `vault` | Vault nằm ở thư mục khác |

Các ngưỡng như 7 ngày, 90 phút, 7 note cho một MOC chỉ là điểm bắt đầu. Hãy chỉnh lại sau khoảng 4 tuần dùng thật.

## 10. Lỗi thường gặp

| Thấy | Cách xử lý |
| --- | --- |
| `Không tìm thấy brain.toml` | Chạy lệnh bên trong repo bộ não, hoặc thêm `--root <đường-dẫn>`. |
| `ModuleNotFoundError: No module named 'tomllib'` | Python cũ hơn 3.11. Cài bản mới hơn. |
| `Lượt chưa đóng được` | Chạy `brain kiem`, sửa từng lỗi được liệt kê, rồi chạy lại `brain turn`. |
| `permanent note chưa nối tới note nào` | Thêm ít nhất một `[[link]]` vào note. |
| `thiếu tieu_chi_xong` | Project active phải có `ket_qua`, `tieu_chi_xong`, `tieu_chi_dung`. |
| Chữ tiếng Việt hiện sai trên Windows | Dùng Windows Terminal, hoặc chạy `chcp 65001` trước. |

## 11. Cập nhật khi có bản mới

Xem [CHANGELOG.md](../CHANGELOG.md) để biết bản mới đổi gì. Để lấy bản mới của `docs/`, `tools/` và `bin/` mà không đụng vào ghi chú của bạn:

```sh
git remote add chuan https://github.com/DaveTran243/Brain_Standard.git   # chỉ làm lần đầu
git fetch chuan
git checkout chuan/main -- docs tools bin tests CHANGELOG.md
```

Đừng lấy thư mục `vault/` hay file `brain.toml` theo cách này, vì chúng sẽ đè lên dữ liệu và cấu hình của bạn. Nếu bản mới đổi `brain.toml`, hãy so sánh rồi sửa tay.

## Đọc thêm

- [dong-chay.md](dong-chay.md) · Inbox, hai câu hỏi, 7 đường nối giữa các làn, nhịp
- [ba-lan.md](ba-lan.md) · luật, số đo và dấu hiệu hỏng của từng làn
- [kiem-duyet.md](kiem-duyet.md) · cổng K1–K4, bảng mã, 10 bước tra cứu
- [tang-thuc-thi.md](tang-thuc-thi.md) · board, milestone, người phụ trách
- [dung-voi-ai.md](dung-voi-ai.md) · dùng với AI trên nhiều nền tảng
