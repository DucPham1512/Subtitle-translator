---
date: 2026-10-21
type: decision
status: done
tags: [decision, refactor, architecture]
---
# 2026-10-21 tách code thành module

Nhánh `refactor/modules`. Quy tắc hiện hành: `.claude/rules/architecture.md` mục 3.3 (sơ đồ thư mục) và 3.4 (ranh giới module), được `tests/test_architecture.py` kiểm.

## Kiến trúc trước khi tách

- **Lúc chạy:** pipeline kiểu ống nối (pipes and filters) qua file. Bảng `STAGES` liệt kê từng tầng (đọc gì, ghi gì, phụ thuộc tầng nào, khoá config nào); `Runner` chạy lần lượt, mỗi tầng ghi artifact vào `work/<ep>/` và được bỏ qua khi hash đầu vào trong `state.json` không đổi. `EpisodeContext` đưa cho mọi tầng config, đường dẫn, tập phim, LLM, tiến độ. Memory: đọc qua `MemoryStore`, ghi chỉ qua `MemoryManager`. CLI là nơi lắp ráp; app là client riêng (chạy job CLI qua QProcess, đọc tiến độ JSON) cộng thêm một lớp `services.py` gọi thẳng vào core.
- **Code:** chia theo vai trò kỹ thuật (`stages/`, `memory/`, `cli/`) cộng khoảng 30 file nằm ngoài cùng. Mỗi tính năng bị rải qua nhiều nơi; ví dụ phần giọng nói nằm ở `stages/voice.py`, `memory/voice_learning.py`, `memory/bootstrap.py`, `memory/manager/candidates.py`, `partial_review.py`, `characters.py`.
- **Đo trên đồ thị import:**
  - 3 vòng import bị che bởi import trong hàm: `stages.ocr` ↔ `subtitle_style`; `memory.manager` ↔ `voice_learning` ↔ `bootstrap`; `pipeline` ↔ `baseline` / `benchmark` / `ocr_benchmark`.
  - Memory phụ thuộc ngược vào stages (bộ nhúng giọng, nhận diện hình).
  - Tên riêng tư dùng chéo file: `pipeline._lazy`, `benchmark._sandbox_paths`, `translate._rank`, `events._relatedness`; `MemoryManager.__all__` xuất cả `_fetch`, `_insert`, ….
  - 9 màn hình của app gọi thẳng vào core, bỏ qua `services.py`.

## Quyết định (chủ dự án chọn)

- **Chia theo tính năng**, mỗi module một thư mục: kernel, settings, infra, llm, workspace, memory, ocr, voice, cast, translation, bootstrap, review, output, pipeline, bench, cli.
- **Giao tiếp qua giao diện:** `__init__.py` của mỗi module là API công khai (`__all__`). Module khác chỉ import `from subagent.<module> import tên`, không đi vào file con, không dùng tên `_`. Kiểm bằng một test, không thêm thư viện.
- **App chỉ đi qua `app/services/`**; màn hình chỉ được import `subagent.kernel` (kiểu dữ liệu, lỗi).
- Kiểm hành vi trên dữ liệu thật (so artifact, `bench score`) được **bỏ qua lần này**, vì dữ liệu series-1 đã mất khi chuyển sang Linux ([2026-10-21 chuyển sang Linux](2026-10-21%20chuy%E1%BB%83n%20sang%20Linux.md)). Bộ test là phép kiểm duy nhất.

## Đã làm

1. Gỡ các chỗ dính nhau trước khi chuyển file:
   - `memory/evidence.py` nhận `trusted_auto_lines`, `load_line_voices`, nên Memory Manager không còn import code giọng nói.
   - Hàm clip / tâm giọng chuyển từ bootstrap sang voice.
   - Pipeline nhận hook `after_finish`; việc sao chép baseline do CLI gắn vào, nên pipeline không còn import bench.
   - Thêm `run_stage` công khai; `_rank` → `rank_attempt`; `_relatedness` → `textutil.relatedness`.
2. Chuyển file từng nhóm bằng `git mv` (giữ lịch sử), mỗi nhóm một commit, test qua sau từng nhóm. `pipeline.py` tách thành `stages.py`, `runner.py`, `report.py`. `series.py` vào workspace vì nó cần khoá job (infra).
3. API của từng module: 442 import chéo chuyển về cấp module. Tên trùng giữa hai file con được đặt tên riêng: `render_video`, `render_benchmark`, `calibrate_band`, `calibrate_style`.
4. `app/services/` (`core.py` + một file cho mỗi nhóm màn hình).
5. Test kiểm ranh giới (`tests/test_architecture.py`). Đã thử cố tình vi phạm: test báo đúng file, dòng và lý do.

## Đo lường

- 261 test qua (thêm 4 test kiến trúc), `ruff` sạch, `python -m subagent check` qua, app mở được.
- **Thời gian mở app:** khi API module import file con ngay lập tức, mở app chậm hơn khoảng 35 ms (225 → 260 ms, nạp thêm `pysubs2`). Chuyển sang xuất tên lười (PEP 562: file con chỉ nạp khi tên được dùng lần đầu) đưa về lại 225 ms.

## Lưu ý

- Test vá (monkeypatch) một hàm ở nơi nó được tìm: thuộc tính của gói khi nơi gọi ở module khác (`subagent.infra.extract_clip`), thuộc tính của file con khi nơi gọi cùng module. Hàm `run` của các tầng vẫn vá ở file của tầng.
- Chưa tách bộ nhúng giọng ra `voice/engine.py` như kế hoạch ban đầu: không cần cho việc gỡ phụ thuộc, và sẽ phải sửa thêm nhiều chỗ vá trong test.
- Sơ đồ trong `knowledge_vault/diagrams/` sẽ cập nhật sau khi nhánh được merge (CLAUDE.md mục 12).

Related: [2026-10-11 tái cấu trúc code](../11-10-2026/2026-10-11%20t%C3%A1i%20c%E1%BA%A5u%20tr%C3%BAc%20code.md), [thiết kế - lý do các lựa chọn](../thi%E1%BA%BFt%20k%E1%BA%BF%20-%20l%C3%BD%20do%20c%C3%A1c%20l%E1%BB%B1a%20ch%E1%BB%8Dn.md)
