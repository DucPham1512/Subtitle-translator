---
date: 2026-11-03
type: decision
status: done
tags: [decision, claude-code, graphify]
---
# 2026-11-03 .graphifyignore

## Quyết định

Thêm `.graphifyignore` ở gốc dự án (cú pháp giống `.gitignore`; graphify đọc `.gitignore` trước, file này chỉ loại thêm). Graphify bỏ qua những nội dung được quản lý từ bên ngoài dự án:

- Toàn bộ `.claude/skills/`: các skill bên thứ ba (claude-md-optimizer, defuddle, frontend-design, json-canvas, knap, obsidian-*, refractor) và cả `pipeline-improvement-experiments` (quy trình làm việc của Claude Code, không phải code của dự án).
- `.claude/settings.json`: thiết lập của Claude Code, không phải code của dự án.
- Media của bộ phim: ảnh nhân vật, sprite bootstrap, mẫu giọng (`data/series/**/*.png`, `data/series/**/*.wav`, 114 file). Loại theo đuôi file chứ không theo thư mục, để giữ `pin.json` trong thẻ nhân vật (code đọc file này).
- Font Noto đi kèm và giấy phép SIL OFL: `app/fonts/`, `data/series/*/fonts/`.
- Tài liệu: spec `.claude/rules/`, `CLAUDE.md`, `README.md`, mẫu `data/series/*/bootstrap/cast.example.md`.
- Toàn bộ `knowledge_vault/`.

Vẫn giữ những file mà code đọc lúc chạy: `prompts/`, prompt riêng của bộ phim (`data/series/*/prompts/`), `data/series/*/bootstrap/cast.md` (`generate_seed` trong `subagent/bootstrap/seed.py` đưa nó vào lệnh gọi LLM tạo memory ban đầu), config, `requirements.txt`. Không có code nào đọc `cast.example.md`; chỉ README trỏ tới nó.

## Lý do

Lần chạy graphify đầu tiên (2026-11-03) phải loại tay các file này. Chúng không nói gì về dự án và chỉ làm đồ thị rối thêm: riêng các skill bên thứ ba có khoảng 5.000 dòng và 26 tài liệu eval. Ghi vào file thì những lần build sau, kể cả `--update`, loại chúng tự động.

Loại vault và tài liệu (quyết định của chủ dự án): đồ thị phải phản ánh đúng mã nguồn của dự án, không lan man sang tài liệu. Trong đồ thị đầu tiên, vault chiếm 35 file và 183 / 3.667 node; 36 cạnh nối vault với phần còn lại, tất cả đều tới spec và prompt, không tới code.

## Kết quả

Build lại với `force` (`--update` không thu nhỏ đồ thị): 3.667 → 3.251 node, 11.892 → 11.197 cạnh, 171 → 142 cộng đồng. Không còn node nào từ vault, spec, README, CLAUDE.md hay skill. Phần tài liệu còn lại lấy từ cache nên không tốn token.

Media bị loại vì nếu để lại, mỗi ảnh tốn một lượt vision và mỗi mẫu giọng tốn một lần chạy Whisper, mà chúng không nói gì về code. Hai lần build đầu đã loại media bằng tay; giờ file này tự loại.

Related: [2026-10-21 rút gọn skill refactor](../21-10-2026/2026-10-21%20r%C3%BAt%20g%E1%BB%8Dn%20skill%20refactor.md)
