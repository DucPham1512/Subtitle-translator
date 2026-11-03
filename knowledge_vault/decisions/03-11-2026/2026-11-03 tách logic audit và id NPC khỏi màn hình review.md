---
date: 2026-11-03
type: decision
status: done
tags: [decision, refactor, app, review, audit]
---
# 2026-11-03 tách logic audit và id NPC khỏi màn hình review

Nhánh `refactor/review-pure-parts`, commit sau `4ebb393` (lần tách trước: [2026-11-03 tách trạng thái màn hình review](2026-11-03%20t%C3%A1ch%20tr%E1%BA%A1ng%20th%C3%A1i%20m%C3%A0n%20h%C3%ACnh%20review.md)). Skill `graph-refactor` lần hai; chủ dự án chọn "Audit + NPC id".

## Quyết định

Tách bốn hàm thuần ra khỏi `ReviewView` (`app/views/review.py`) sang `app/views/review_state.py`:

- `marked_count(sample, marks)`: số dòng mẫu đã chấm (cho dòng tiến độ audit).
- `all_correct_mark(event_id, old, speaker, marked_at)`: dấu "mọi khía cạnh đúng", giữ các khía cạnh N/A và ghi chú đã có; thời điểm truyền vào, nên hàm cho kết quả cố định.
- `next_unmarked(order, current, marks)`: dòng mẫu tiếp theo (vòng lại từ đầu) còn phải chấm: chưa chấm, hoặc speaker sai mà chưa ghi ai thật sự nói.
- `next_npc_number(ids, prefix, episode_number)`: số `<n>` tiếp theo còn trống của id tự động `npc_<ep>_<n>` trong tập.

Trạng thái audit (`audit_mode`, `audit_sample`, `audit_marks`) vẫn ở trên view, vì `tests/test_app.py` đọc thẳng các thuộc tính này. Chuyển nó vào một object sẽ làm test đổi ngoài đường dẫn import, tức là đổi hành vi theo luật của skill. Thêm mô tả trong bố cục kho (`architecture.md` 3.3).

## Lý do

- Kế hoạch lần hai: panel sửa nhân vật bị loại vì 7 method chủ yếu nối widget và gọi ngược vào khoảng 8 phần khác của view; tách thành class sẽ "feature envy". Chỉ phần tính id NPC là thuần.
- Logic chấm audit trước đây nằm trong handler Qt và chỉ có một test tích hợp; giờ có test riêng cho từng quy tắc (vòng lại, chờ "ai thật sự nói", giữ N/A, chỉ đếm id của tập này).

## Kết quả

- ruff sạch; pytest 265 → 268, tất cả qua (thêm 3 test, `tests/test_review_state.py` chạy 0,08 s); hai test tích hợp audit và NPC qua mà không sửa.
- `ReviewView` vẫn 81 method, `review.py` vẫn 1.296 dòng (khối import dài thêm bằng phần logic bớt đi); `review_state.py` 113 dòng.
- Đồ thị (`graphify update .`): 3.278 → 3.289 node. Điểm "nhiều việc" của `review.py` 103,2 → 27,7 (12 → 8 cộng đồng, tỷ lệ cộng đồng lớn nhất 0,34 → 0,73). Một phần con số này do graphify phân cụm lại toàn đồ thị mỗi lần cập nhật, không chỉ do thay đổi này; số method và số symbol mới là số ổn định.

Muốn `ReviewView` thật sự nhỏ đi thì phải tách cả trạng thái (audit, nhân vật) ra object riêng, và sửa cách `test_app.py` đọc trạng thái màn hình. Việc đó cần chủ dự án đồng ý trước.
