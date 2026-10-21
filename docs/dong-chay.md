# Dòng chảy

Mọi thứ vào một Inbox, qua hai câu hỏi, rồi đi vào đúng một trong ba làn. Các làn trao đổi với nhau qua 7 đường có tên, không đi tắt.

Từ 3.0, Javis đứng ở hai đầu dòng chảy: **thu** ở đầu vào và **làm tiếp** ở đầu ra. Phần giữa, tức hai câu hỏi và chọn làn, vẫn do bạn quyết. Xem [Vòng Javis](#vòng-javis).

```text
Javis THU ──► Inbox ──► bạn PHÂN LOẠI ──► lối ra ──► Javis LÀM TIẾP ──► kết quả về Inbox
              (ghi, nop)  (2 câu hỏi, 3 làn)    (giao @javis)    (javis, xong)
```

## Nguồn vào

| Nguồn | Đi qua K1? |
| --- | --- |
| Lời bạn: ghi tay, nói, gõ, lệnh `ghi:`, kể cả nhắn qua Javis | Không |
| Agent tra cứu: web, paper, API, Claude hay Javis tự tra | Có, chặn cứng |
| Kết quả việc Javis làm xong (`brain xong`) | Không, nhưng đi tối đa tới Fleeting; dữ kiện tự tra trong đó phải đã nộp riêng qua K1 |
| Export chat mỗi tuần, chỉ khi có dữ liệu mới | Không khi nhập, nhưng mang nhãn chưa kiểm và đi tối đa tới Fleeting |

Export chat chứa cả lời bạn lẫn câu trả lời của AI, nên không lập phiếu cho cả bản export. Nó vào Inbox bằng `brain ghi --kenh export`, được coi như mã F6: chưa kiểm, đi tối đa tới Fleeting. Một dữ kiện trong đó muốn lên literature, permanent hay thẻ ôn thì phải lập phiếu nguồn riêng và nộp qua K1 bằng `brain nop`. Lời bạn chép lại từ export vẫn là lời bạn, không qua K1.

Trạng thái của máy và các routine ghi vào `_log`, không ghi vào Inbox.

## Hai câu hỏi làm rõ

**Câu 1 · Cần làm gì không?**

| Trả lời | Lối ra |
| --- | --- |
| Dưới 2 phút | Làm luôn |
| Một bước | Next Actions |
| Nhiều bước, làm trong 3 tháng tới | Project (nhiều bước thì có board, xem [tầng thực thi](tang-thuc-thi.md)) |
| Chưa làm | Someday/Maybe |
| Chờ người khác, ngoài board | Waiting For |

**Câu 2 · Có đáng giữ không?** (khi câu 1 là "không")

| Trả lời | Lối ra |
| --- | --- |
| Ý thoáng qua | Fleeting, giữ tối đa 7 ngày |
| Tóm một nguồn đọc | Literature note |
| Ý đã chín, đứng một mình được | Permanent note, có ít nhất 1 link |
| File hoặc code | Làn file và code, khu 50–59 |
| Không | Xoá |

## Ba làn

| Làn | Mô hình | Câu hỏi lõi | Kho |
| --- | --- | --- | --- |
| Hành động | GTD + PARA | Bước tiếp theo, cụ thể, là gì? | Next Actions, Projects, Someday, Areas, Waiting For, Archive, board |
| Tri thức | Zettelkasten + LYT + FSRS | Ý này nối với ý nào tôi đã có? | Fleeting, literature, permanent, MOC, bộ thẻ |
| File và code | Johnny Decimal | Thứ này nằm ở số nào? | Index 50.00, thư mục 5x.xx, repo |

Chi tiết luật từng làn: [ba-lan.md](ba-lan.md).

## Bảy đường nối

| Mã | Từ → đến | Khi nào | Mang theo |
| --- | --- | --- | --- |
| I1 | hành động → tri thức | Xong milestone, xong việc quan trọng, hoặc đóng project | 1 bài học thành permanent note, link về project |
| I2 | tri thức → hành động | Một note gợi ra việc làm được | 1 mục Someday, link về note |
| I3 | hành động → file | Lập project nhiều bước | Category trong khu 50–59, repo và board |
| I4 | tri thức → hành động | Một thẻ bị quên từ 3 lần trở lên | Next action "đọc lại <nguồn>" |
| I5 | file → tri thức | Một lần chạy cho ra số liệu mới | Literature note, nguồn là số AC.ID của log |
| I6 | file → hành động | Issue giao cho bạn, hoặc lỗi chặn cả project | Next action trỏ số issue. Lỗi thường ở lại board. |
| I7 | tri thức → hành động | Kiểm lại thấy khẳng định sai | Việc sửa note, thẻ hoặc node bản đồ |

## Vòng Javis

Javis là trợ lý vận hành chạy trên bộ não, ví dụ [Javis OS](dung-voi-javis.md). Nó không có trí nhớ riêng về tri thức: mọi thứ nó biết nằm trong bộ não.

| Bước | Ai | Làm gì | Lệnh |
| --- | --- | --- | --- |
| 1 · Thu | Javis | Nhận từ Telegram, giọng nói, web, email. Lời bạn chép nguyên văn; dữ kiện tự tra có phiếu nguồn | `brain ghi`, `brain nop` |
| 2 · Phân loại | Bạn | Trả lời hai câu hỏi, chọn làn. Javis chỉ được đề xuất lối ra | |
| 3 · Giao | Bạn | Gắn nhãn cho next action Javis được làm, kèm mức quyền | `brain giao "…" <mức>` |
| 4 · Làm tiếp | Javis | Nhận việc ở mức không quá mức của lượt đang chạy, làm, đặt kết quả vào repo hoặc board | `brain javis --muc <mức>` |
| 5 · Trả kết quả | Javis | Đánh dấu xong; một dòng kết quả vào Inbox | `brain xong <số> "…"` |

Kết quả quay về bước 2, nên không có gì vào làn mà chưa qua tay bạn.

**Nhãn.** Trên next action, dạng `@javis:<mức>`, kèm ngày giao. `brain giao` gắn cả hai:

```text
- [ ] Soạn email hỏi kế toán · @máy · ~20' · @javis:auto · giao 2026-10-21
```

| Mức | Javis được | Ví dụ |
| --- | --- | --- |
| `suggest` | Đọc, tra cứu qua K1, đề xuất. Không ghi file | So sánh giá ba máy in |
| `auto` | Thêm việc ghi nháp, code, issue trong repo | Soạn email, viết script trong khu 5x |
| `full` | Thêm hành động thật bên ngoài: gửi tin, đăng bài, đặt hàng | Gửi email đã duyệt |

**Luật của vòng.**

1. Chỉ bạn giao việc. Javis không tự gắn hay nâng mức nhãn; plugin và hook chặn việc đó.
2. Javis không bao giờ viết permanent note, xoá dữ liệu, bỏ qua K1, hay tự chốt hoặc dừng project, ở mọi mức.
3. Việc giao quá `treo_toi_da_ngay` (mặc định 7) chưa xong thì `brain kiem` cảnh báo. Nhãn thiếu mức là lỗi.
4. Weekly Review đếm việc giao đang mở, xong trong tuần và đang treo.

## Nhịp

| Nhịp | Việc |
| --- | --- |
| Mỗi ngày, 30–45 phút | Chọn tối đa 3 việc từ Next Actions, làm ít nhất 1 việc thật, ôn 15–20 thẻ, ghi ý mới vào Inbox; giao cho Javis những việc nó làm được |
| Mỗi lượt làm việc | Kết thúc bằng `brain turn <viec\|y\|file\|xoa> "tóm tắt"` |
| Chủ nhật, 30 phút | Weekly Review: dọn Inbox, rà Projects và board, Someday, Areas, Waiting For, đối chiếu Index, rà việc đã giao Javis; đọc số đo `brain weekly` |
| Mỗi tháng | Kiểm lại 10 khẳng định ngẫu nhiên trong permanent và bản đồ tri thức |
| Mỗi quý | Mỗi Area sinh một project; gộp category nếu cần |

## Nền, không nằm trong dòng chảy

- `_log`: nhật ký máy, các mục bị K1 loại, các lượt `brain turn`.
- Archive: project đã xong hoặc đã dừng, ghi lý do dừng.
