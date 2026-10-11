---
date: 2026-10-11
type: decision
status: done
tags: [decision, translation, series, register]
---
# 2026-10-11 tạo văn phong dịch mới

Spec: `.claude/rules/translation.md` mục 5.11 (Translation styles); app: `.claude/rules/app.md` mục 6.2.

## Vấn đề

Văn phong dịch (register) là một khối chữ nằm trong `prompts/translator_system.md`, và chỉ có một khối: cổ trang / tiên hiệp. Bộ phim mới không chọn được văn phong khác. Danh sách từ xưng hô mà luật kiểm đại từ dùng (`translate.pronoun_terms`) lại nằm chung trong `config.yaml`, nên một phim hiện đại (anh / em, tôi / bạn) cũng bị kiểm theo danh sách cổ trang.

## Quyết định (chủ dự án chọn)

- **Mỗi văn phong là một file dùng chung** `prompts/registers/<id>.md`: phần đầu YAML (`name`, `pronoun_terms`) và đoạn hướng dẫn cho translator. Mọi bộ phim đều chọn được; phim hiện đại thứ hai có thể dùng lại văn phong của phim thứ nhất.
- **Văn phong mang theo từ xưng hô của nó:** khi cấu hình gộp không đặt `translate.pronoun_terms`, danh sách lấy từ văn phong của bộ phim. Đặt danh sách riêng trong `series.yaml` vẫn ghi đè được.
- **Tạo ngay trong cửa sổ "Bộ phim mới":** nút "Văn phong mới…" mở hộp thoại: mã, tên, từ xưng hô, và hướng dẫn cho translator (có sẵn mẫu: bối cảnh, tên và thuật ngữ, hệ xưng hô, giọng văn). Lưu xong, văn phong được chọn sẵn cho bộ phim đang tạo. Không bao giờ ghi đè một văn phong đã có (bộ phim khác có thể đang dùng).
- **Cổ trang / tiên hiệp** chuyển từ prompt translator sang `prompts/registers/co_trang_tien_hiep.md`, cùng 31 từ xưng hô trước đây nằm trong `config.yaml`. Prompt translator chỉ còn chỗ trống `{{register}}`.

## Kiểm tra

- Prompt translator sau khi ghép văn phong **giống hệt từng byte** prompt cũ, nên cache LLM vẫn dùng được.
- Danh sách từ xưng hô hiệu lực của `series-1` không đổi (31 từ).
- Hash đầu vào của tầng dịch giờ tính cả file văn phong: sửa văn phong thì các tập chạy sau sẽ dịch lại. Lần đổi cấu trúc này làm hash thay đổi một lần (file prompt đổi), nhưng cache LLM vẫn khớp nên dịch lại không tốn thêm.
- Test mới: lưu, liệt kê, không ghi đè; bộ phim nhận chữ và từ xưng hô của văn phong; danh sách riêng ghi đè được; hộp thoại trong app tạo văn phong và chọn sẵn nó.

Related: [2026-10-11 nhiều bộ phim trong một dự án](2026-10-11%20nhi%E1%BB%81u%20b%E1%BB%99%20phim%20trong%20m%E1%BB%99t%20d%E1%BB%B1%20%C3%A1n.md)
