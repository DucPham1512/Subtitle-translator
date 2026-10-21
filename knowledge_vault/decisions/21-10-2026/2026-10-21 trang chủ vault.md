---
date: 2026-10-21
type: decision
status: done
tags: [decision, vault]
---
# 2026-10-21 trang chủ vault

## Quyết định

- Thêm `Home.md` ở gốc vault: giới thiệu ngắn vault dùng để làm gì, bảng "bắt đầu nhanh", liên kết tới sơ đồ, đo lường, và quy ước tổ chức thư mục.
- Danh sách quyết định, việc đang mở, ghi chú tham khảo và changelog là các view của `Home.base` (Bases, plugin lõi của Obsidian, đã bật) nhúng vào trang. Chúng đọc `date`, `status`, `type`, `tags` trong frontmatter.
- Liên kết dùng `[[wikilink]]` theo tên file, nên không hỏng khi ghi chú đổi thư mục.

## Lý do

- Trang chủ là điểm vào duy nhất; không phải nhớ ghi chú nào nằm ở thư mục ngày nào.
- Danh sách viết tay sẽ lệch dần mỗi khi thêm quyết định; Base tự cập nhật, và giữ quy tắc "một sự thật một chỗ" (trạng thái chỉ nằm trong frontmatter của từng ghi chú).

## Lưu ý

- Obsidian không có sẵn tuỳ chọn "mở trang chủ khi khởi động"; có thể ghim `Home.md` vào Bookmarks.
- Ghi chú quyết định mới cần có `date` và `status` trong frontmatter để hiện đúng trong bảng.

Related: [2026-10-21 thư mục quyết định theo ngày](2026-10-21%20th%C6%B0%20m%E1%BB%A5c%20quy%E1%BA%BFt%20%C4%91%E1%BB%8Bnh%20theo%20ng%C3%A0y.md)
