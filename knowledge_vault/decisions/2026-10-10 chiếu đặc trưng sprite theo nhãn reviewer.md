---
date: 2026-10-10
type: decision
status: rejected
tags: [decision, cast, sprite, measurement]
---
# 2026-10-10 chiếu đặc trưng sprite theo nhãn reviewer

Nguồn ý tưởng: paper "Detecting and Grounding Important Characters in Visual Stories" (Liu & Keller, AAAI 2023, arXiv 2303.17647). Hành vi hiện tại của nhận diện hình: `.claude/rules/voice-cast.md` mục 5.8b; ngưỡng trong `config.yaml` (khối `cast`).

## Kết luận (2026-10-10)

**Không dùng.** Phép chiếu LDA làm thử đúng như kế hoạch, đo trên sprite bank thật, và thua cách nhận diện hiện tại (vector DINOv2 thô). Toàn bộ code đã gỡ theo quyết định của chủ dự án; chỉ giữ ghi chú này. Chi tiết ở mục "Lần thử" bên dưới.

## Quyết định ban đầu

- **Làm thử (test implementation):** chiếu vector DINOv2 của mỗi crop (768 số) sang một không gian nhỏ học từ các box reviewer đã gán nhãn (LDA, chỉ NumPy, không thêm dependency), rồi nhận diện bằng cosine trong không gian đó thay vì trên vector thô. Chưa đưa vào pipeline; chỉ đưa vào sau khi benchmark nhận diện (6.11e, mục 3) xác nhận.
- **Không làm** xếp hạng "nhân vật quan trọng" theo paper.
- **Không dùng** cách ghép chuỗi theo phân bố xuất hiện + Hungarian của paper (Algorithm 1).

## Lý do

- Thiết kế nhân vật của phim gần như không đổi qua các tập, nên những gì tách được các nhân vật ở tập trước vẫn đúng ở tập sau. DINOv2 được huấn luyện trên ảnh tổng quát: vector của nó chủ yếu mang tư thế, nền, kích thước crop và nét vẽ chung của phim, nên phần thiết kế (tóc, trang phục, màu) bị lấn át.
- LDA không chọn tay đặc trưng: nó học từ nhãn những hướng giữ các crop của cùng một nhân vật gần nhau và đẩy các nhân vật khác ra xa. Tư thế, ánh sáng, nền gần như không được trọng số.
- Xếp hạng độ quan trọng không giúp: probation (5.15b) và lifecycle (5.15a) đã chỉ giữ nhân vật quay lại, một tín hiệu tốt hơn tần suất trong một tập. Mọi dòng vẫn cần người nói để chọn xưng hô.
- Ghép theo phân bố xuất hiện không tách được hai nhân vật cùng đứng trong một cảnh, và rất nhạy lỗi đầu vào (paper: recall 77.5% với gold, 21.7–27.3% với output máy). Phiếu bầu theo sprite đang nói của sprite learning đã là dạng tốt hơn của ý này.

## Đo lường (2026-10-10, baseline `replay-2026-10`, chỉ đọc, $0)

**Nhân vật một lần và nhân vật quay lại** (gold, 2,133 dòng hội thoại):

- 25 nhân vật chỉ xuất hiện một tập: 256 dòng (12% hội thoại, 30% dòng của nhân vật mới). 14 nhân vật quay lại: 605 dòng.
- Số dòng ở tập đầu tiên không đoán được ai sẽ quay lại: npc_011_04 có 30 dòng và không quay lại; npc_004_02 có 14 dòng rồi xuất hiện 7 tập, 161 dòng.
- Độ chính xác speaker: dàn chính 95.8%, NPC quay lại (tập đầu) 72.9%, (tập sau) 81.3%, NPC một lần 65.2%.
- Speaker sai trên dòng NPC gần như không làm reviewer viết lại tiếng Việt (0–5% số dòng sai, so với 11.5% ở dàn chính): với NPC một lần, sai danh tính chủ yếu tốn công sửa, không làm giảm chất lượng dịch. Lỗi đáng sửa là nhầm giữa dàn chính và NPC (32 dòng NPC một lần bị gán cho dàn chính, 23 dòng dàn chính bị gán cho NPC).
- Ghép id tự động theo tập lỏng hơn `suite.group_map`, nên tổng lỗi (khoảng 291) thấp hơn số 406 trong [đo lường - nhận diện nhân vật và giọng](đo%20lường%20-%20nhận%20diện%20nhân%20vật%20và%20giọng.md); tỷ lệ giữa các nhóm mới là điều đáng tin.

