---
date: 2026-10-08
type: measurement
tags: [measurement, script-review, ocr]
---
# Đo lường - script review

Chuyển từ CLAUDE.md (mục 5.13a) ngày 2026-10-08. Hành vi hiện tại nằm ở `.claude/rules/translation.md`.

## Sửa lỗi OCR trong hội thoại (prompt Round 3)

Đo trên 12 tập đã duyệt tay, so với answer key OCR; 142 trên 1,761 dòng có tiếng Trung sai sau OCR correction.

- Prompt cũ chỉ ra 41 dòng trong số đó là nhiễu / đáng ngờ, không đưa ra sửa nào.
- Prompt mới đề xuất 46 sửa: 38 đúng hoàn toàn (83%), 1 có hại (sửa một dòng vốn đúng), cộng 16 cờ kiểm OCR. Chấp nhận mọi sửa thì số dòng tiếng Trung đúng tăng từ 1,619 lên 1,656.
- Không có các bước kiểm ngữ cảnh thì đề xuất nhiều hơn (51 đúng) nhưng làm hỏng 8 dòng đúng (chơi chữ và nói giảm như 鸡道, 史).
- Đã xoá 37 dòng mà reviewer cũng xoá, và 2 dòng reviewer gõ lại (đọc rác của 不好 và 也太……).
- Khoảng $0.005 mỗi tập.

Related: [đo lường - OCR](đo%20lường%20-%20OCR.md), [đo lường - benchmark suite](đo%20lường%20-%20benchmark%20suite.md)
