---
date: 2026-11-03
type: decision
status: done
tags: [decision, refactor, app, review]
---
# 2026-11-03 tách trạng thái màn hình review

Nhánh `refactor/review-pure-parts`. Chạy skill `graph-refactor` lần đầu: kế hoạch từ đồ thị graphify, chủ dự án chọn mục tiêu "ReviewView, phần thuần".

## Quyết định

Tách hai phần không dùng Qt ra khỏi `ReviewView` (`app/views/review.py`) sang file mới `app/views/review_state.py`:

- `LineHistory`: undo / redo theo từng dòng. Gồm hai ngăn xếp, quy tắc gộp các lần sửa cùng một trường của một dòng trong 1,5 s thành một bước, `clear()` (khi mở tập) và `break_merge()` (sau undo, reset, discard). Trước đây là ba thuộc tính `undo`, `redo`, `_last_push` cùng logic nằm trong view.
- `LineFilter` + `line_matches()`: bộ lọc danh sách dòng (flag, "rule_warnings", speaker, chỉ chưa duyệt, tìm trong zh / vi, mẫu audit). Trước đây là `_matches`, đọc thẳng từ các widget.

`ReviewView` giữ `_push_undo` dưới dạng một dòng gọi `history.push`, nên 8 chỗ gọi không đổi. `_line_filter()` chụp trạng thái thanh công cụ thành `LineFilter`. Hành vi giữ nguyên, kể cả chi tiết: khi mở tập chỉ xoá ngăn xếp, giữ mốc gộp như trước. Thêm `review_state.py` vào bố cục kho trong `.claude/rules/architecture.md` (3.3).

## Lý do

- Đồ thị: `ReviewView` có 81 method, file 1.314 dòng, các symbol rải trên 12 cộng đồng (cộng đồng lớn nhất chỉ chiếm 23%). Đây cũng là file thay đổi nhiều nhất (13 commit trong 3 tháng).
- Undo / redo và bộ lọc là logic thuần nhưng trước đây chỉ kiểm được bằng cách dựng cả màn hình (test_app). Tách ra thì kiểm riêng được, nhanh, không cần Qt.
- Chọn phần thuần trước vì rủi ro thấp nhất trong mục tiêu ReviewView. Hai nhóm còn lại (panel sửa nhân vật, phần audit) để lần sau.

Các lead bị loại khi kiểm code: BootstrapView (lớn nhưng gắn kết, gọi core qua `app/services/bootstrap` từng bước một), `settings_form.py` (các widget chỉ dùng ở đó), `kernel/models.py` / `util.py` (theo thiết kế), `Services` / `config.py` (ít thay đổi), các hàm trùng tên (`get_engine`, `write_report`, `_pct`… mỗi hàm làm một việc khác).

## Kết quả

- ruff sạch; pytest 261 → 265 test, tất cả qua (thêm `tests/test_review_state.py`: 4 test chạy 0,08 s). `test_app.py`, gồm 3 test undo, qua mà không phải sửa.
- `app/views/review.py`: 1.314 → 1.296 dòng (+24 / −42). Số method vẫn 81 (bỏ `_matches`, thêm `_line_filter`), số cộng đồng vẫn 12; tỷ lệ của cộng đồng lớn nhất 0,23 → 0,34. Cái được là logic và trạng thái chuyển ra ngoài và có test riêng, không phải số method.
- Đồ thị cập nhật (`graphify update .`): 3.251 → 3.278 node, 11.197 → 11.277 cạnh (thêm module và test mới).

Việc tiếp theo trong kế hoạch: tách panel sửa nhân vật (7 method) và phần audit (6 method) của `ReviewView`; xoá 3 symbol không dùng.

Related: [2026-11-03 graphifyignore](2026-11-03%20graphifyignore.md)
