---
date: 2026-10-08
type: measurement
tags: [measurement, ocr, answer-key]
---
# Đo lường - OCR

Chuyển từ CLAUDE.md (mục 5.4a, 6.11c, 6.11e) ngày 2026-10-08. Hành vi hiện tại và cấu hình nằm ở `.claude/rules/ocr.md`, `.claude/rules/benchmarks.md` và `config.yaml`; ghi chú này giữ lý do và số đo.

## Vì sao có phân đoạn phụ đề chung (5.4a)

Công cụ hướng tới nhiều bộ hoạt hình (mục tiêu của chủ dự án), nên không được tinh chỉnh theo font của một bộ. Phụ đề là chữ có nét gần như đều độ dày, đứng yên trong khi cảnh phía sau thay đổi, và giữ cùng kiểu suốt một bộ phim.

## Kiểu phụ đề của bộ này

- Hiệu chỉnh trên ep005: chữ sáng, fill 168–255, outline 72 (xám điển hình 14), nét 0.125 và chiều cao chữ 0.77 so với dải phụ đề.
- Mức outline đặt ở một phần tư quãng từ xám điển hình của outline về phía fill, vì nén video làm outline sáng lên không đều: ở đúng mức xám điển hình, chữ chỉ đo được 45–57% được viền và chữ ở hai đầu dòng bị bỏ. Với `seg_outline_share` 0.4, chữ đo được 56–77% và cảnh nền nhiều nhất 16%.

## Vì sao có OCR benchmark (6.11c)

So sánh các thiết lập OCR (5.4) trên các tập đã được người duyệt, không cần LLM và không cần kiểm tay thêm.

## Answer key

- Xây ngày 2026-10-02: kiểm mọi dòng mà tiếng Trung đã duyệt khác với lần đọc OCR thứ hai (287 dòng) đối chiếu với ảnh phụ đề, cộng các dòng cả hai đọc sai giống nhau. Tiếng Trung đã duyệt khác màn hình ở khoảng 7% số dòng (chữ đạo cụ như 姬 / 楚 / 史, 7 thay cho 了, thiếu chữ ở đầu/cuối dòng, dòng ngắn bị đọc rác; 14 chỗ reviewer cố ý sửa lỗi chính tả và tên trên màn hình được chấm theo màn hình). 110 sửa, 20 loại.
- Remap sang bản replay (2026-10-06): 108 sửa, 8 loại, bỏ 5 loại chỉ nói về một mảnh của dòng đã gộp, mất 1 dòng (ep008:0072).
- Mở rộng cho bản replay (2026-10-06, quyết định của chủ dự án: kiểm bằng khung hình, không sửa file đã duyệt): tiếng Trung đã duyệt vẫn còn lỗi reviewer không sửa (giữ 7 thay cho 了, thiếu 了 / 一 / 啊, 老参 thay cho 老爹, 没力气 thay cho 没办法, 住手 thay cho 住口) và những chỗ cố ý viết lại lời của phim (北匕 thay cho 北鼻, 屎 thay cho 史, 看来 thay cho 表, 不是 thay cho 不系, 楚留勤 thay cho 楚留竿). Kiểm 255 dòng mà tiếng Trung đã duyệt khác với OCR thô mới, OCR cũ (archive), một sửa của script review, hoặc chứa chữ Latin / số 7 không thuộc con số, đối chiếu với khung hình video (đầu, giữa và cuối dòng khi chưa rõ): thêm 47 sửa và 1 loại (ghi chú `extended` trong key), tổng cộng 155 sửa, 9 loại. Chữ 于 của font phụ đề trông giống 干; tính là 于.
- Phát hiện khi kiểm (tầng events): ep013:0106 là ba phụ đề (楚哥, 你说怎么办, 姬哥) bị đọc thành một event: 楚哥 / 姬哥 nằm trong `ocr.merge_max_edit_distance` nên gộp qua dòng ở giữa, và dòng ở giữa bị bỏ. Đã loại khỏi key; một dòng ngắn khác nằm giữa hai dòng gần giống nhau sẽ bị mất.

## Kết quả đo (so với answer key)

