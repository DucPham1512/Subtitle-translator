---
date: 2026-10-10
type: decision
status: done
tags: [decision, translation, evaluator, glossary, measurement]
---
# 2026-10-10 vòng phản hồi translator - evaluator

Câu hỏi của chủ dự án: vì sao evaluator đề xuất sửa mà translator không làm gì. Spec: `.claude/rules/translation.md` mục 5.11–5.12, `.claude/rules/app.md` mục 6.4.

## Đo lường (baseline `replay-2026-10`, 16 tập, chỉ đọc, $0)

Có hai lỗi khác nhau, cùng một biểu hiện:

**Lỗi A: đề xuất không bao giờ đến được translator (128 dòng).**

- Prompt của evaluator yêu cầu đưa câu sửa khi có điểm **dưới 4**; code chỉ đánh trượt dòng, nên chỉ gửi lại, khi có điểm **dưới 3** (`evaluate.min_score: 3`).
- Dòng được 3 điểm vẫn qua: `judge()` bỏ câu sửa đi và lưu lời phàn nàn thành "(passed) …". Translator không bao giờ thấy.
- Ví dụ: ep001:0060 "'ngon' quá hiện đại cho bối cảnh cổ trang, dùng 'tốt'"; ep001:0080 "'Cha' tự nhiên hơn 'Cha già'".
- Phần lớn là nhiễu: reviewer chỉ viết lại 21 / 128 dòng đó. Gửi lại tất cả cho translator sẽ chủ yếu làm xáo những dòng đã ổn.

**Lỗi B: translator bị yêu cầu thoả một luật không thể thoả đúng (43 dòng trả lại y nguyên câu cũ).**

- Sau một lỗi luật cứng, translator thường trả lại đúng câu cũ; vòng lặp dừng (đúng thiết kế) và dòng mang cờ `retry_cap`.
- Nguyên nhân chính: mục glossary 鱼 → "cá" khớp **bên trong từ khác**: 钓鱼 ("câu cá" = câu), 钓鱼佬 (câu thủ), 降鱼钓法, 鱼钩 (lưỡi câu). Luật này bật trên 35 dòng; 12 dòng kết thúc ở trạng thái trượt.
- Khi translator nghe theo, câu tiếng Việt hỏng: "đi **Cá** phải đội mũ" (ep003:0009), "câu **Cá** với bọn họ", "gắn **Cá** câu" cho 鱼钩. Vài dòng hỏng kiểu này đã được duyệt và nằm trong gold.
- Nguyên nhân khác: 13 dòng trượt vì mục glossary sai (đã sửa trong [2026-10-10 sửa lỗi glossary học từ bản dịch máy](2026-10-10%20s%E1%BB%ADa%20l%E1%BB%97i%20glossary%20h%E1%BB%8Dc%20t%E1%BB%AB%20b%E1%BA%A3n%20d%E1%BB%8Bch%20m%C3%A1y.md)), 7 vì ma trận đại từ trái với ngữ cảnh của dòng, vài dòng vì evaluator chấm thấp speaker không xác định được (translator không thể sửa).

Tổng: 326 dòng được dịch lại, 108 dòng kết thúc ở trạng thái trượt (25 do glossary, 7 do đại từ, 10 do speaker ngoài danh sách ứng viên, 66 do điểm rubric).

## Quyết định (chủ dự án chọn)

1. **Lỗi B, luật glossary khớp theo từ:** một thuật ngữ chỉ tính khi đứng thành từ trọn vẹn sau khi tách từ bằng jieba (đã dùng cho pinyin). Thuật ngữ từ 2 chữ trở lên được giữ nguyên khối khi tách; chữ đơn không được ưu tiên, nên 钓鱼 vẫn là một từ. Áp dụng cho mọi mục glossary, kể cả thuật ngữ ngắn sau này. Không xoá mục 鱼 → cá.
2. **Lỗi A, đưa đề xuất cho reviewer:** dòng 3 điểm vẫn qua (không tốn thêm lệnh gọi), nhưng câu sửa của evaluator được giữ lại và hiện trong phần ghi chú của màn review ("Evaluator suggests: …") khi khác câu hiện tại. Reviewer tự quyết. Không đổi prompt: ngưỡng "dưới 4" của prompt giờ có ích (câu sửa được dùng), không còn bị bỏ đi.

