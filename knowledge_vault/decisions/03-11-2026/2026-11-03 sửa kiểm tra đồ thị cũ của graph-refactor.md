---
date: 2026-11-03
type: decision
status: done
tags: [decision, claude-code, skill, graphify]
---
# 2026-11-03 sửa kiểm tra đồ thị cũ của graph-refactor

## Quyết định

Script `.claude/skills/graph-refactor/scripts/refactor_targets.py` chỉ báo đồ thị "cũ" khi một file Python **mà đồ thị bao gồm** (đã có trong đồ thị, hoặc file mới trong một thư mục đồ thị bao gồm) thay đổi **sau** khi `graph.json` được ghi. Tính cả thay đổi đã commit, chưa commit và file mới chưa track; file đã xoá vẫn tính, vì đồ thị còn node của nó.

## Lý do

Hai lần chạy skill đầu tiên báo nhầm:

- tính cả file mà `.graphifyignore` loại (chính script của skill trong `.claude/skills/`);
- tính các sửa đổi chưa commit dù `graphify update` đã đọc chúng (graphify đọc cây làm việc, không đọc commit).

## Kết quả

Kiểm tra cả hai chiều: sau khi cập nhật đồ thị thì báo "current"; sửa một file mà đồ thị bao gồm thì báo "stale".
