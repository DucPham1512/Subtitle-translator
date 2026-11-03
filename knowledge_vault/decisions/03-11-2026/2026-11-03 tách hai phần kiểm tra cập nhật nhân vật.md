---
date: 2026-11-03
type: decision
status: done
tags: [decision, refactor, memory, character-updates]
---
# 2026-11-03 tách hai phần kiểm tra cập nhật nhân vật

Skill `graph-refactor`, nhánh `refactor/graph-pass`.

## Quyết định

`check()` (`subagent/memory/character_updates.py`, 5.15c) từ 62 dòng tách hai vòng lặp thành hai hàm, chuyển nguyên văn:

- `_character_change()`: cập nhật một nhân vật, chỉ giữ những gì dòng bằng chứng cho thấy (tên được dùng để gọi hoặc tự giới thiệu, mô tả mới, biệt danh);
- `_pronoun_change()`: một cặp xưng hô giữa hai nhân vật của tập, chỉ giữ khi dòng bằng chứng dùng các từ đó và cặp khác với cặp trong memory.

Mỗi hàm trả về một `MemoryProposal` hoặc `None`, và ghi lý do bỏ vào cùng danh sách `dropped`. Thứ tự giữ như cũ: nhân vật trước, xưng hô sau, theo thứ tự trong câu trả lời.

## Lý do

Một trong các hàm dài nhất (kiểm thêm bằng AST: hàm trên 60 dòng). Hai vòng lặp là hai bộ quy tắc riêng.

## Kết quả

ruff sạch; 272 test qua; 5 test của `test_character_updates.py` qua mà không sửa. `check()` 62 → 14 dòng (`_character_change` 34, `_pronoun_change` 23).