Phương án không chọn: nâng `min_score` lên 4 (khoảng 128 lần dịch lại trên 16 tập, phần lớn ở dòng reviewer giữ nguyên); xoá riêng mục 鱼 (thuật ngữ một chữ khác sẽ gây lỗi y hệt).

## Kiểm tra

- Trên dòng thật: 鱼 vẫn được tính khi đứng riêng (那条鱼, 钓会儿鱼), không còn tính trong 钓鱼, 鱼钩; 降鱼十八钓, 姬佬, 竿门开, 钓位 vẫn được tìm thấy.
- Test mới: luật glossary khớp theo từ; dòng 3 điểm qua mà vẫn giữ câu sửa.
- Chưa đo bằng benchmark: cách đo là một lần chạy lại mới (snapshot từ `translate`, không dùng cache), so số dòng `retry_cap` vì glossary và số dòng bị ép chữ "Cá".

## Bổ sung: thuật ngữ tự đặt của phim (2026-10-10)

- **Benchmark** (ep001–ep003, snapshot từ `translate`, không cache, $0.08; `_suite/20261010T064153-feedback-fix-ep001-003`), so với output đã ghi: dòng bị luật glossary bắt 15 → 10 (trên 鱼: 8 → 3), dòng dịch lại 79 → 61, dòng trả lại y nguyên 13 → 9, dòng `retry_cap` 25 → 20 (do glossary 4 → 3), dòng bị ép chữ "Cá" 3 → 2, câu sửa của evaluator giữ lại cho reviewer 0 → 18 (5 trên dòng reviewer đã viết lại). Điểm dịch so với gold (giống bản duyệt 61.8%) không so được với tham chiếu: tham chiếu dùng cache, chính là bản reviewer đã sửa thành gold.
- **Lỗ hổng còn lại:** thuật ngữ tự đặt của phim (降鱼钓法, 降鱼十八钓, 何罗鱼) chưa có trong từ điển jieba trước khi vào glossary, nên jieba tách 降 / 鱼 và luật lại ép "Cá" ("Cá Giáng Câu Pháp" ở ep002).
- **Đề xuất của chủ dự án:** thêm một lượt LLM để xác định cách tách từ (tên chiêu, địa danh, tên nhân vật). Đo trước: chế độ HMM có sẵn của jieba gộp các chuỗi chữ lạ thành một từ mới (降鱼, 竿门开, 钓帝). Trên 16 tập (242 dòng có 鱼), luật 鱼 bắn sai (bản duyệt không có "cá"): HMM tắt 16, HMM bật 1 (và dòng đó là lỗi trong gold: 鱼 bị dịch "lưỡi"); bắn đúng 52 → 41 (11 dòng 鱼 thật không còn được luật kiểm, vô hại vì translator vẫn viết "cá"). Độ chính xác 76% → 98%.
- **Quyết định:** bật HMM trong bộ tách từ của luật glossary (không thêm lượt LLM: lượt đó tốn một lệnh gọi mỗi tập và có thể gán nhầm, để sửa khoảng một dòng mỗi tập mà HMM đã sửa miễn phí). Glossary nhiều nghĩa cũng huỷ, xem [2026-10-07 chia hai chế độ auto và human](2026-10-07%20chia%20hai%20ch%E1%BA%BF%20%C4%91%E1%BB%99%20auto%20v%C3%A0%20human.md).

Related: [điểm yếu đã biết](điểm%20yếu%20đã%20biết.md), [đo lường - benchmark suite](đo%20lường%20-%20benchmark%20suite.md)
