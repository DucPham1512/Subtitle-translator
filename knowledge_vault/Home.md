---
date: 2026-10-21
type: home
tags: [home]
---
# Trang chủ

Vault này là **nhật ký quyết định** của Subtitle Agent: pipeline chạy trên máy, dịch phụ đề tiếng Trung in cứng (hardsub) của phim hoạt hình sang tiếng Việt, thêm pinyin rồi in lại lên video. Vault giữ **lý do, số đo và lịch sử**; hành vi hiện tại nằm trong code, `CLAUDE.md`, `.claude/rules/` và `config.yaml` (ngoài vault). Claude Code là bên ghi duy nhất.

## Bắt đầu nhanh

| Muốn biết | Mở |
|---|---|
| Pipeline gồm những tầng nào | [[tổng quan pipeline]] |
| Pipeline trông thế nào | [[sơ đồ pipeline]] |
| Vì sao thiết kế như vậy | [[thiết kế - lý do các lựa chọn]] |
| Còn lỗi gì, đang làm gì | [[điểm yếu đã biết]] |
| Đã làm theo thứ tự nào | [[lịch sử - thứ tự triển khai và dữ kiện dự án]] |
| Hôm nay / gần đây đã đổi gì | thư mục `changelog/` (bảng ở cuối trang) |

## Sơ đồ

Mở trong draw.io hoặc VS Code.

- [[pipeline.drawio|Pipeline]]
- [[modules.drawio|Các module của code]]
- [[speaker detection.drawio|Nhận diện người nói]]
- [[voice matching.drawio|Khớp giọng]]
- [[sprite matching.drawio|Nhận diện hình (sprite)]]
- [[translation loop.drawio|Vòng lặp dịch]]

## Đo lường

- [[đo lường - OCR|OCR]]
- [[đo lường - nhận diện nhân vật và giọng|Nhận diện nhân vật và giọng]]
- [[đo lường - script review|Script review]]
- [[đo lường - benchmark suite|Benchmark suite]]

## Việc đang mở

Ghi chú có `status` khác `done` / `rejected` (đề xuất, tạm dừng, nháp).

![[Home.base#Đang mở]]

## Quyết định theo ngày

![[Home.base#Quyết định]]

## Ghi chú tham khảo

Ghi chú không gắn với một ngày, được cập nhật liên tục.

![[Home.base#Tham khảo]]

## Changelog

![[Home.base#Changelog]]

## Cách tổ chức vault

| Thư mục | Nội dung | Đặt tên |
|---|---|---|
| `decisions/dd-mm-yyyy/` | Mỗi thay đổi hoặc quyết định một ghi chú: ngày, quyết định, lý do, số đo | `yyyy-mm-dd <tên>.md`, trong thư mục của ngày quyết định |
| `decisions/` (gốc) | Ghi chú tham khảo không có ngày: đo lường, thiết kế, lịch sử, điểm yếu | `<loại> - <chủ đề>.md` |
| `changelog/` | Mỗi phiên làm việc một dòng, trỏ tới ghi chú quyết định | `yyyy-mm-dd.md` |
| `map/` | Mô tả pipeline bằng chữ | |
| `diagrams/` | Sơ đồ draw.io, sửa tại chỗ sau khi nhánh được merge | `<chủ đề>.drawio` |

Các bảng trên trang này là Base ([[Home.base]]): ghi chú mới có `date` / `status` trong frontmatter tự hiện ra, không cần sửa trang này.