**Chất lượng đặc trưng DINOv2** (5 tập kiểm On screen: ep002, ep005, ep009, ep012, ep015; khoảng 1,000 crop, 11 nhân vật):

- Cosine cùng nhân vật, khác tập: trung vị 0.565 (p10 0.377). Khác nhân vật: trung vị 0.525 (p90 0.65). Hai phân bố chồng nhau nhiều, nên ngưỡng `match_similarity` phải cao và phần lớn crop thành "không nhận ra".
- Khớp mỗi crop với 4 tập còn lại (leave-one-episode-out):

| | DINOv2 thô | Sau chiếu LDA |
|---|---|---|
| Dàn chính (865 crop) | 61.7% | 74.1% |
| NPC (92 crop) | 73.9% | 88.0% |

- Phép thử dễ hơn thực tế: chỉ chọn giữa 11 nhân vật đã gán nhãn, và box chưa gán nhãn mà máy đã gọi tên được tính là gold (thiên về crop dễ). Tin mức tăng hơn con số tuyệt đối.

## Lần thử (2026-10-10)

### Cách làm

Bản làm thử nằm sau cờ `cast.projection: off | lda` (mặc định tắt, không bật trong `config.yaml`):

- **Phép chiếu** (`subagent/sprite_projection.py`, chỉ NumPy, kết quả xác định): LDA có điều chuẩn. Ma trận phân tán trong nhóm Sw cộng `reg` × trung bình đường chéo × I; lấy các vector riêng của Sw⁻¹Sb (giải dạng đối xứng qua Cholesky), giữ số nhân vật − 1 chiều, sắp theo trị riêng, cố định dấu. Áp dụng: trừ trung bình, nhân ma trận, chuẩn hoá L2.
- **Học ở đâu:** ngay đầu cast stage, từ sprite bank đọc qua `memory/store.py` (bỏ nhân vật archived và generic như khi khớp). Không lưu phép chiếu vào `data/memory/`, không ghi memory, nên chế độ snapshot của bench (memory_at_run) không bị rò dữ liệu tương lai.
- **Chỉ học từ exemplar tin cậy.** `sprite_bank` không ghi nguồn gốc exemplar, nên đã thêm cột `source` (quyết định của chủ dự án): `reviewer_label` (box reviewer gán nhãn, đánh dấu đang nói, hoặc xác nhận bằng On screen checked), `reviewer_box` (box reviewer vẽ), `talker` (sprite đang nói được nhận ra là speaker đã duyệt), `talker_vote` (sprite lạ được đặt tên bằng phiếu), `promoted` (hình của ứng viên thử việc), `recognised` (máy tự khớp ≥ `add_similarity`); tiền tố `auto:` ở tập chế độ auto. Tin cậy = reviewer_* hoặc talker / talker_vote / promoted ở tập human; không bao giờ `recognised` hay `auto:*`. Dữ liệu cũ được điền ngược bằng cách khớp vector của exemplar với các box đã phát hiện trong tập của nó (box không khớp được là box reviewer vẽ hoặc dời).
- **Khớp:** khi bật, chiếu cả crop lẫn mọi exemplar của bank, rồi dùng luật đặt tên cũ với hai khoá riêng `projected_match_similarity` / `projected_match_margin` (phân bố cosine trong không gian mới khác hẳn). Gom sprite lạ (`unknown_similarity`), sprite learning và `cast_embeddings.npy` vẫn ở không gian thô.
- **Đo:** lệnh chỉ đọc `sprites evaluate`. Trên các dòng On screen checked của baseline `replay-2026-10` (ep002, ep005, ep009, ep012, ep015; 2,928 box, 4 box reviewer dời bị bỏ qua), mỗi box được gọi tên bằng sprite bank **đúng như lúc tập đó chạy** (đọc `memory.db` ở commit memory_at_run từ lịch sử git vào file tạm), ở cả hai không gian. Chia nhóm: dàn chính, NPC đã có nhãn trước tập đó, NPC chưa từng có nhãn, box reviewer để trống hoặc đánh dấu không phải nhân vật. Kèm lưới quét ngưỡng tương đồng × margin cho cả hai không gian.
- **Điều kiện thắng** (đặt trước khi đo): phép chiếu đúng nhiều tên hơn, với số tên sai (trên nhân vật, và trên box không phải ai) không cao hơn cách thô ở ngưỡng hiện tại. Thắng thì mới chạy `bench run` (snapshot, từ cast stage) và so benchmark 2, 3 với `reference-snapshot`.
- Fit trên bank thật: 315–647 exemplar mỗi tập, 315–550 tin cậy; 6–14 nhân vật, 5–13 chiều.

