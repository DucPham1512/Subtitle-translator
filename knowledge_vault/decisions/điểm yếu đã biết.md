---
date: 2026-10-07
type: list
status: draft
tags: [weakness]
---
# Điểm yếu đã biết

Nguồn: [CLAUDE.md](../../CLAUDE.md). Chưa giải thích, chưa xếp ưu tiên.

## OCR và event

- 了 bị đọc thành 7
- Chữ ở hai đầu dòng bị cắt hoặc mất
- Chữ đạo cụ trên màn hình lẫn vào phụ đề (姬, 楚, 史, 表)
- Một dòng ngắn nằm giữa hai dòng gần giống nhau bị nuốt khi gộp event
- RapidOCR âm thầm chạy CPU thay vì GPU
- OCR chậm trên CPU
- Segmentation chung chưa kiểm chứng trên series thứ hai
- Tiếng Trung đã duyệt vẫn sót lỗi OCR
- Answer key thiếu những dòng OCR mới đọc được

## Speaker và listener

- Speaker sai nhiều với nhân vật mới
- Speaker sai nhiều với dòng không có ai nói (nobody)
- Voice match yếu ở trạng thái confusable
- Show dùng lại giọng AI cho nhiều nhân vật phụ
- `speaker_conf` của translator chỉ chép điểm voice
- NPC quay lại hay bị gán id mới
- Appearances ở chế độ auto chỉ dựa trên speaker đoán

## Nhận diện hình

- Tỷ lệ gọi đúng tên nhân vật thấp, nhiều box không nhận ra
- Talking sprite ít khi chỉ đúng speaker
- Picture veto chỉ sai người nói ngang với số lần sửa đúng
- Không tách được những cặp nhân vật luôn xuất hiện và cử động cùng nhau
- Nhân vật đứng một mình không có talking claim
- Cast stage chậm

## Dịch và evaluator

- Evaluator bắt được ít dòng mà reviewer viết lại
- Tiêu chí speaker của evaluator bắt được ít speaker sai
- Có dòng được dịch từ tiếng Trung sai
- Partial review đổi speaker mà không dịch lại đại từ
- Glossary chỉ có một nghĩa cho mỗi từ → [[2026-10-07 chia hai chế độ auto và human]]
- Script review sửa nhầm dòng đúng (表 là từ của show)
- Polyphone fallback chỉ áp dụng cho danh sách chữ ngắn

## Memory và học

- Memory sai chủ yếu đến từ nhân vật được tạo ở lần xuất hiện đầu tiên, chưa kiểm
- Dòng của chế độ auto có thể làm lỗi voice match tự củng cố
- Thay đổi đại từ không được parse trong code, phụ thuộc vào dreaming

## Đo lường

- Speaker benchmark chạy trên memory đã học từ các tập được audit
- Số dịch và evaluator chỉ so được giữa các lần re-run
- Chain run lệch replay từ ep010 do code probation cũ
- Gemini free tier hết quota theo ngày
