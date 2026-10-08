---
paths:
  - "subagent/memory/**"
---
### 5.15 Memory Manager (`memory/manager.py`)

- **Responsibility:** the only component allowed to write memory. Everything else reads through `memory/store.py` read functions.
- **Interface:** `apply(proposals: list[MemoryProposal]) -> ApplyResult`, `update_briefings(episode_id, approved_lines)`, `commit(message)`, `history(limit)`, `diff(commit_sha)`, `entry_history(table, key)`, `rollback(commit_sha)`.
- **Write rules:**
  - A locked entry is changed only by a proposal with `source="human"`.
  - Proposals from `translator` are applied only if their evidence lines were approved.
  - Human edits create or update entries with `locked=1`.
  - A proposal that conflicts with an existing unlocked entry is applied only if it has more evidence than the current entry (`memory_log.evidence_count`); otherwise it is written to `data/memory/conflicts.json` / `conflicts.md` for review.
  - Only human edits delete entries. Deleting a character also deletes its pronoun pairs, voice and confusable pairs.
  - Identical proposals (same kind, source, payload) are merged and their evidence pooled. Characters are applied before the entries that reference them.
  - Every write runs in a transaction and adds a `memory_log` row. Rejected proposals are logged as `op="rejected"` with a reason.
  - An unnamed automatic character (auto id, `name_vi` still equal to the id) takes the first name proposed for it, without the evidence comparison; the id is then replaced by the name in every `briefings/*.md`. Later renames follow the normal rules; a name set by a person is locked.
- **After each episode:**
  - Probation (5.15b, `memory.probation`): candidates that came back are promoted, this episode's new voices and new translator-named characters become candidates, proposals about candidates wait, expired candidates are dropped. With probation off: new voices that approved lines still use (as speaker or listener) become characters at once (`name_zh` = `name_vi` = id, unlocked, source `translator`).
  - Apply approved proposals and human-edit proposals.
  - Record the reviewer's remove / keep decisions in `line_decisions` (5.13a).
  - One `utility` call writes `briefings/<episode_id>.md`, updates `story_so_far.md` within its word cap, and appends to `INDEX.md`. The same call returns `character_fates`: only fates the script states explicitly (`dies`, `leaves`, `returns`) with the stating line as evidence.
  - Character lifecycle (5.15a): record appearances, then update statuses. The commit message counts the moves (`episode ep006: 12 writes, 1 archived`).
  - `git add -A && git commit -m "episode <id>: <n> writes"` in `data/memory/`, then fill `commit_sha` on the new `memory_log` rows.
- **Manual edits from the app:** go through `apply()` with `source="human"`, become locked, and are committed as one commit per save (`manual edit: <n> changes`).
- **Rollback:** `rollback(sha)` closes all DB connections, restores the folder with `git checkout <sha> -- .`, and commits `rollback to <sha>`. History is never rewritten (no `reset --hard`), so a rollback can itself be undone. Refused while any job is running.
- **Locking:** memory writes take `data/memory/.lock` so the app and a running job never write at the same time.
- **All or nothing:** the episode update snapshots the memory files first and restores them if any step fails (NFR-R4).

### 5.15a Character lifecycle (`memory/manager.py: update_lifecycle`)

- **Appearances:** after each episode, every character used as speaker or listener in an approved, non-deleted line gets an `appearances` row (rerun-safe). The first run backfills earlier episodes from their `approved.jsonl`.
- **Generic characters** (`characters.generic`, set only by a person: Memory → Characters "Generic" checkbox): one name for many individuals (e.g. all fish, passers-by). Lines can be assigned to them and they keep their pronoun pairs, but they are left out of voice matching, voice learning, picture matching and sprite learning (`MemoryStore.unmatchable_ids`, with archived characters), never archived by the lifecycle, and marked "(generic: …)" in the prompt's characters block.
- **Rules** (`memory.character_lifecycle`; unlocked characters only: automatic `npc_…` ones and translator-created ones; locked characters are never changed):
  - stated `dies` / `leaves` → `archived`, even if kept;
  - stated `returns` → `kept`;
  - appears in two consecutive episodes (by number) → `kept`; kept characters are never archived for absence;
  - `active` and absent for `memory.archive_after_absent` processed episodes after its last appearance → `archived`;
  - an archived character used again in an approved line → `active` (then the rules above apply).
- **Archived means hidden, not deleted:** left out of the characters and pronoun blocks of every prompt and out of voice matching; rows, voice and history stay. Review dropdowns show it marked "(archived)".
- Every change is a `memory_log` row (source `system`, reason = `status_note`) inside the episode's commit, so it can be rolled back. A person can set `status` / `status_note` in Memory → Characters (that locks the character); model proposals cannot set them.
- Until the visual cast check exists, an appearance is only as reliable as the speaker labels: confirmed in human mode, the machine's guess in auto mode.

### 5.15b Probation for new characters (`memory/probation.py`, `memory/manager.py: probation`)

