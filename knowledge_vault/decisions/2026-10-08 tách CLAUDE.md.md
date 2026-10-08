---
date: 2026-10-08
type: decision
status: done
tags: [decision, docs, claude-md]
---
# 2026-10-08 tách CLAUDE.md

## Quyết định

- `CLAUDE.md` chỉ giữ những gì Claude Code dùng trong mọi phiên: tổng quan, tech stack, bản đồ spec, yêu cầu phi chức năng, quy tắc và quy tắc vault.
- Spec chi tiết (mục 3.2–6.11) chuyển nguyên văn sang `.claude/rules/*.md`, mỗi file có `paths:` nên chỉ nạp khi Claude làm việc với các file khớp.
- Nội dung dành cho chủ dự án (số đo, lịch sử quyết định, lý do thiết kế, thứ tự triển khai, dữ kiện dự án, sơ đồ pipeline) chuyển sang vault, dịch sang tiếng Việt; số, đường dẫn và khoá config giữ nguyên.
- Chưa commit (quyết định của chủ dự án).

## Lý do

- File cũ dài 1,503 dòng, gấp khoảng 7.5 lần hướng dẫn dưới 200 dòng của Anthropic; file dài làm Claude tuân thủ chỉ dẫn kém đi.
- Mục 12 của `CLAUDE.md` đã quy định: khi rút gọn, chuyển lịch sử sang `decisions/` và để lại một dòng liên kết.

## Kết quả

- `CLAUDE.md`: 1,503 → khoảng 165 dòng.
- 10 file trong `.claude/rules/`: architecture, data-models, config, ocr, voice-cast, translation, memory, pipeline-cli, app, benchmarks.
- Kiểm không mất nội dung: mọi dòng của file cũ nằm trong `CLAUDE.md` mới, trong một file rules, hoặc trong các ghi chú vault dưới đây; chỉ bỏ hai tiêu đề mục cha ("## 3. Architecture", "## 5. Components") vì các file rules thay chỗ của chúng.

Ghi chú nhận nội dung chuyển sang:

- [đo lường - OCR](đo%20lường%20-%20OCR.md)
- [đo lường - nhận diện nhân vật và giọng](đo%20lường%20-%20nhận%20diện%20nhân%20vật%20và%20giọng.md)
- [đo lường - script review](đo%20lường%20-%20script%20review.md)
- [đo lường - benchmark suite](đo%20lường%20-%20benchmark%20suite.md)
- [thiết kế - lý do các lựa chọn](thiết%20kế%20-%20lý%20do%20các%20lựa%20chọn.md)
- [lịch sử - thứ tự triển khai và dữ kiện dự án](lịch%20sử%20-%20thứ%20tự%20triển%20khai%20và%20dữ%20kiện%20dự%20án.md)
- [sơ đồ pipeline](../map/sơ%20đồ%20pipeline.md)