### Kết quả

| (ngưỡng tương đồng, margin)             | Dàn chính đúng / không nhận ra / sai (1,076 box) | NPC đã có nhãn (110) | NPC chưa từng có nhãn (511) | Box không phải ai bị gọi tên (1,231) |
| --------------------------------------- | ------------------------------------------------ | -------------------- | --------------------------- | ------------------------------------ |
| Thô (0.70, 0.03), hiện tại              | 590 / 453 / 33                                   | 63 / 44 / 3          | 0 / 412 / 99                | 218                                  |
| Chiếu (0.60, 0.05), mặc định            | 848 / 96 / 132                                   | 78 / 24 / 8          | 0 / 87 / 424                | 936                                  |
| Chiếu, tốt nhất trong lưới (0.95, 0.02) | 499 / 570 / 7                                    | 46 / 64 / 0          | 0 / 404 / 107               | 195                                  |

Theo điều kiện thắng (tổng tên đúng, khi số tên sai không quá 135 trên nhân vật và 218 trên box không phải ai):

| | Tên đúng | Tên sai | Box không phải ai bị gọi tên |
|---|---|---|---|
| Thô (0.70, 0.03) | **653** | 135 | 218 |
| Chiếu, reg 0.1 (0.93, 0.10) | 622 | 133 | 211 |
| Chiếu, reg 1.0 (0.95, 0.05) | 616 | 125 | 199 |
| Chiếu, reg 10 (0.96, 0.02) | 535 | 126 | 182 |

Chỉ chọn trong số nhân vật đã có nhãn (không ngưỡng, không có lựa chọn "không biết", giống phép thử trước khi làm): thô 873 / 1,186 (73.6%), chiếu 970 (81.8%, reg 0.1), 990 (83.5%, reg 1.0), 966 (81.5%, reg 10).

### Chỉ số cho thấy thất bại

- **Số tên đúng khi giữ số tên sai không tăng:** thô 653, phép chiếu tốt nhất 622. Đây là điều kiện thắng; phép chiếu không đạt ở bất kỳ ngưỡng hay mức điều chuẩn nào đã thử.
- **NPC chưa từng có nhãn bị gọi sai tên:** 424 / 511 ở ngưỡng mặc định (thô: 99). Muốn kéo xuống ngang thô thì phải đặt ngưỡng 0.95, và khi đó dàn chính chỉ còn 499 tên đúng (thô: 590).
- **Box không phải nhân vật bị gọi tên:** 936 / 1,231 ở ngưỡng mặc định (thô: 218).
- Không chạy `bench run`, vì phép chiếu không qua được bước này.

