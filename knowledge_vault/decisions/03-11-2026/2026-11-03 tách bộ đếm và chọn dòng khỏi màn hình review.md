---
date: 2026-11-03
type: decision
status: done
tags: [decision, refactor, app, review]
---
# 2026-11-03 tách bộ đếm và chọn dòng khỏi màn hình review

Skill `graph-refactor`, nhánh `refactor/graph-pass`; tiếp theo [2026-11-03 tách logic audit và id NPC khỏi màn hình review](2026-11-03%20t%C3%A1ch%20logic%20audit%20v%C3%A0%20id%20NPC%20kh%E1%BB%8Fi%20m%C3%A0n%20h%C3%ACnh%20review.md).

## Quyết định

Ba quy tắc thuần cuối cùng của `ReviewView` chuyển sang `app/views/review_state.py`:

- `review_counts()` → `ReviewCounts` (tổng, đã duyệt, còn cờ, đã xoá) cho bộ đếm ở đầu màn hình; chuỗi `tr()` và việc bật / tắt nút vẫn ở view;
- `next_pending()`: dòng tiếp theo cần duyệt sau "Approve and next" (đi tiếp, rồi quay về đầu, không còn thì đứng yên);
- `row_state()`: ký hiệu ở cột trạng thái (✕ ✓ ⚑ ·; ở chế độ audit là dấu chấm của dòng).

## Lý do

Cùng kiểu như hai lần tách trước: quy tắc thuần nằm trong handler Qt chỉ kiểm được qua test tích hợp. `_render_context` (67 dòng) vẫn ở view vì nó dựng HTML từ các chuỗi `tr()`.

## Kết quả

ruff sạch; pytest 268 → 271, tất cả qua (thêm 3 test; `test_review_state.py` có 10 test, chạy 0,09 s). `review.py` 1.296 → 1.290 dòng; `ReviewView` vẫn 81 method (các method chỉ gọi hàm mới).
