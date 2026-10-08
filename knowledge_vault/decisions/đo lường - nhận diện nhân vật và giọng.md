---
date: 2026-10-08
type: measurement
tags: [measurement, cast, voice, speaker]
---
# Đo lường - nhận diện nhân vật và giọng

Chuyển từ CLAUDE.md (mục 5.8b, 5.11, 6.4, NFR-P1b) ngày 2026-10-08. Hành vi hiện tại nằm ở `.claude/rules/voice-cast.md`, `.claude/rules/translation.md`, `.claude/rules/app.md`.

## Vì sao có cast (5.8b)

Chỉ dựa vào giọng thì không tách được rất nhiều nhân vật phụ, và phim dùng lại giọng AI giữa các nhân vật. Hình ảnh thì tách được: nhân vật nhận ra được nhờ trang phục qua các tập, và sprite đang nói là sprite chuyển động.

## Kết quả đo

- Replay ep001–005 với speaker đã duyệt: sprite đang nói được gọi đúng tên 4/5, 6/14, 29/39, 29/33 (ep002–ep005); speaker nằm trong số nhân vật nhận ra được ở 25–38% số dòng; độ phủ tăng theo kho sprite. Kho của dàn nhân vật chính sạch, trừ những cặp luôn xuất hiện và cử động cùng nhau.
- Tầng cast mất khoảng 90 s cho một tập 5 phút trên RTX 3060.

## Picture veto (5.11, `translate.picture_veto`)

Tắt mặc định. Đo trên ep007–011 (100 dòng gold): độ chính xác speaker khi tắt 78.5%, `recognised` 78.7%, `any` 77.4%; trên các dòng mà giọng và hình bất đồng: 47 / 37 / 33%. Veto sửa được các trường hợp dùng chung giọng, nhưng hình cũng gọi sai người nói thường xuyên như vậy, nên chờ nhận diện sprite đang nói tốt hơn.

## Thẻ nhân vật (6.4)

Thẻ "Who is this character?" được làm vì một NPC quay lại thường bị gán id mới khi id cũ không nhận ra được (quyết định của chủ dự án ngày 2026-10-03).

Related: [đo lường - benchmark suite](đo%20lường%20-%20benchmark%20suite.md), [thiết kế - lý do các lựa chọn](thiết%20kế%20-%20lý%20do%20các%20lựa%20chọn.md)
