---
date: 2026-11-03
type: decision
status: done
tags: [decision, refactor, ocr]
---
# 2026-11-03 tách hai bước của calibrate kiểu phụ đề

Skill `graph-refactor`, nhánh `refactor/graph-pass`.

## Quyết định

`calibrate()` (`subagent/ocr/subtitle_style.py`, 5.4a) từ 80 dòng tách thành hai bước, chuyển nguyên văn:

- `_text_regions(bands, stable_range, h)`: gom các vùng giống chữ theo từng polarity (MSER, stroke-width transform, độ ổn định, viền);
- `_style_from_regions(found, h, source)`: chọn polarity, rồi suy ra khoảng xám của fill, mức viền, độ dày nét, chiều cao chữ.

`calibrate()` giờ chỉ kiểm số band rồi gọi hai bước.

## Lý do

Hàm dài thứ hai trong code không phải giao diện (kiểm thêm bằng AST: các hàm trên 60 dòng). Hai bước là hai việc khác nhau: tìm vùng chữ, và học kiểu từ chúng.

Cách kiểm: chạy `calibrate` trên các band tổng hợp của `tests/test_subtitle_style.py`, 4 seed × 2 polarity (chữ sáng viền tối, và đảo màu), cộng trường hợp thiếu band, trước và sau khi sửa, rồi so kết quả (bỏ ngày calibrate).

Các hàm dài khác cũng xem nhưng để nguyên: `suite.score_translation` (một vòng thẳng với ba bộ đếm), `settings_form._field` (rẽ nhánh theo kiểu trường, mỗi nhánh vài dòng), `cmd_audit` (CLI rẽ nhánh theo lệnh), `suite.render` (dựng báo cáo Markdown); các `__init__` của widget Qt.

## Kết quả

Kết quả giống hệt ở cả 9 trường hợp. ruff sạch; 272 test qua.

Phát hiện, để nguyên: `_text_regions` / `_style_from_regions` có nhiều ngưỡng viết thẳng trong code (0,15 / 0,8 / 0,4 chiều cao, độ lệch xám 60, phân vị 5 / 99,5). Spec 5.4a mô tả chúng là thiết kế cố định, nhưng CLAUDE.md §9 muốn mọi ngưỡng nằm trong config. Chuyển chúng ra config là một quyết định riêng.
