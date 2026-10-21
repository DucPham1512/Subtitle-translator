---
date: 2026-10-21
type: decision
status: done
tags: [decision, app, preview, linux]
---
# 2026-10-21 xem trước video trên Linux

Sau khi chuyển sang Linux ([2026-10-21 chuyển sang Linux](2026-10-21%20chuy%E1%BB%83n%20sang%20Linux.md)), trình phát xem trước trong app không chạy. Spec: `.claude/rules/app.md` mục 6.5.

## Nguyên nhân (ba lỗi, không phải một)

1. Chưa cài libmpv. Trên Linux libmpv là gói hệ thống (`libmpv2` trên Ubuntu / Debian), không phải file `libmpv-2.dll` cạnh app.
2. Máy dùng Wayland. App nhúng mpv vào widget bằng window id, cách này chỉ chạy trên X11.
3. `LC_NUMERIC=vi_VN.UTF-8`. Qt áp locale hệ thống khi mở app, còn libmpv từ chối khởi động nếu locale số không phải C.
4. (Tìm ra khi kiểm tra sau khi cài libmpv.) Dù app đã chạy qua XWayland, mpv vẫn thấy `WAYLAND_DISPLAY` nên tự chọn backend Wayland, bỏ qua window id và vẽ ở một cửa sổ riêng: widget xem trước không có cửa sổ con nào.

## Quyết định

- `app/__main__.py`: trên Linux, khi đang ở Wayland và có XWayland (`DISPLAY`), app chạy qua XWayland (`QT_QPA_PLATFORM=xcb`). Nếu người dùng tự đặt `QT_QPA_PLATFORM` thì giữ nguyên.
- `app/preview.py`: đặt `LC_NUMERIC` về `C` ngay trước khi tạo trình phát mpv. Chỉ ảnh hưởng cách C định dạng số; Python và giao diện Qt không đổi.
- `app/preview.py`: khi app chạy qua XWayland (`xcb`) trên Linux, mpv dùng backend X11 (`gpu-context=x11egl`).
- Thông báo "không tải được libmpv" giờ theo hệ điều hành: Windows vẫn hướng dẫn tải `libmpv-2.dll`, Linux hướng dẫn `sudo apt install libmpv2`. Đã thêm bản tiếng Việt và biên dịch lại `.qm`.
- README thêm hướng dẫn cho Linux.

## Lưu ý

- Dưới XWayland, nếu màn hình đặt tỉ lệ phóng không nguyên (vd. 125%), chữ trong app có thể hơi mờ. Cách thay thế triệt để là vẽ mpv qua OpenGL (render API) thay vì nhúng window id; chưa làm vì lớn hơn nhiều.
- Kiểm tra: 257 test qua, `ruff` sạch. Sau khi cài `libmpv2` (0.41.0): chạy `PreviewWidget` thật trên màn hình với video ep001, bộ lọc che phụ đề thật và một file ASS thử dựng bằng `build_ass`. Cửa sổ mpv nằm trong widget, `gpu-next`, 30 fps, 0 khung bị bỏ; ảnh chụp màn hình cho thấy dải phụ đề gốc được làm mờ, pinyin và tiếng Việt đủ dấu hiện đúng. Ở máy này tỉ lệ màn hình là 2× nên chữ không bị mờ.
