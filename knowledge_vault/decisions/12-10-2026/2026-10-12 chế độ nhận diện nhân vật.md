---
date: 2026-10-12
type: decision
status: done
tags: [decision, pronouns, character-identification, series]
---
# 2026-10-12 chế độ nhận diện nhân vật (bật / tắt)

Nhánh `feat/pronoun-mode`. Spec: mục 5.11a trong `.claude/rules/translation.md`.

## Quyết định (chủ dự án chọn)

Mỗi bộ phim chọn một trong hai cách quyết định xưng hô:

- **Bật** (`show.character_identification: true`): chương trình tự tìm người nói / người nghe (giọng, hình) và dùng bảng xưng hô theo từng cặp. Giống hệt trước đây. series-1 giữ chế độ này.
- **Tắt**: không nhận diện nhân vật; mọi câu dùng **một cặp xưng hô mặc định** (`show.self_term` / `show.address_term`, ví dụ ta / ngươi).

Các lựa chọn cụ thể:

- Công tắc **theo bộ phim** (series.yaml), không dùng chung.
- Cặp mặc định là **một cặp cho cả bộ phim**, nhập khi tạo bộ phim. Bắt buộc khi tắt.
- Cửa sổ Bộ phim mới: ô **Nhận diện nhân vật** mặc định *không đánh dấu* (tắt), nên luôn hỏi cặp xưng hô. Lệnh `series add` bắt chọn `--identify-characters` hoặc `--pronouns SELF ADDRESS`.
- Khi tắt, **bỏ qua và ẩn** người nói / người nghe: không chạy audio, voice, cast, sprite check. Translator không nhận thông tin người nói. Màn Review ẩn hàng người nói, thẻ nhân vật, cột và bộ lọc người nói, tab On screen và Partial review.
- Khi tắt, cũng tắt:
  - luật kiểm đại từ và bảng xưng hô trong prompt;
  - học giọng và học sprite;
  - nhân vật mới, thử việc (probation), cập nhật nhân vật, lifecycle.
  - Thuật ngữ, style rules, line decisions, briefing vẫn chạy.

## Cách làm

- **Prompt:** khối `<!-- if:identify -->` / `<!-- if:default_pair -->` trong `translator_system.md` và `evaluator_system.md`. Dòng đánh dấu bị xoá, nên prompt ở chế độ bật **giống từng byte** với trước (đã kiểm). Cache prompt của series-1 không đổi.
- **Ở chế độ tắt:**
  - Prompt yêu cầu dùng đúng cặp mặc định cho ngôi thứ nhất / thứ hai. Cặp này thắng hướng dẫn xưng hô của văn phong. Tên, danh xưng (师父, 宗主…) vẫn dịch như thường.
  - Evaluator chấm `pronouns` theo cặp mặc định và bỏ tiêu chí `speaker`.
- **Stage bị tắt:** ghi trạng thái `off` trong `state.json`. Đổi chế độ thì translate và các bước sau chạy lại.

## Chưa làm

- Không có luật kiểm (rule check) bằng code cho cặp mặc định: chỉ prompt và evaluator. Thêm sau nếu thấy translator hay lệch cặp.
- Bootstrap vẫn hiện bước mẫu giọng / sprite; ở chế độ tắt có thể bỏ qua.

Related: [thiết kế - lý do các lựa chọn](../thiết%20kế%20-%20lý%20do%20các%20lựa%20chọn.md), [2026-10-11 tạo văn phong dịch mới](../11-10-2026/2026-10-11%20t%E1%BA%A1o%20v%C4%83n%20phong%20d%E1%BB%8Bch%20m%E1%BB%9Bi.md)
