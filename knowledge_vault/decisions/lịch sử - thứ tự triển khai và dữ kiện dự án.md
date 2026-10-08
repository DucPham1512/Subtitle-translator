---
date: 2026-10-08
type: history
tags: [history, project-facts]
---
# Lịch sử - thứ tự triển khai và dữ kiện dự án

Chuyển từ CLAUDE.md (mục 10 và 11) ngày 2026-10-08.

## Thứ tự triển khai (đã hoàn thành)

1. Khung dự án, config, models, CLI, `llm.py` có cache và theo dõi chi phí, registry tập (`add`, `relink`).
2. Lệnh calibrate, rồi ingest + OCR + events (có phát hiện dòng không phải hội thoại) trên một clip 2 phút; tinh chỉnh dải phụ đề và ngưỡng.
3. OCR correction.
4. Memory store + Memory Manager + bootstrap (chưa có giọng).
5. Pinyin.
6. Windows + vòng translator / evaluator, rồi script review.
7. Review gate, bản nháp review và `finish-review` (CLI), cập nhật memory, briefing. Dùng chế độ auto cho đến khi có màn hình review trong app.
8. Render, giao output và cleanup.
9. Audio + voice bank + khớp giọng; đưa ứng viên speaker vào input của translator.
10. Sprite check (chỉ khi tỷ lệ mơ hồ đo được đáng làm).
11. Dreaming.
12. Report và lệnh status.
13. Khung app: điều hướng, settings, khung i18n (tiếng Anh + tiếng Việt), chạy job với tiến độ JSON.
14. Màn hình Episodes và Run.
15. Màn hình review có preview trực tiếp.
16. Màn hình memory có lịch sử và rollback.
17. Bootstrap wizard.
18. Màn hình dreaming.

## Dữ kiện dự án (chủ dự án đã xác nhận)

| Câu hỏi | Trả lời | Xử lý ở |
|---|---|---|
| Phần cứng | GPU NVIDIA | 2, NFR-P1, 5.19 |
| Hệ điều hành | Windows | NFR-PT1–PT5, 5.19 |
| Độ phân giải video | Chưa biết | Đọc bằng ffprobe; dải phụ đề tính theo tỷ lệ; cỡ chữ co theo chiều cao (5.3, 5.19) |
| Bố cục phụ đề | Vị trí cố định, một dòng | 5.3 calibration, 5.4 |
| Chữ khác trong dải phụ đề | Chưa biết | 5.5 phát hiện dòng không phải hội thoại, 5.11 `line_type` |
| Output | Luôn có pinyin + tiếng Việt | 5.19 |
| Bối cảnh | Cổ trang / tiên hiệp | 5.11 register, các loại glossary |
| Độ dài tập | 5–15 phút | Ngân sách đặt sau báo cáo của tập đầu |
| Giao diện | App desktop có preview video, bao trọn mọi việc | 6 |
| Preview khi review | Phụ đề mới hiển thị trực tiếp trên video đã che | 6.5 |
| Memory trong app | Xem, sửa, rollback | 6.7, 5.15 |
| Ngôn ngữ giao diện | Chuyển được giữa tiếng Anh / tiếng Việt | 6.9, 6.10 |
| Thứ tự review | Luôn theo thời gian; cờ qua bộ lọc | 6.4 |
| Dịch lại từ màn hình review | Không, chỉ sửa tay | 6.4 |
| Thêm video | Một file, nhiều file, thư mục, kéo thả | 5.21, 6.3 |
| Số tập | Đoán từ tên file, người dùng xác nhận | 5.21 |
| Video gốc | Liên kết, không sao chép | 5.21 |
| Nơi lưu output | Một thư mục mặc định đặt trong Settings | 5.22, 6.9 |
| Nội dung output | Chỉ video hoàn chỉnh | 5.22 |
| Tên output | Tên gốc + `_vi` | 5.22 |
| File output đã tồn tại | Hỏi mỗi lần | 5.22 |
| File làm việc | File tạm tự xoá khi một tập xong | 5.23 |

Còn phải đo trên tập thật đầu tiên (ghi chú gốc): tỷ lệ dải phụ đề, ngưỡng thay đổi và OCR, ngưỡng khớp giọng, ngưỡng dòng không phải hội thoại, và chi phí mỗi tập.

Các số mục trong cột "Xử lý ở" trỏ tới tiêu đề cùng số trong `CLAUDE.md` và `.claude/rules/`.

Related: [thiết kế - lý do các lựa chọn](thiết%20kế%20-%20lý%20do%20các%20lựa%20chọn.md)
