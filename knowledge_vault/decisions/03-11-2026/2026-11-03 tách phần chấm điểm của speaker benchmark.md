---
date: 2026-11-03
type: decision
status: done
tags: [decision, refactor, bench]
---
# 2026-11-03 tách phần chấm điểm của speaker benchmark

Skill `graph-refactor`, nhánh `refactor/graph-pass`.

## Quyết định

`run_benchmark()` (`subagent/bench/benchmark.py`, 6.11b) tách phần chấm điểm mỗi tập ra hàm thuần `_score_episode()`: speaker hôm nay và speaker lúc audit so với gold, các ô theo tầng (flagged / unflagged: số dòng, số dòng đã kiểm, số sai) và các dòng bất đồng. Trả về `_Tally`; vòng lặp chỉ cộng dồn theo đúng thứ tự cũ. Thêm test `test_score_episode_strata_and_disagreements`.

## Lý do

Đồ thị: `run_benchmark` là một trong ba hàm dài nhất (gọi 24 hàm khác nhau, 78 dòng). Trong đó lẫn hai việc: chạy các stage trong sandbox, và chấm điểm. Phần chấm điểm thuần nhưng trước đây chỉ kiểm được qua cả lần chạy benchmark giả.

`dream()` (cũng dài) để lại: phần lớn của nó dựng prompt, mà prompt phải giữ đúng từng byte (luật cache 5.1), nên tách ra thì rủi ro cao hơn lợi.

## Kết quả

ruff sạch; pytest 271 → 272, tất cả qua; `test_gold_answers_and_benchmark` qua mà không sửa. `run_benchmark` 78 → 57 dòng; vẫn gọi 23 hàm, vì việc của nó là điều phối.
