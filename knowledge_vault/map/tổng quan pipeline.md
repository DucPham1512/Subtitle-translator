---
date: 2026-10-07
type: map
tags: [map, pipeline]
---
# Tổng quan pipeline

## Trước tập 1

- **Memory bootstrap** — soạn nhân vật, cặp đại từ, glossary gốc và voice bank từ cast list, clip giọng, sprite → `data/bootstrap/seed_draft.json`, sau khi duyệt ghi vào memory.

## Mỗi tập

1. **Frame sampling + change detection** — tìm khung hình mà dải phụ đề thay đổi → `bands/`, `changes.jsonl`, `video.json`
2. **OCR** — đọc chữ Trung từ các dải đã lưu → `ocr_raw.jsonl`
3. **Event building** — gộp kết quả OCR theo khung thành sự kiện phụ đề có thời gian, đánh dấu dòng nghi không phải hội thoại → `events_raw.jsonl`
4. **OCR correction** — sửa lỗi chữ trông giống nhau bằng ngữ cảnh và glossary → `events.jsonl`
5. **Audio extraction** — tách âm thanh mono → `audio.wav`
6. **Voice match** — đề xuất speaker theo giọng, gom giọng mới thành nhân vật tự động → `speakers.jsonl`, `new_voices.json`, `voice_embeddings.npz`
6b. **Cast** — nhận diện nhân vật trên màn hình và sprite đang nói → `cast.jsonl`, `cast_embeddings.npy`
7. **Pinyin** — sinh pinyin tất định từ tiếng Trung đã sửa → `pinyin.jsonl`
8. **Scene windowing** — chia sự kiện thành cửa sổ cảnh → `windows.json`
9. **Translate + evaluate loop** — dịch sang tiếng Việt, chọn speaker/listener, chấm bằng rule check và LLM, dịch lại dòng hỏng → `translations.jsonl`, `evaluations.jsonl`, `memory_prefix.md`
10. **Sprite check** (tùy chọn) — giải speaker độ tin thấp bằng hình nhân vật → cập nhật `translations.jsonl`, `sprite.json`
11. **Script review** — soát cả tập: dòng lặp, nhiễu OCR, lỗi OCR trong hội thoại → `script_review.jsonl`
12. **Review gate** — auto: duyệt hết; human: tạo bản nháp và dừng chờ review → `approved.jsonl` + `edits.jsonl` (auto) hoặc `review_draft.jsonl` (human)
13. **Human review + finish** — reviewer sửa trong app, rồi chốt → `review_draft.jsonl`, rồi `approved.jsonl`, `edits.jsonl`
14. **Memory update** — Memory Manager ghi đề xuất đã duyệt, probation, lifecycle, briefing, commit git → memory DB + briefings
15. **Voice + sprite learning** — học lại voice bank và sprite bank từ dòng đã duyệt → voice bank, confusable pairs, sprite bank
16. **Render + deliver** — tạo ASS, che phụ đề gốc, burn-in, chuyển video vào folder output → `output.ass`, video hoàn chỉnh
17. **Report** — tổng hợp thời gian, chi phí, cờ, tỷ lệ → `report.md` (`cost.jsonl` ghi theo từng lệnh LLM)
18. **Cleanup** — xóa file tạm → (không có đầu ra; `state.json` đánh dấu `purged`)

Bước 14–18 chạy trong `finish-review`, hoặc ngay sau bước 12 ở chế độ auto.

## Giữa các tập

- **Dreaming** (offline) — gom sửa của reviewer thành đề xuất glossary, cặp đại từ, style rule, nén briefing → `data/memory/dream_proposals.json`

# Các pipeline cơ bản
## 1. Nhận diện người nói
description....
[[speaker detection.drawio]]
## 2. Nhận diện hình ảnh
[[sprite matching.drawio]]
## 3. Nhận diện giọng nói
[[voice matching.drawio]]
## 4. Vòng lặp dịch
[[translation loop.drawio]]