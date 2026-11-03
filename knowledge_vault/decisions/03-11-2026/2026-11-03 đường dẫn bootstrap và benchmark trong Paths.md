---
date: 2026-11-03
type: decision
status: done
tags: [decision, refactor, paths]
---
# 2026-11-03 đường dẫn bootstrap và benchmark trong Paths

Skill `graph-refactor`, nhánh `refactor/graph-pass`.

## Quyết định

Thêm bốn thuộc tính vào `Paths` (`subagent/settings/config.py`), cùng kiểu với `card_pins`, `llm_cache`…:

- `bootstrap_voices` (`bootstrap/voices/`), `bootstrap_sprites` (`bootstrap/sprites/`), `cast_file` (`bootstrap/cast.md`);
- `benchmarks` (`<work>/_benchmark/`).

Thay 12 chỗ ghép đường dẫn bằng tay trong `cast/sprite.py`, `cast/card.py`, `voice/voice.py`, `bootstrap/seed.py`, `bench/benchmark.py`, `app/services/core.py` và `app/views/bootstrap.py`. Test vẫn tự ghép đường dẫn như cũ, vẫn đúng.

## Lý do

Khi kiểm lead "BootstrapView biết bố cục thư mục" thì thấy cùng một bố cục được ghép bằng tay ở 3–5 chỗ, trải qua nhiều module, có cả view của app. CLAUDE.md §9 yêu cầu không hardcode đường dẫn; `Paths` là nơi giữ bố cục dự án. Đã kiểm: không có code nào gán lại `paths.work` / `paths.bootstrap` sau khi tạo (sandbox của bench tạo `Paths` mới), nên các thuộc tính suy ra không bị lệch.

File của thư mục memory (`dream_state.json`, `speaker_corrections.jsonl`…) chỉ lặp lại bên trong module memory nên để nguyên.

## Kết quả

ruff sạch; 268 test qua trước và sau; +17 / −14 dòng ở 8 file. Không còn chuỗi `"voices"` / `"sprites"` / `"cast.md"` / `"_benchmark"` nào ghép đường dẫn trong code chạy thật, ngoài định nghĩa trong `Paths`.

Phát hiện, để nguyên (sửa nó là đổi hành vi): `BootstrapView._save_sprite` đặt tên template theo số file đang có (`template_<n+1>`), nên nếu một template ở giữa bị xoá ngoài app thì template mới sẽ ghi đè file cuối.
