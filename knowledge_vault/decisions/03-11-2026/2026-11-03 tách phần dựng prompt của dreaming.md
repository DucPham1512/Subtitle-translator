---
date: 2026-11-03
type: decision
status: done
tags: [decision, refactor, memory, dreaming]
---
# 2026-11-03 tách phần dựng prompt của dreaming

Skill `graph-refactor`, nhánh `refactor/graph-pass`.

## Quyết định

`dream()` (`subagent/memory/dreaming.py`, 5.18) tách hai hàm:

- `_speaker_corrections(paths, since=...)`: đọc `speaker_corrections.jsonl` và giữ các dòng sau lần dream trước. Trước đây là một biểu thức ghép đường dẫn file hai lần.
- `_dream_variable(...)`: phần biến đổi của prompt (đề xuất đã bị từ chối, thuật ngữ dùng không đều, sửa của người, sửa speaker, các dòng đã duyệt).

## Lý do

Đồ thị: `dream()` là một trong ba hàm dài nhất (gọi 24 hàm khác nhau, 52 dòng). Trước đó đã ghi là để lại vì prompt phải giữ đúng từng byte (luật cache 5.1, và khoá cache LLM là hash của messages). Lần này làm, kèm cách kiểm: một test tạm ghi lại đúng messages mà `dream()` gửi, với đủ các nhánh (sửa speaker cũ và mới, dòng trống, đề xuất bị từ chối), chạy trước và sau khi sửa rồi so từng byte.

## Kết quả

- Prompt giống hệt từng byte trước và sau (`cmp`); test tạm đã xoá.
- ruff sạch; 272 test qua. `dream()` 52 → 40 dòng.
