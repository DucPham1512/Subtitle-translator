---
date: 2026-10-10
type: decision
status: done
tags: [decision, translation, glossary, memory, measurement]
---
# 2026-10-10 sửa lỗi glossary học từ bản dịch máy

Spec: `.claude/rules/memory.md` mục 5.15 (luật ghi) và 5.16 (khai thác chỉnh sửa của reviewer).

## Đo lường trước khi sửa (baseline `replay-2026-10`, chỉ đọc, $0)

Trên 16 tập (2,136 dòng), reviewer sửa tiếng Việt 87 dòng:

| Nguyên nhân | Số dòng | Thuộc về |
|---|---|---|
| Speaker / listener sai, đại từ sai theo | 22 | nhận diện người nói |
| Tiếng Trung sai do OCR | 12 | OCR |
| **Bản dịch** | **53** (khoảng 3.3 mỗi tập) | dịch / memory |

53 dòng dịch chia ra:

- **Khoảng 25: thuật ngữ của phim sai dạng Hán-Việt** (降鱼十八钓, 姬佬, 竿门开, 龙抬头, 钓位, …).
- Khoảng 10: chọn đại từ, cách xưng hô (chú → cha, người → ngươi).
- Khoảng 10: sai nghĩa, tiếng lóng (史 dùng thay 屎 → "cứt", 我去 → "Vãi", 鱼 bị dịch là "lưỡi").
- Khoảng 8: sửa văn phong nhỏ.
- Evaluator cho qua gần hết, đa số chấm 5 ở mọi tiêu chí.

So với khoảng 25 lần sửa speaker mỗi tập, phần dịch là phần nhỏ: một bộ dịch hoàn hảo chỉ bớt khoảng 3 lần sửa mỗi tập.

## Lỗi tìm thấy

Glossary học **thuật ngữ sai của máy**, ngay cả khi reviewer đã sửa đúng dòng đó:

- Ở ep008 translator đề xuất 降鱼十八钓 → "Hàng lưỡi Thập Bát Điếu", dẫn chứng ep008:0043 và ep008:0046. Reviewer sửa cả hai dòng thành "Hàng Ngư Thập Bát Điếu", nhưng đề xuất vẫn được áp dụng với từ của máy: luật chỉ kiểm dòng dẫn chứng đã được duyệt, không kiểm reviewer có sửa dòng đó không.
- Khai thác chỉnh sửa cũng không bắt được, vì hai lý do: nó chỉ sửa từ đã có trong glossary, và chạy trước khi từ mới của tập được thêm; và hàm `replaced_term` chỉ nhận ra khi cả cụm từ bị thay trong một lần, còn reviewer chỉ đổi một chữ trong cụm ("lưỡi" → "Ngư"). Vì thế các lần sửa lại ở ep012 và ep014 cũng không cập nhật glossary.
- Từ đó glossary ép từ sai vào mọi tập sau (translator phải dùng đúng glossary, rule check của evaluator cũng kiểm theo nó). Reviewer phải sửa lại 降鱼十八钓 ở ep012 và hai lần ở ep014, 姬佬 hai lần ở ep002, 竿门开 ở ep012.
- 5 mục sai lúc phát hiện: 降鱼十八钓 "Hàng lưỡi Thập Bát Điếu", 姬佬 "Cơ huynh", 竿门开 "Cần môn khai", 龙抬头 "Long Sở Đầu", 趴地虎 "Ba Địa Hổ".

## Quyết định

1. **Sửa luật học** (`memory/manager.py`):
   - `reviewed_glossary`: đề xuất glossary của translator mà reviewer đã sửa mất từ đó trên dòng dẫn chứng thì lấy dạng reviewer viết (đề xuất `human`, khóa, dẫn chứng là các chỉnh sửa đó). Không đọc ra được một dạng duy nhất (từ bị xoá, cả dòng bị viết lại, các chỉnh sửa khác nhau) thì bỏ đề xuất.
   - `replaced_term` theo dấu các chữ của cụm từ qua phép so khác biệt theo từ, nên sửa một phần cụm cũng tính. Chữ mới chỉ được coi là thay cho cụm khi có chung ít nhất một chữ với cụm, hoặc chữ đứng cạnh cụm trong dòng không đổi; một dòng bị viết lại hoàn toàn không cho ra dạng nào (an toàn hơn bản cũ, vốn nhận cả câu mới làm thuật ngữ).
   - Áp dụng cho cả thuật ngữ mới (lúc tập được duyệt) và thuật ngữ đã có (khai thác chỉnh sửa ở các tập sau).
2. **Sửa 5 mục sai trong memory thật** bằng chỉnh sửa của chủ dự án (khóa), một commit `manual edit: 5 changes`: 降鱼十八钓 → Hàng Ngư Thập Bát Điếu, 姬佬 → Cơ lão, 竿门开 → Can môn khai, 龙抬头 → Long Đài Đầu, 趴地虎 → Bò Đất Hổ.
3. **Chưa làm:** đại từ, tiếng lóng, văn phong (khoảng 1–2 dòng mỗi tập) và cải thiện evaluator. Trần nhỏ, evaluator gần như không bắt được các dòng này.

## Kiểm tra

- Cả 5 lần sửa thật được `replaced_term` đọc ra đúng dạng reviewer viết.
- Test mới: sửa một phần cụm từ; thuật ngữ mới của translator lấy dạng reviewer viết; dòng bị viết lại không tạo thuật ngữ.
- Chưa đo bằng benchmark: lỗi chỉ lộ ra ở các tập sau khi glossary đã học sai, nên cách đo đúng là một lần chạy chain mới. Lợi ích dự kiến: khoảng 6 dòng trên 16 tập của baseline, nhưng với phim hơn 230 tập, một thuật ngữ sai của chiêu thức chính sẽ tốn một lần sửa mỗi khi nó xuất hiện.

Related: [điểm yếu đã biết](../điểm%20yếu%20đã%20biết.md), [đo lường - benchmark suite](../đo%20lường%20-%20benchmark%20suite.md)
