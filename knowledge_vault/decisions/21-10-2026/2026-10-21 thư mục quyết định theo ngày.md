---
date: 2026-10-21
type: decision
status: done
tags: [decision, vault]
---
# 2026-10-21 thư mục quyết định theo ngày

## Quyết định (chủ dự án chọn)

- CLAUDE.md mục 9 có quy tắc mới: các quyết định cùng một ngày nằm chung một thư mục, đặt tên theo ngày quyết định.
- Tên thư mục là **`dd-mm-yyyy`** (ví dụ `decisions/21-10-2026/`). Quy tắc ghi `dd/mm/yyyy`, nhưng `/` là dấu phân cách đường dẫn và Windows không cho dùng trong tên thư mục, nên thay bằng `-`.
- Các ghi chú tham khảo không có ngày (`đo lường - …`, `thiết kế - lý do các lựa chọn`, `lịch sử - …`, `điểm yếu đã biết`) **giữ ở gốc `decisions/`**: chúng được cập nhật liên tục, không thuộc một ngày nào.
- Tên file giữ nguyên (vẫn có tiền tố `yyyy-mm-dd`), nên các liên kết `[[...]]` của Obsidian vẫn chạy.

## Thực hiện

- 13 ghi chú có ngày được chuyển (`git mv`) vào 6 thư mục: `07-10-2026`, `08-10-2026`, `10-10-2026`, `11-10-2026`, `12-10-2026`, `21-10-2026`.
- Liên kết markdown tương đối trong `changelog/` và `decisions/` được tính lại bằng script (giữ nguyên kiểu mã hoá của từng liên kết).
- Kiểm tra: 66 liên kết `.md` tương đối trong vault, 0 liên kết hỏng. Các file trong `.claude/rules/` chỉ trỏ tới ghi chú không có ngày nên không phải sửa.

## Lưu ý

- Thư mục `dd-mm-yyyy` không tự xếp theo thời gian trong danh sách file (ví dụ `01-11-2026` đứng trước `07-10-2026`). Tiền tố `yyyy-mm-dd` trong tên file vẫn giữ thứ tự bên trong mỗi thư mục.

Related: [2026-10-21 rút gọn skill refactor](2026-10-21%20r%C3%BAt%20g%E1%BB%8Dn%20skill%20refactor.md)
