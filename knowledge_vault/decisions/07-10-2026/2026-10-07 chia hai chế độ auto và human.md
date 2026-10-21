---
date: 2026-10-07
type: decision
status: proposed
tags: [decision, review-mode, speaker, glossary]
---
# 2026-10-07 chia hai chế độ auto và human

## Quyết định

Pipeline có hai chế độ chạy:

- **auto**: chạy nhanh, không cần review.
  - Chỉ gán speaker khi nhân vật thuộc seed bootstrap **và** voice ở trạng thái fixed. Mọi trường hợp khác để speaker rỗng.
  - Dòng có speaker rỗng dùng cặp đại từ mặc định **ta/ngươi**.
- **human**: có reviewer, giữ chất lượng cao.

Glossary nhiều nghĩa (áp dụng cho cả hai chế độ):

- Mỗi entry có thể có nhiều nghĩa, mỗi nghĩa kèm một điều kiện ngắn.
- Toàn bộ các nghĩa được đưa vào prefix để translator tự chọn.
- Rule check chỉ cảnh báo mềm, không chặn.

Giá trị chế độ nằm ở `review.mode` trong `config.yaml`.

## Lý do

- Auto ưu tiên tốc độ, human ưu tiên chất lượng; tách hai chế độ để không phải đánh đổi trong cùng một luồng.
- Gán speaker sai làm sai cả cặp đại từ. Khi không có reviewer, chỉ tin speaker trong trường hợp chắc chắn (seed bootstrap + voice fixed); còn lại thà để rỗng và dùng đại từ trung tính mặc định.
- Một từ trong glossary có thể có nhiều nghĩa tùy ngữ cảnh. Ép một nghĩa duy nhất hoặc chặn cứng bằng rule check sẽ sinh lỗi; để translator chọn theo điều kiện và chỉ cảnh báo mềm thì an toàn hơn.

## Cần làm

- [ ] Thêm chế độ `auto` bên cạnh `human` cho `review.mode`.
- [ ] Ở chế độ auto: chỉ gán speaker khi nhân vật thuộc seed bootstrap và voice fixed; còn lại để speaker rỗng.
- [ ] Dòng speaker rỗng dùng cặp đại từ mặc định ta/ngươi.
- [ ] ~~Mở rộng schema glossary: một entry nhiều nghĩa, mỗi nghĩa kèm điều kiện ngắn.~~ (huỷ 2026-10-10)
- [ ] ~~Đưa các nghĩa và điều kiện vào prefix cho translator.~~ (huỷ 2026-10-10)
- [ ] ~~Đổi rule check glossary sang cảnh báo mềm.~~ (huỷ 2026-10-10)
- [ ] Chế độ human: cân nhắc bật lại cập nhật nhân vật theo tập (`memory.character_updates`), có thể chỉ cho thẻ nhân vật và màn Memory, không vào prompt translator. Xem [2026-10-08 cập nhật nhân vật theo tập](../08-10-2026/2026-10-08%20c%E1%BA%ADp%20nh%E1%BA%ADt%20nh%C3%A2n%20v%E1%BA%ADt%20theo%20t%E1%BA%ADp.md).

## Cần đo

- Chạy benchmark suite với chế độ "chỉ dùng speaker khi chắc", so với cấu hình hiện tại.
- Chỉ số: độ giống bản dịch của reviewer.
- Kết quả: _chưa có_.

## Glossary nhiều nghĩa: huỷ (2026-10-10)

Chủ dự án quyết định huỷ phần glossary nhiều nghĩa, sau khi đo trên baseline `replay-2026-10`:

- 357 lần thuật ngữ glossary xuất hiện trong dòng đã duyệt; chỉ 13 dòng không dùng bản dịch của mục đó, và **không dòng nào là nghĩa thứ hai thật**: 5 là dạng sai cũ của glossary mà reviewer đã chấp nhận (趴地虎, 竿门开), 5 là cùng nghĩa nhưng viết khác hoặc rút gọn, 1 là biệt danh trong câu, 2 là lỗi dịch lọt vào gold.
- Trường hợp "khác nghĩa" thật duy nhất là chữ đơn nằm trong từ dài hơn (鱼 trong 钓鱼, 鱼钩), đã giải quyết bằng luật glossary khớp theo từ (jieba) mà không đổi định dạng glossary: [2026-10-10 vòng phản hồi translator - evaluator](../10-10-2026/2026-10-10%20v%C3%B2ng%20ph%E1%BA%A3n%20h%E1%BB%93i%20translator%20-%20evaluator.md).
- Luật glossary giữ là luật cứng: 25 dòng trượt vì glossary đều do 5 mục sai và lỗi 鱼, đã sửa. Làm mềm luật sẽ mất phần giữ thuật ngữ nhất quán qua các tập (NFR-Q1).

