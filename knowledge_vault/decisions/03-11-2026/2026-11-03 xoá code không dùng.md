---
date: 2026-11-03
type: decision
status: done
tags: [decision, refactor, dead-code]
---
# 2026-11-03 xoá code không dùng

Skill `graph-refactor`, nhánh `refactor/dead-code`.

## Quyết định

Xoá ba symbol không ai dùng:

- `atomic_write_bytes` (`subagent/kernel/util.py`);
- `read_episode_briefing` (`subagent/memory/briefings.py`);
- `PreviewWidget.close_media` (`app/preview.py`).

## Lý do

Đồ thị không có cạnh nào trỏ tới chúng, và tên của chúng không xuất hiện ở đâu khác trong code Python, trong `__all__` hay trong spec. Các hàm phụ mà chúng gọi (`_atomic_write`, `_read`) vẫn được dùng ở chỗ khác nên giữ lại.

## Kết quả

- −12 dòng; ruff sạch; 268 test qua trước và sau.
- Symbol không dùng theo đồ thị: 3 → 0. Đồ thị build lại với `--force`: 3.289 → 3.286 node.
