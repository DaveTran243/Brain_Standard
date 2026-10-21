# Dòng chảy

Mọi thứ vào một Inbox, qua hai câu hỏi, rồi đi vào đúng một trong ba làn. Các làn trao đổi với nhau qua 7 đường có tên, không đi tắt.

## Nguồn vào

| Nguồn | Đi qua K1? |
| --- | --- |
| Lời bạn: ghi tay, nói, gõ, lệnh `ghi:` | Không |
| Agent tra cứu: web, paper, API, Claude tự tra | Có, chặn cứng |
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

## Nhịp

| Nhịp | Việc |
| --- | --- |
| Mỗi ngày, 30–45 phút | Chọn tối đa 3 việc từ Next Actions, làm ít nhất 1 việc thật, ôn 15–20 thẻ, ghi ý mới vào Inbox |
| Mỗi lượt làm việc | Kết thúc bằng `brain turn <viec\|y\|file\|xoa> "tóm tắt"` |
| Chủ nhật, 30 phút | Weekly Review: dọn Inbox, rà Projects và board, Someday, Areas, Waiting For, đối chiếu Index; đọc số đo `brain weekly` |
| Mỗi tháng | Kiểm lại 10 khẳng định ngẫu nhiên trong permanent và bản đồ tri thức |
| Mỗi quý | Mỗi Area sinh một project; gộp category nếu cần |

## Nền, không nằm trong dòng chảy

- `_log`: nhật ký máy, các mục bị K1 loại, các lượt `brain turn`.
- Archive: project đã xong hoặc đã dừng, ghi lý do dừng.
