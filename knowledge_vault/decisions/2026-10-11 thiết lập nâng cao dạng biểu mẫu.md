---
date: 2026-10-11
type: decision
status: done
tags: [decision, app, settings, config]
---
# 2026-10-11 thiết lập nâng cao dạng biểu mẫu

Spec: `.claude/rules/app.md` mục 6.9 (Advanced); cách lưu: `.claude/rules/config.md` mục 5.2a.

## Quyết định (chủ dự án chọn)

Tab Advanced của Settings không còn là ô YAML thô mà là biểu mẫu cho mọi thiết lập (192 trường, 27 mục):

- **Điều khiển theo loại trường:** giá trị cố định → danh sách thả xuống; danh sách không cố định → thẻ (thêm bằng Enter hoặc dấu phẩy, xoá bằng ×, như thẻ trong Jira); chữ → ô nhập; số → ô số; bật / tắt → ô đánh dấu; đường dẫn → ô nhập + nút Chọn….
- **Tập giá trị đã biết cũng là danh sách thả xuống:** văn phong dịch, baseline (thêm "(none)"); gợi ý tên cờ cho `voice.learn_auto_allowed_flags`.
- **LLM:** mỗi vai (translator, evaluator, utility) một nhóm ô (base URL, tên khoá, model); bảng giá một dòng mỗi model, có Thêm / Xoá dòng.
- **Một biểu mẫu, tự lưu đúng file:** biểu mẫu hiện thiết lập hiệu lực của bộ phim đang chọn; mỗi trường có nhãn "bộ phim này" hoặc "dùng chung", và khi lưu, mỗi thay đổi vào `series.yaml` hoặc `config.yaml` theo luật sẵn có.
- **Bố cục:** danh sách mục bên trái kèm ô tìm kiếm (lọc theo tên khoá hoặc chú thích); bên phải là các trường của mục, dưới mỗi trường là chú thích.
- **Giữ ô YAML thô** sau nút "Sửa dạng YAML…".
- **Giữ nguyên chú thích khi lưu:** chỉ giá trị trên dòng của khoá đó được viết lại (`subagent/yaml_edit.py`), không thêm dependency.

## Lý do

- `config.yaml` có một chú thích cho mỗi giá trị đã tinh chỉnh (số đo phía sau nó). Cách lưu cũ (`yaml.safe_dump`) xoá hết chú thích ở lần lưu đầu tiên. Lỗi này đã có từ trước, ở tab General và khi căn chỉnh phụ đề trong app, và giờ cũng được sửa vì mọi lần lưu đều đi qua cách mới.
- Chú thích hiện trong biểu mẫu lấy từ chính file YAML và ghi chú cạnh trường trong `config.py`, nên không phải viết lại ở chỗ thứ ba.

## Kiểm tra

- Trên `config.yaml` và `series.yaml` thật (chỉ trong bộ nhớ, không ghi): đổi từng giá trị trong 178 giá trị, kết quả đọc lại đúng, không giá trị nào khác đổi, không mất chú thích nào: 0 lỗi.
- Mở biểu mẫu trên cấu hình thật: không có thay đổi nào được báo (đọc rồi ghi lại không làm đổi gì).
- Test mới: sửa trong chỗ (giữ chú thích, danh sách, khoá trong mapping dạng `{}`, khoá mới, khoá có dấu chấm như tên model, xoá, thay bảng giá; file hỏng ở chỗ khác thì báo lỗi chứ không ghi); biểu mẫu (năm loại trường, lưu đúng file, chú thích còn nguyên); ô thẻ.

Related: [2026-10-11 nhiều bộ phim trong một dự án](2026-10-11%20nhi%E1%BB%81u%20b%E1%BB%99%20phim%20trong%20m%E1%BB%99t%20d%E1%BB%B1%20%C3%A1n.md)
