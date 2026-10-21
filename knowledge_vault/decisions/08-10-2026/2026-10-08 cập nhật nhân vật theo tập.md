---
date: 2026-10-08
type: decision
status: paused
tags: [decision, memory, characters, way-2]
---
# 2026-10-08 cập nhật nhân vật theo tập

Bước 3 của Hướng 2 (nhận diện nhân vật và tự cập nhật dữ liệu nhân vật). Spec: `.claude/rules/memory.md` mục 5.15c.

## Quyết định

- Sau mỗi tập (khi Finish review, và khi bench chạy chế độ chain học lại), một lệnh gọi `utility` **riêng** (không gộp vào lệnh gọi briefing) đọc kịch bản đã duyệt và đề xuất bốn loại cập nhật cho các nhân vật có mặt trong tập: tên tiếng Việt, mô tả, tên gọi khác / danh xưng, và cặp xưng hô thực sự được dùng.
- **Tên gọi khác** lưu ở cột mới `aliases` của nhân vật (và của ứng viên đang thử việc), hiện trong khối nhân vật của prompt ("called: 会长 (Hội trưởng)"). Thuật ngữ không gắn với một người vẫn ở glossary.
- **Nhân vật chưa khóa** (NPC, nhân vật do translator tạo): áp dụng ngay trong commit của tập, bỏ qua luật "nhiều bằng chứng hơn thì thắng".
- **Ứng viên đang thử việc:** tên (nếu chưa có), mô tả và tên gọi khác lưu vào dòng ứng viên, nên thẻ nhân vật và "Browse characters…" hiện chúng khi duyệt tập sau; khi được nhận, tất cả chuyển sang nhân vật.
- **Nhân vật đã khóa** (dàn chính, mục bạn đã sửa): chờ duyệt ở tab mới Memory → **Character updates**, mỗi mục một trường (tên, mô tả, tên gọi khác, cặp xưng hô), kèm các dòng bằng chứng. Chấp nhận = chỉnh sửa của bạn (khóa); từ chối thì không đề xuất lại.
- **Chế độ auto:** chỉ học từ dòng tin cậy (giọng, translator và lần đánh giá đầu đồng ý — cùng luật với thử việc); phần còn lại chờ duyệt (nhân vật đã biết) hoặc bị bỏ (ứng viên, giọng mới).
- **Mô tả** được viết lại toàn bộ mỗi lần, giữ ý cũ trừ khi kịch bản nói khác, cắt ở `memory.description_max_chars` (200 ký tự).
- **Bật ngay** (`memory.character_updates: true` trong `config.yaml`) theo quyết định của chủ dự án, trước khi đo bằng bench chain. Mặc định trong code vẫn là tắt.

## Lý do

- Trong cả 16 tập replay, translator chỉ đề xuất 1 nhân vật (Can Phong, ep014) và 1 cặp xưng hô; mọi NPC còn lại vẫn không tên, mô tả chỉ là "Voice found automatically in epXXX". Translator không có gì để nhận ra NPC khi họ quay lại.
- Lệnh gọi riêng thì bật / tắt và đo được độc lập, không làm thay đổi briefing. Chi phí khoảng $0.002–0.005 mỗi tập với DeepSeek.
- Kiểm tra trong code ưu tiên độ chính xác (theo [điểm yếu đã biết](../điểm%20yếu%20đã%20biết.md) và quy tắc "precision over coverage"): tên và tên gọi khác phải xuất hiện trong dòng mà người khác nói với nhân vật đó (hoặc tên trong câu tự giới thiệu); cặp xưng hô phải có từ xưng / gọi trong tiếng Việt của dòng có đúng người nói và người nghe; bằng chứng phải có nhân vật đó làm người nói hoặc người nghe.
- Mục đã khóa chờ duyệt thay vì bị từ chối: thông tin mới về dàn chính vẫn có ích, nhưng chỉ bạn mới được sửa chúng.
- Một trường chỉ có một mục chờ (mục mới thay mục cũ), để danh sách không phình ra qua từng tập.

## Đo lường