- **Candidate:** after an episode, a new voice of that episode (`npc_<ep>_<n>`) or an id the translator proposes as a new character, with ≥ `memory.probation_min_lines` approved, non-deleted dialogue lines as speaker, becomes a row in `candidates`: its name (from the translator's proposal, if any), its voice (mean of those lines in `voice_embeddings.npz`) and its look (the unrecognised talking sprites on those lines, `candidate_sprites`). Fewer lines: nothing is remembered (the proposal is logged as rejected). Candidates are not characters: not in the Characters list, prompts' characters block, voice bank or sprite bank; voice and sprite learning skip them.
- **Waiting proposals:** pronoun pairs involving a candidate are stored with it (`pending_json`) and applied when it is promoted. A name proposed for a candidate is kept if it has none yet (first name wins).
- **Coming back:** in an episode numbered 1..`memory.probation_window` after its first, the voice stage gives matching lines the candidate's id (5.8). At finish, the candidate's lines in that episode count: approved lines with it as speaker (human mode), only trusted lines in auto mode (`voice_learning.trusted_auto_lines`: voice, translator and first evaluation agree). Each counting line's talking sprite is compared with its look: a recognised known character talking or a different-looking sprite disagrees; a sprite ≥ `cast.match_similarity` like its look agrees; no talking sprite or no look remembered is neutral. Promoted when at least one line counts and disagreements < agreements + neutral lines. In human mode the reviewer's assignment is the evidence: the candidate is promoted even when the picture disagrees (user decision 2026-10-05: the talking-sprite check overruled a reviewer-assigned return, and the NPC fell out of its window), and the look the picture disputes is not copied into the sprite bank (sprite learning relearns it from the reviewed lines). The look check still gates auto mode.
- **Promotion:** a `characters` row (unlocked; name or id), the candidate's voice in `voice_bank` (voice learning refines it), its look in `sprite_bank`, an `appearances` row for the first episode, then the waiting proposals. `memory_log` rows with source `system`; the episode commit counts it (`1 promoted`).
- **Dropped:** a candidate still waiting when an episode numbered beyond its window finishes. Rows stay (status `dropped`), so it can be inspected or rolled back.
- **From review:** an NPC created in review ("New NPC", 6.4) is added to the episode's new voices at finish (`characters.review_voice_ids`); a candidate assigned by hand in a later episode counts as coming back like one the voice stage found.
- Rerunning an episode's finish rebuilds that episode's candidates. With `memory.probation: false` the old behaviour applies (new voices become characters at once).

### 5.16 Human-edit mining (part of Memory Manager import step)

- A changed `speaker`/`listener` → appended to `data/memory/speaker_corrections.jsonl` for dreaming (mining an episode again first drops its earlier entries).
- A `vi` change where a glossary term's translation differs → glossary proposal with `source="human"`.
- Pronoun changes are not parsed in code; dreaming extracts them (5.18).

### 5.17 Memory bootstrap (`memory/bootstrap.py`, runs before episode 1)

- **Inputs:** `config.yaml`, `data/bootstrap/cast.md` (cast list, relationships, synopsis), `data/bootstrap/voices/<char_id>/*.wav` (3–5 clips each), `data/bootstrap/sprites/<char_id>/*.png`, optionally episode 1 events. Clips and sprites can be captured from episode video in the app's bootstrap wizard (6.6).
- **Steps:**
  1. `utility` call drafts characters (Hán-Việt names), initial pronoun pairs from the stated relationships, and seed glossary terms.
  2. Compute voice-bank centroids; compute pairwise centroid similarity; pairs ≥ `voice.confusable_similarity` go to `confusable_pairs`.
  3. Write the seed draft to `data/bootstrap/seed_draft.json`; the app shows it for review and editing (6.6).
  4. On approval, the Memory Manager writes everything with `locked=1` and commits.
- Rerunnable per character: adding a new character's clips later recomputes only that centroid and its pair similarities.

### 5.18 Dreaming (`memory/dreaming.py`, offline)

- **Trigger:** `python -m subagent dream`, run between episodes (manually or by a scheduler).
- **Inputs:** memory (characters, glossary, pronoun matrix, style rules), `edits.jsonl` not yet seen (`dream_state.json`), `speaker_corrections.jsonl`, up to `memory.dream_max_lines` approved lines, glossary terms used inconsistently, and the rejected proposals.
- **Tasks:**
  - Glossary: find same zh with inconsistent vi across approved lines; propose one form.
  - Relationships: detect pronoun usage in approved lines that differs from the matrix; propose updated pairs (with `since_episode`).
  - Briefings: when `story_so_far.md` reaches 90% of its word cap, compress it to 70% (one `utility` call), proposed as a briefing change.
  - Style rules: turn recurring human edits into short style rules with one example each (`add`, `use` for an existing rule, `remove`), keeping at most `memory.style_rules_max`, dropping the least-used.
- **Filters in code** (nothing to decide is never shown):
  - glossary proposals equal (case-insensitive) to the current entry, and duplicates, are dropped;
  - a style rule of the form "Dịch X thành 'Y'" is a term translation: it becomes a glossary proposal;
  - `add` / `use` of a rule that already exists and `remove` of a rule that does not are dropped;
  - proposals matching a rejected one (by signature: glossary zh + vi, pronoun pair + terms, style rule action + text) are dropped and counted (`previously_rejected`); the prompt also lists the last 60 rejections.
- **Output:** proposals with `source="dreaming"` go through the Memory Manager. All proposals are written to `data/memory/dream_proposals.json` and reviewed in the app's dreaming screen (6.8); unlocked ones are preselected for acceptance, ones touching locked entries are preselected for rejection. The CLI option `dream --auto-apply` applies only proposals that touch no locked entry.
- **Rejection memory:** applying in the app records every unchecked proposal in `dream_rejections.json` (signature, description, date) in the same commit (`dream: <n> writes, <m> rejected`). `--auto-apply` skips proposals on locked entries without recording them as rejected. "Forget rejected proposals" in the app clears the list (its own commit).
- Dreaming never writes directly and never deletes locked entries.

History, measurements and reasons for this area (for the owner; not needed to code): `knowledge_vault/decisions/thiết kế - lý do các lựa chọn.md`.