- OCR khi đó: 86.6% dòng / CER 2.71% (12 tập). Giới hạn detection 960 px: 86.3% / 2.58% nhưng mất 26 dòng.
- Trên ep001, ep006, ep012: OCR khi đó 81.4% / 3.94%; cắt dòng từ pixel gốc 87.8% / 2.05%; cắt dòng từ mask 74.1% / 4.59%; isolated 75.0% / 4.68% (chữ nhị phân hoá mất nét: 于→无, 青→四).
- Cả 12 tập (2026-10-03): cắt dòng 88.9% / 1.98% (mất 7 dòng); mask tinh chỉnh theo phim (nét ≤ 0.14, fill trung bình ≥ 238) 89.9% / 1.80%, thêm `band_frames: 5` 90.1% / 1.75%; phân đoạn chung (5.4a) với mức outline 14 và share 0.5: 82.9% / 2.75% (101 dòng bị cắt đầu hoặc cuối: chữ cuối trượt bài kiểm outline), với mức outline 72 và share 0.4: 89.3% / 1.82%, thêm `band_frames: 5` 90.0% / 1.73% (mất 5 dòng). Mức cải thiện của bản tinh chỉnh theo phim giữ nguyên trên các tập chưa từng xem khi tinh chỉnh (+3.2 đến +3.5 so với OCR khi đó). Lỗi lớn nhất còn lại ở mọi phương pháp: 了 đọc thành 7 (khoảng một nửa số dòng sai).

## Symmetric crop (2026-10-03)

12 tập, sau khi vẽ lại dải phụ đề cân giữa và học lại style trên ep001; baseline là phân đoạn không có symmetric crop.

| Tolerance | Dòng đúng | CER | Event rác |
|---|---|---|---|
| baseline | 91.9% | 1.42% | 312 |
| 0 | 93.0% | 1.24% | 150 |
| 0.25 | 93.0% | 1.21% | 144 |
| 0.5 | 92.8% | 1.27% | 148 |
| 0.75 | 92.9% | 1.25% | 151 |
| 1 | 92.7% | 1.28% | 144 |

- Mọi lần chạy đều mất 7 dòng.
- Dòng đúng ở baseline nhưng sai khi bật: 16, 7, 7, 2, 4 (chữ ở mép bị cắt: 比→此, mất 才 và 一; cộng các lần lật 了 / 7 do bề rộng crop khác nhau, theo cả hai chiều).
- Dòng được sửa: mảnh lạc ở hai đầu dòng (一他们, 老爹一, 楚，, 史) và các dòng ngắn trước đó bị đọc thành rác.
- Chọn 0.75: gần như chính xác nhất, ít dòng hỏng nhất. Mức 91.9% của baseline so với 90.0% trước đó đến từ dải phụ đề mới và style mới cùng lúc.

## End to end (2026-10-03)

11 tập, sandbox với memory khi đó. Trước = OCR cũ của các tập + script review cũ; sau = phân đoạn chung có fusion + script review Round 3; cả hai đi qua OCR correction, voice, cast, dịch và chấm, script review.

- Tiếng Trung đúng sau OCR correction: 90.8% → 93.7% (95.5% nếu chấp nhận các sửa của script review).
- Dòng dịch từ tiếng Trung sai: 140 → 91.
- Trên 90 dòng reviewer viết lại tiếng Việt, độ giống với bản của reviewer: 0.80 → 0.84.
- Speaker trên nhân vật có tên: 92.3% cả hai. Evaluator đạt ngay lần đầu: 92.0% → 92.2%. Chi phí như nhau.
- OCR mới còn đọc được khoảng 35 dòng mà OCR cũ bỏ sót hoặc đọc thành rác bị reviewer xoá (是我赢了 đọc thành 丰音, 号称肿脸仙人咩 thành 女): các dòng này không có trong answer key, nên điểm theo key đánh giá thấp OCR mới và tính chúng là rác.

Related: [đo lường - benchmark suite](đo%20lường%20-%20benchmark%20suite.md), [đo lường - script review](đo%20lường%20-%20script%20review.md), [điểm yếu đã biết](điểm%20yếu%20đã%20biết.md)