- Chạy thử một tập (ep014, chỉ đọc, không ghi bộ nhớ), 2026-10-08:
  - Lần 1: 6 nhân vật, 0 cặp xưng hô. Lỗi: npc_014_01 nhận tên gọi 会长 vì nó *nói* 会长 với npc_009_01; mô tả kể lại cốt truyện tập và vượt 200 ký tự.
  - Sửa: tên và tên gọi khác chỉ tính từ dòng mà nhân vật là người nghe (hoặc tự giới thiệu: 我是, 在下, 老夫 …); prompt yêu cầu mô tả chỉ ghi điều lâu dài, rà mọi cặp người nói → người nghe, loại câu chửi (老贼).
  - Lần 2: 5 nhân vật (tên Điếu Bất Quần cho npc_004_02, đúng: Cơ Tử gọi thẳng tên ở ep014:0005), 6 cặp xưng hô, đều khớp với các dòng.
- Bench chain có tính năng (2026-10-09, `_suite/20261008T160430-character-updates`, $0.63) so với `reference-chain` ($0.31):
  - Người nói: 82.3% so với 82.1%; nhân vật mới (NPC, gộp nhóm) 57.9% = 57.9%. **Không thấy cải thiện.**
  - Người nghe: 88.3% so với 93.0%; xưng hô giống bản duyệt 92.9% so với 93.7%; tiếng Việt giống bản duyệt 68.0% so với 81.8%.
  - **Chưa kết luận được:** `reference-chain` dùng lại cache (chính bản máy mà chủ dự án đã sửa thành gold), còn lần này dịch lại từ ep002, nên mọi lần chạy mới đều có vẻ kém hơn. Phần lớn chênh lệch người nghe là trống ↔ có người (ví dụ None → co_tu 25 dòng), kiểu khác biệt giữa hai lần dịch.
  - Bộ nhớ sandbox cuối chạy: 105 ghi từ updater, cặp xưng hô 29 → 76, 15 mục chờ duyệt; mô tả NPC phần lớn đúng và có ích (ví dụ npc_011_02 và npc_008_02 đều được ghi là con trai npc_009_01, khớp alias trong gold), vài lỗi (npc_014_03 "trưởng hội câu cá", tên gọi chung 叔叔).
  - Bước tiếp (tạm dừng theo chủ dự án): chạy đối chứng chain, tính năng tắt, `--no-cache`, để biết mức nhiễu.
- Cách đo ban đầu: chạy `bench run --mode chain` với tính năng bật, so với lần chạy tham chiếu `reference-chain` (benchmark 2: người nói / người nghe, nhất là NPC; benchmark 4: xưng hô). Xem [đo lường - benchmark suite](../đo%20lường%20-%20benchmark%20suite.md).

## Quyết định tiếp theo (2026-10-10)

- **Tắt** (`memory.character_updates: false`), giữ nguyên code. Đối chứng chain (tắt tính năng, `--no-cache`) dừng sau ep002 và không chạy tiếp.
- Lý do: người nói không đổi (NPC 57.9% = 57.9%), xưng hô không tốt hơn (92.9% so với 93.7%). Lỗi người nói nằm ở khớp giọng (confusable 71%, new voice 77%, unknown 26%), không phải ở việc thiếu thông tin nhân vật; translator gần như luôn theo giọng.
- Giá trị còn lại là cho **người duyệt**: thẻ NPC có mô tả thật, ma trận xưng hô đầy hơn. Benchmark không đo được điều này. Có thể bật lại cho chế độ **human** khi tách hai chế độ: [2026-10-07 chia hai chế độ auto và human](../07-10-2026/2026-10-07%20chia%20hai%20ch%E1%BA%BF%20%C4%91%E1%BB%99%20auto%20v%C3%A0%20human.md). Cần cân nhắc lúc đó: chỉ lưu cho thẻ và màn Memory, không đưa vào prompt translator, để tránh rủi ro người nghe giảm (88.3% so với 93.0%, chưa rõ là nhiễu hay thật).

## Liên quan

- [2026-10-07 chia hai chế độ auto và human](../07-10-2026/2026-10-07%20chia%20hai%20ch%E1%BA%BF%20%C4%91%E1%BB%99%20auto%20v%C3%A0%20human.md)

- [điểm yếu đã biết](../điểm%20yếu%20đã%20biết.md)
- [thiết kế - lý do các lựa chọn](../thiết%20kế%20-%20lý%20do%20các%20lựa%20chọn.md)