### Vì sao thất bại

- **Bài toán thật là tập mở, phép thử trước là tập đóng.** Phép thử leave-one-episode-out ban đầu (61.7% → 74.1%) chỉ hỏi "là ai trong 11 nhân vật đã gán nhãn". Pipeline thật phải trả lời cả "có phải ai đã biết không": 511 / 1,697 box nhân vật là NPC chưa từng có nhãn, và 1,231 box reviewer không gán cho ai. Ở tập đóng phép chiếu vẫn thắng (73.6% → 83.5%); ở tập mở thì thua.
- **LDA không có chỗ cho "không phải ai trong số này".** Học từ k nhân vật, nó chỉ giữ k − 1 chiều (5–13 ở đây), là những chiều tách các nhân vật đã biết. Mọi thứ khác (NPC mới, box không phải nhân vật) bị nén vào cùng không gian nhỏ đó và rơi gần một nhân vật đã biết, với cosine cao. Không gian thô 768 chiều còn giữ được khoảng cách đến "không giống ai", nên ngưỡng ở không gian thô từ chối được những box đó.
- Tăng điều chuẩn (reg 10) làm phép chiếu gần không gian thô hơn nhưng mất luôn phần lợi ở tập đóng; không có mức nào vừa giữ lợi ích vừa giữ khả năng từ chối.

### Đã gỡ

Theo quyết định của chủ dự án (2026-10-10), toàn bộ thay đổi code đã bị gỡ, không commit: `sprite_projection.py`, `sprite_eval.py` (`sprites evaluate`), cột `sprite_bank.source` và lệnh `sprites tag-sources`, việc ghi nguồn trong sprite learning và probation, `bench run --set`, các khoá `cast.projection*`, test và spec. `data/memory/` không bị ghi (cột mới chưa từng được thêm vào memory thật).

### Bài học và hướng có thể thử sau

- Đo trên đúng câu hỏi pipeline phải trả lời, có cả lựa chọn "không nhận ra" và nhân vật chưa có nhãn, trước khi làm. Phép thử tập đóng đã cho mức tăng sai lệch.
- Nếu làm lại: ghép hai không gian. Vector thô quyết định "có phải nhân vật đã biết không" (giữ khả năng từ chối), phép chiếu chỉ chọn "là ai" trong số đã biết (lấy phần lợi ở tập đóng). Chưa làm, chưa đo; đo được miễn phí bằng cùng cách đánh giá ở trên.
- Nếu cần lại `bench run --set` (đặt config chỉ cho một lần chạy) hay cột nguồn gốc của exemplar, cách làm đã mô tả ở trên.

## Kế hoạch thử ban đầu (đã thay bằng lần thử ở trên)

1. Học phép chiếu khi sprite learning chạy sau mỗi lần Finish review, chỉ từ nhãn tin cậy (nhãn box của reviewer, dòng human mode); dòng auto mode không được dạy phép chiếu, để lỗi không tự củng cố.
2. Cast stage chiếu crop và sprite bank trước khi so; ngưỡng (`match_similarity`, `match_margin`, `unknown_similarity`, `add_similarity`) phải đo lại trong không gian mới.
3. Chấm bằng benchmark 3 (nhận diện) và 2 (speaker) so với `reference-snapshot` / `reference-chain`. Theo dõi riêng NPC chưa từng gán nhãn.
4. Nếu chưa đủ: thử đặc trưng màu (histogram trang phục) hoặc bỏ nền trước DINOv2; cần frame đã phân tích, baseline không lưu.

Related: [đo lường - nhận diện nhân vật và giọng](đo%20lường%20-%20nhận%20diện%20nhân%20vật%20và%20giọng.md), [điểm yếu đã biết](điểm%20yếu%20đã%20biết.md), [đo lường - benchmark suite](đo%20lường%20-%20benchmark%20suite.md)
