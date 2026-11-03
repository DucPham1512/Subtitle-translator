---
date: 2026-11-03
type: decision
status: done
tags: [decision, refactor, app, review]
---
# 2026-11-03 chia nhỏ phần ghi chú của màn hình review

Skill `graph-refactor`, nhánh `refactor/graph-pass`.

## Quyết định

`ReviewView._render_context` (khung ghi chú chỉ đọc của màn hình review, 6.4) từ 67 dòng chia thành:

- `_render_context` (22 dòng): phần đã xoá, flag, lý do, rồi ghép các phần bên dưới theo đúng thứ tự cũ;
- `_partial_section`, `_evaluator_section`, `_rule_sections` (thuật ngữ và cặp xưng hô): các method của view, vì chúng dựng chuỗi `tr()`;
- `_section`, `_bullets`: hai closure lồng bên trong trước đây, nay là hàm ở mức module.

## Lý do

Hàm dài nhất còn lại trong `ReviewView` sau các lần tách trước, gồm sáu phần không liên quan nhau. Chuỗi giao diện vẫn nằm trong `ReviewView`, nên ngữ cảnh dịch Qt (`<name>ReviewView</name>` trong `app/i18n/*.ts`) vẫn khớp.

Cách kiểm: một test tạm ghi lại mọi chuỗi HTML gửi tới khung ghi chú, qua 11 trường hợp phủ đủ các phần (đã xoá, flag, lý do, partial review, evaluator có gợi ý, thuật ngữ, cặp xưng hô, không có cặp xưng hô, không có ghi chú, không có `rules`). Chạy trước và sau khi sửa rồi so từng byte.

## Kết quả

- HTML giống hệt từng byte trước và sau (`cmp`); test tạm đã xoá.
- ruff sạch; 272 test qua. `review.py` 1.290 → 1.306 dòng (chữ ký và docstring của các method mới). Thêm 3 method vào `ReviewView` (81 → 84): đây là đánh đổi của Extract Method, đổi lại không còn method nào dài quá 30 dòng trong phần này.
