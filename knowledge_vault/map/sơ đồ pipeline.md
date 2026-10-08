---
date: 2026-10-08
type: map
tags: [map, pipeline, diagram]
---
# Sơ đồ pipeline

Chuyển từ CLAUDE.md (mục 3.1) ngày 2026-10-08. Sơ đồ: [pipeline.drawio](../diagrams/pipeline.drawio) (mở được trong draw.io hoặc VS Code); nhãn giữ tiếng Anh vì trùng tên tầng trong code. Danh sách tầng bằng tiếng Việt ở [tổng quan pipeline](tổng%20quan%20pipeline.md).

Cách đọc: video đi vào bộ tách phụ đề (lấy mẫu khung hình → OCR → sửa OCR → events); song song là tách âm thanh và khớp giọng, và nhận diện nhân vật trên màn hình. Translator dịch theo cửa sổ cảnh và chọn speaker / listener; evaluator chấm và gửi lại tối đa 2 lần. Dòng có speaker không chắc có thể qua sprite check. Script review soát cả tập, rồi review gate tách hai chế độ: human (duyệt trong app) và auto. Kịch bản đã duyệt đi vào Memory Manager (bên ghi duy nhất, rồi học giọng) và renderer (ASS → che phụ đề gốc → burn-in). Dreaming chạy offline giữa các tập; bootstrap chạy một lần trước tập 1.

Related: [tổng quan pipeline](tổng%20quan%20pipeline.md)
