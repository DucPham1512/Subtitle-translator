---
date: 2026-10-08
type: measurement
tags: [measurement, benchmark, baseline, audit]
---
# Đo lường - benchmark suite

Chuyển từ CLAUDE.md (mục 6.11, 6.11b, 6.11d, 6.11e) ngày 2026-10-08. Cách dùng hiện tại nằm ở `.claude/rules/benchmarks.md`; kết quả từng lần chạy ở `<work>/_suite/history.jsonl` và `<work>/_baseline/replay-2026-10/references/`.

## Vì sao có từng công cụ

- **Audit (6.11):** đo độ chính xác qua nhiều tập (của bất kỳ bộ phim nào) mà không phải kiểm từng dòng; biết được chỉ kiểm các dòng bị gắn cờ có đủ hay không.
- **Speaker benchmark (6.11b):** chấm mọi thay đổi sau này (code, dọn memory, prompt) dựa trên những gì đã audit, không cần kiểm tay lại.
- **Baseline (6.11d):** một bộ benchmark cần gold mà các lần chạy lại không ghi đè được (quyết định của chủ dự án ngày 2026-10-03: replay ep001–ep016 từ memory bootstrap và duyệt lại theo thứ tự tập, làm baseline cho các thí nghiệm sau).
- **Benchmark suite (6.11e):** chấm mọi thí nghiệm sau này (cập nhật memory, evaluator, prompt, OCR, nhận diện) theo một gold không đổi: baseline `replay-2026-10` (quyết định của chủ dự án ngày 2026-10-06: năm benchmark, cả hai chế độ chạy lại, id tự động ghép theo nhóm).

## Chi phí speaker benchmark (6.11b)

Khoảng 3 phút và $0.03 tiền dịch cho mỗi tập 5 phút (đo trên ep010). Memory đã học từ các tập đã audit, nên chỉ so các lần chạy với nhau.

## Kiểm tra harness

- Snapshot trên ep002 từ `translate`: translations, evaluations, script review giống hệt, $0.
- Chain ep001 → ep002: các commit học trong sandbox khớp với replay (sprites from ep001: +384, -69); prefix và output của ep002 giống hệt.

## Kết quả của output đã ghi (2026-10-06, 16 tập, 2,136 dòng)

- OCR thô 93.5% dòng / CER 1.03%; sau correction 96.0% / 0.64%; nếu chấp nhận các sửa của script review 96.9%.
- Speaker 81.6% (đã biết 94.8%, mới 55.6%, không ai 42.5%); listener 95.8%; ứng viên đầu của voice 84.6% (fixed 97.2%, confusable 68.6%, new voice 79.1%).
- Nhận diện trên 656 dòng: tìm thấy 99.0% box / 88.2% là nhân vật; gọi đúng tên 38.5% (909 không nhận ra, 136 sai tên); tìm thấy sprite đang nói 60.8%, sprite đó đúng là speaker 21.9%.
- 96.0% dòng tiếng Việt reviewer giữ nguyên (dòng viết lại giống 0.768); thuật ngữ đại từ khớp 97.4%. Evaluator bắt được 16.5% dòng bị viết lại khi tính "failed" / 41.2% khi tính "doubt"; báo động nhầm 4.2% / 9.7%; tiêu chí speaker bắt được 9.2% speaker sai.
- Xoá trước chính xác 97.5%, phủ 93.7% số dòng reviewer xoá; 23 sửa OCR, 20 đúng, 2 có hại (bỏ chữ 表 vốn là một phần của phụ đề: 这么来劲哦表, 我快不行了表; phim dùng 表 như một từ, cũng có 表你真系个人才哦, 哦哟表).

## Lần chạy tham chiếu (2026-10-06, cả 16 tập, code không đổi)

Các thí nghiệm so với hai lần chạy này, không so với output đã ghi (gold được sửa từ chính output đó).

- `reference-snapshot` (từ `ocr_fix`): mọi file được chấm giống hệt output đã ghi trên cả 16 tập (events, voice, cast, translations, evaluations, script review, prompt prefix); mọi điểm bằng nhau; $0 (cache).
- `reference-chain`: giống hệt đến hết prefix của ep009; từ ep010 memory khác vì replay đã finish ep001–ep010 bằng code trước bản sửa probation (5.15b: NPC reviewer gán khi quay lại được thăng cấp dù hình bất đồng), nên code hiện tại thăng cấp `npc_008_02` ở ep009 (trong replay nó bị bỏ và quay lại thành `npc_011_02`), và briefing cùng các prompt sau đó đổi theo. Speaker 82.1% (đã biết 94.6%, mới 57.9%), listener 93.0%, ứng viên đầu của voice 85.2%, nhận diện đúng tên 40.1%, độ giống tiếng Việt 0.961, evaluator bắt 6.7% / báo động nhầm 3.5%; $0.31 (các lệnh cache không phục vụ được sau ep009). Trong lần chạy lại, dòng tiếng Việt khác gold không hẳn là sai (gold được sửa từ câu chữ đã ghi), nên số liệu dịch và evaluator chỉ so được giữa các lần chạy lại.

Related: [đo lường - OCR](đo%20lường%20-%20OCR.md), [đo lường - nhận diện nhân vật và giọng](đo%20lường%20-%20nhận%20diện%20nhân%20vật%20và%20giọng.md), [đo lường - script review](đo%20lường%20-%20script%20review.md)
