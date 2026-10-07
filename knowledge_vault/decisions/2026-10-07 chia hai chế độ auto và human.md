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
- [ ] Mở rộng schema glossary: một entry nhiều nghĩa, mỗi nghĩa kèm điều kiện ngắn.
- [ ] Đưa các nghĩa và điều kiện vào prefix cho translator.
- [ ] Đổi rule check glossary sang cảnh báo mềm.

## Cần đo

- Chạy benchmark suite với chế độ "chỉ dùng speaker khi chắc", so với cấu hình hiện tại.
- Chỉ số: độ giống bản dịch của reviewer.
- Kết quả: _chưa có_.
