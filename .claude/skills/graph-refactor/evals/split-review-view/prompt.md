---
tags: [graph-refactor]
max_turns: 80
timeout_seconds: 1800
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

app/views/review.py feels way too big. Use the graph to work out how ReviewView should be broken up. Plan only for now, I want to see it before anything changes.
