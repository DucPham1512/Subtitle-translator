---
date: 2026-10-21
type: decision
status: done
tags: [decision, install, linux]
---
# 2026-10-21 chuyển sang Linux

## Hiện trạng

- Dự án chuyển từ Windows sang Linux (GPU RTX 3060 Laptop, driver 595). `.venv` mới dùng Python 3.14; `requirements.txt` (ghim trên 3.13) cài được nguyên vẹn, không đổi phiên bản nào.
- Khi cài: `/tmp` là RAM disk 7,5 GB, không đủ chỗ giải nén các wheel CUDA, pip báo "Disk quota exceeded". Cách xử lý: đặt `TMPDIR` sang ổ chính khi chạy `pip install`.
- Kiểm tra: 257 test qua, `ruff` sạch, torch thấy CUDA, ONNX Runtime có CUDA / TensorRT, `python -m subagent check` báo `device: GPU`.
- **Mất toàn bộ dữ liệu series-1** không nằm trong git: `memory/` (memory.db, briefings, lịch sử git), `episodes/index.json`, thư mục làm việc cũ (gồm baseline `replay-2026-10`). Bootstrap, font, ghi chú prompt và `series.yaml` vẫn còn.

## Quyết định (chủ dự án chọn)

- Video vào và ra nằm trong dự án: `video_data/input/` (video gốc, đăng ký bằng `add video_data/input`) và `video_data/output/` (`output.folder` trong `config.yaml`). `video_data/` được git bỏ qua.
- `output.folder` ghi đường dẫn tuyệt đối, vì đường dẫn tương đối ở khoá này tính theo thư mục đang chạy lệnh, không theo thư mục dự án.
- Bỏ `paths.work_dir: E:/Video Data/Raw` trong `series.yaml` của series-1; thư mục làm việc về mặc định `work/series-1/` trong dự án.
- Lần tái cấu trúc module sắp tới **không kiểm tra hành vi trên dữ liệu thật** (so sánh artifact, `bench score`) vì không còn dữ liệu để so; bộ test là phép kiểm duy nhất. Chủ dự án cho phép bỏ qua lần này.
- API key cho cả Deepseek và Gemini đã được cung cấp trong .env.

## Còn thiếu

- series-1 bắt đầu lại từ memory rỗng: chạy `bootstrap` trước tập đầu.
