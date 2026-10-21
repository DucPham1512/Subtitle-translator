---
date: 2026-10-21
type: decision
status: done
tags: [decision, claude-code, skill]
---
# 2026-10-21 rút gọn skill refactor

## Quyết định

`.claude/skills/refractor/SKILL.md` dài 644 dòng, vượt mức khuyến nghị 200 dòng cho một file skill. Tách thành ba file trong cùng thư mục, giữ nguyên nội dung (chỉ chuyển chỗ, không sửa chữ):

- `SKILL.md` (~140 dòng): tổng quan, khi nào dùng, nguyên tắc, khi nào không nên refactor, quy trình an toàn, checklist, bảng các thao tác refactor, và mục **Reference Files** trỏ tới hai file dưới.
- `code-smells.md`: 10 code smell thường gặp kèm ví dụ BAD / GOOD.
- `techniques.md`: ví dụ Extract Method, thêm kiểu dữ liệu (type safety), design pattern (Strategy, Chain of Responsibility).

## Lý do

SKILL.md được nạp toàn bộ mỗi khi skill chạy; phần ví dụ dài chỉ cần khi gặp đúng loại vấn đề, nên để Claude đọc khi cần (progressive disclosure) thì tốn ít ngữ cảnh hơn.
