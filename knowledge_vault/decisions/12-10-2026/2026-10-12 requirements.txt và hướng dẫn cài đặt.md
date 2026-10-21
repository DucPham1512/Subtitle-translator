---
date: 2026-10-12
type: decision
status: done
tags: [decision, install, docs]
---
# 2026-10-12 requirements.txt và hướng dẫn cài đặt

Nhánh `docs/install-guide`.

## Quyết định (chủ dự án chọn)

- **Một file `requirements.txt` cho cả máy đích** (Windows, GPU NVIDIA): pipeline, app, OCR GPU, giọng nói (torch CUDA), nhận diện nhân vật, công cụ test. Cài bằng một lệnh `pip install -r requirements.txt`.
- **Ghim đúng phiên bản** (`==`) đang chạy trong `.venv` (Python 3.13), để máy mới cài đúng bộ đã test. Khoảng phiên bản và các nhóm tuỳ chọn vẫn ở `pyproject.toml`.
- torch lấy từ chỉ mục wheel CUDA 12.8 của PyTorch (`--extra-index-url`). OCR GPU dùng `onnxruntime-gpu[cuda,cudnn]`, nên pip tự tải thư viện CUDA 13 / cuDNN 9.
- **README:** các mục Quick start / Requirements / Setup cũ được viết lại thành hai mục:
  - **Install**: 5 bước (cần gì, UTF-8, venv + requirements, khoá API, kiểm tra), thêm phần chỉ dùng CPU và driver cũ.
  - **Run**: app và dòng lệnh.
  - Các mục khác giữ nguyên.

## Kiểm tra

`pip install --dry-run -r requirements.txt` trong `.venv` hiện tại: giải được hết, không cần cài thêm gì. Chưa thử cài trên máy mới.

## Lưu ý

- Máy chỉ có CPU vẫn cài được bằng file này: torch và ONNX Runtime tự chạy trên CPU. README chỉ cách thay bằng bản CPU cho nhẹ hơn.
- Khi nâng phiên bản một gói, cập nhật cả `requirements.txt`.
