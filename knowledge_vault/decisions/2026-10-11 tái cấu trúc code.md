---
date: 2026-10-11
type: decision
status: done
tags: [decision, refactor, code-structure]
---
# 2026-10-11 tái cấu trúc code

Nhánh `refactor/structure`, 10 commit, mỗi bước một commit. Hành vi không đổi: toàn bộ test chạy lại sau từng bước và đều qua.

## Phạm vi (chủ dự án chọn)

Memory Manager, CLI, màn Review, và các hàm dài khác.

## Đã làm

- **Memory Manager** (`subagent/memory/manager.py`, 1,442 dòng):
  - 7 khối "BEGIN / COMMIT / ROLLBACK" chép lại giống nhau → một hàm `_transaction()`.
  - Tách thành gói `memory/manager/`, mỗi module một việc: `apply` (luật ghi, memory dạng Markdown, chỉnh sửa tay, conflict), `episode` (cập nhật sau mỗi tập, lifecycle, line decisions, khai thác chỉnh sửa, briefing), `candidates` (thử việc), `updates` (cập nhật nhân vật), `banks` (voice bank, sprite bank), `history` (git, diff, rollback); `rows` / `results` / `proposals` cho phần dùng chung. File lớn nhất còn 358 dòng. Đã kiểm: cả 80 định nghĩa được chuyển nguyên văn; mọi `from subagent.memory.manager import …` vẫn chạy.
  - **Quy tắc 9** trong CLAUDE.md đổi từ "chỉ ghi memory trong `memory/manager.py`" thành "chỉ trong gói `memory/manager/`" (quyết định của chủ dự án).
  - Hai hàm dài nhất: `probation` (137 dòng) thành bốn bước (nhận lại ứng viên quay lại, thêm ứng viên, giữ đề xuất, bỏ ứng viên hết hạn); `_apply_row` (113 dòng) thành làm sạch dữ liệu, rồi xoá / cập nhật / thêm.
- **CLI** (`subagent/__main__.py`, 741 dòng → 74): các lệnh chuyển vào `subagent/cli/` theo nhóm (episodes, memory, measure, series). Trợ giúp `--help` của chương trình và cả 19 lệnh giống hệt từng byte trước và sau.
- **Màn Review:** hàm khởi tạo 216 dòng thành các phần (trạng thái, thanh công cụ, danh sách dòng, trình sửa, hàng người nói, nút, bên phải, nối tín hiệu, bộ hẹn giờ), gọi đúng thứ tự cũ, nên thứ tự phím Tab không đổi.
- **Hàm dài khác:** `sprite_learning.plan`, `translate.run_window`, `bench_run.run`, `cast.run`, `write_sprites` (thêm một hàm xoá exemplar thay cho đoạn lặp lại).

## Kết quả

- Hàm dài hơn 100 dòng: 4 → 0. Hơn 50 dòng: 34 → 27.
- Còn lại chủ yếu là hàm dựng giao diện (preview, Episodes, cửa sổ chính, biểu mẫu Settings) và hàm viết báo cáo / chấm điểm (`suite.render`, `score_translation`): code tuần tự, tách ra ít lợi.

Related: [thiết kế - lý do các lựa chọn](thiết%20kế%20-%20lý%20do%20các%20lựa%20chọn.md)
