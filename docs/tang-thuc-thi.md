# Tầng thực thi · 2.2

Bộ não giữ vai điều phối: kết quả muốn có, tiêu chí xong và dừng, các quyết định và bài học. Phần thực thi của project nhiều bước nằm ở board trong repo của category đó, nơi có backlog, milestone, hạn và người phụ trách từng việc.

## Thứ gì nằm ở đâu

| Thứ | Nơi |
| --- | --- |
| Kết quả, tiêu chí xong và tiêu chí dừng | Project file |
| Quyết định lớn và lý do | Project file, mục `## Quyết định` |
| Việc chính bạn làm tiếp theo | Next Actions |
| Backlog, issue, lỗi thường | Board |
| Milestone và hạn | Board |
| Người phụ trách từng việc | Board |
| Chờ người ngoài, không thuộc board nào | Waiting For |
| Bài học sau mỗi milestone | Permanent note qua I1 |

## Project file 2.2

Mẫu: [`vault/10-Action/13-Projects/_mau-project.md`](../vault/10-Action/13-Projects/_mau-project.md). Các trường mới của 2.2 là `repo`, `board`, `milestone`, `han`, `nguoi` và mục `## Quyết định`.

```yaml
---
loai: project
trang_thai: active        # someday | active | done | stopped
bat_dau: 2026-10-20
ket_qua: "…"
tieu_chi_xong: "…"
tieu_chi_dung: "…"
code: 51                  # category trong Coding/
repo: owner/ten-repo
board: https://github.com/users/owner/projects/1
milestone: "M1 · …"
han: 2026-12-31           # bỏ trống nếu không có
nguoi: [ban, …]
---
```

## Cách một việc đi qua

1. **Project 1–2 bước:** không cần board, việc vào thẳng Next Actions.
2. **Project nhiều bước:** mở category, repo và board ngay khi lập (I3), rồi chia milestone đầu tiên.
3. **Mỗi sáng:** việc trên board mà bạn là người làm tiếp được kéo sang Next Actions, ghi kèm số issue.
4. **Log có lỗi:** thành issue trên board. Chỉ lỗi chặn cả project mới đi I6 lên Next Actions.
5. **Xong milestone:** rút 1 bài học (I1), ghi milestone kế tiếp vào project file.
6. **Giao việc cho người khác:** gán người phụ trách trên board. Waiting For chỉ còn cho việc chờ bên ngoài.

## Thay cho giới hạn

Từ 2.2.0 không còn con số nào chặn việc ghi: `brain turn` không báo lỗi khi có nhiều project hay nhiều next action. `brain weekly` chỉ đo để bạn nhìn thấy: số project active, số next action đang mở, project có hạn đã qua.

`brain kiem` vẫn cảnh báo (không chặn) khi:
- project active có milestone mà chưa có board;
- project active không có việc nào trong Next Actions và cũng không có board;
- project active đã qua `han`.
