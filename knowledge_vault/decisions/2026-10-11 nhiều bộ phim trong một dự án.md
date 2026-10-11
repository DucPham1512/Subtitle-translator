---
date: 2026-10-11
type: decision
status: done
tags: [decision, series, config, architecture]
---
# 2026-10-11 nhiều bộ phim trong một dự án

Spec: `.claude/rules/config.md` mục 5.2a; app: `.claude/rules/app.md` mục 6.2, 6.9.

## Quyết định (chủ dự án chọn, 2026-10-11)

- **Mỗi bộ phim một thư mục** `data/series/<slug>/`: `memory/` (repo git riêng), `bootstrap/`, `episodes/index.json`, `character_cards/`, `fonts/` (font phụ đề), `prompts/` (ghi chú riêng của bộ phim) và `series.yaml`.
- **Dùng chung:** `config.yaml`, `.env`, `prompts/` (prompt chung), `cache/`, `app/fonts/` (font của giao diện app, bản riêng, không phụ thuộc bộ phim nào).
- **Cấu hình:** `config.yaml` giữ phần dùng chung; `series.yaml` của mỗi bộ phim ghi đè bất kỳ mục nào nó cần. Kết quả gộp được kiểm tra như một cấu hình. Thiết lập lưu từ app (Settings, căn chỉnh phụ đề) tự vào đúng file: mục mô tả bộ phim (show, video, ocr, non_dialogue, voice, cast, script_review, paths, baseline, bench) vào `series.yaml`, phần còn lại vào `config.yaml`.
- **Prompt:** prompt chung ở thư mục gốc; phần riêng của một bộ phim là ghi chú nối vào cuối dưới tiêu đề "Series notes". Sửa prompt chung thì mọi bộ phim đều được hưởng. Đặc điểm của bộ phim hiện tại (font vẽ 了 giống số 7; chữ lạ 楚, 姬, 史 từ đồ vật trên màn hình; tiếng lóng 史 = 屎) đã chuyển từ prompt script review chung sang ghi chú của `series-1`.
- **Thư mục làm việc:** bộ phim mới dùng `<work_dir>/<slug>/` (mã tập `ep001` không bị trùng giữa các bộ phim). `series-1` giữ nguyên `E:/Video Data/Raw` qua `series.yaml`, nên không phải di chuyển gì (các thư mục tập, `_baseline`, `_suite`).
- **Chọn bộ phim:** app có ô chọn bộ phim ở đầu thanh bên; đổi bộ phim thì dựng lại cửa sổ (mọi màn hình tải lại; không cho đổi khi đang có job). "Bộ phim mới…" hỏi mã, tên, văn phong dịch, thư mục làm việc rồi mở màn Bootstrap. CLI: `--series SLUG`, mặc định `series.default`; lệnh `series list | add | default | rename | migrate`.
- **Mã của bộ phim hiện tại:** `series-1` (tên tạm; đổi bằng `series rename`).
- **Làm cùng lúc:** một bộ phim mỗi lần trong app; job của các bộ phim khác nhau có thể chạy song song vì khoá job và memory là riêng từng bộ phim (GPU dùng chung).

## Lý do

- Mọi đường dẫn trong code đã đi qua một đối tượng `Paths`, nên chỉ cần `Paths` biết bộ phim đang chọn là gần như toàn bộ pipeline dùng được cho nhiều bộ phim; chỉ thẻ nhân vật là đường dẫn cứng phải sửa.
- Ghi đè theo mục (thay vì một file cấu hình đầy đủ cho mỗi bộ phim) để khoá API, giá, ngân sách, cách render chỉ phải đổi một chỗ.
- Ghi chú nối thêm (thay vì thay cả prompt) để bản sửa prompt chung đến được mọi bộ phim.

## Chuyển dữ liệu hiện có (2026-10-11)

- `python -m subagent series migrate series-1`: chuyển `data/memory`, `data/bootstrap`, `data/episodes`, `data/character_cards`, `fonts/` vào `data/series/series-1/`; các mục mô tả bộ phim của `config.yaml` sang `series.yaml` (giữ nguyên chú thích); thẻ nhân vật trong cache vào `cache/character_cards/series-1/`.
- Kiểm tra sau khi chuyển: cấu hình gộp **giống hệt** cấu hình cũ; memory còn 20 nhân vật và lịch sử git (`7379c28 manual edit: 5 changes`); registry 17 tập; thư mục làm việc vẫn là `E:\Video Data\Raw`; tìm thấy baseline, subtitle style và `cast.md`.
- `.gitignore` thêm `data/series/*/memory/` và `data/series/*/episodes/` (như `data/memory/`, `data/episodes/` trước đây).

## Ảnh hưởng cần biết

- Prompt script review của `series-1` giờ là prompt chung + ghi chú (nội dung tương đương, câu chữ khác), nên hash đầu vào của tầng script review đổi: lần chạy tới của một tập sẽ chạy lại script review (một lệnh gọi mỗi tập) và cache LLM không dùng lại được cho tầng này.
- Phần code kiểm tra 7 / 了 của script review vẫn để chung: nó chỉ chặn những lần sửa làm mất chữ số hoặc biến số thật thành 了, nên với phim khác nó không bao giờ bật.

Related: [điểm yếu đã biết](điểm%20yếu%20đã%20biết.md), [thiết kế - lý do các lựa chọn](thiết%20kế%20-%20lý%20do%20các%20lựa%20chọn.md)
