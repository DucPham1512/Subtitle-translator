---
paths:
  - "subagent/stages/pinyin_gen.py"
  - "subagent/stages/windows.py"
  - "subagent/stages/translate.py"
  - "subagent/stages/evaluate.py"
  - "subagent/stages/script_review.py"
  - "subagent/stages/review.py"
  - "prompts/**"
---
### 5.9 Pinyin (`stages/pinyin_gen.py`)

- **Responsibility:** deterministic pinyin for corrected Chinese.
- **Details:**
  - Load glossary names into jieba's user dictionary and their pinyin into pypinyin's phrase dictionary, so names are segmented and read correctly.
  - `pypinyin.lazy_pinyin(..., style=Style.TONE)` over jieba segments; join syllables within a word, space between words.
  - Polyphone fallback: a small config list of high-risk characters (e.g. 了, 行, 长, 得, 还) that occur outside a known phrase are sent in one batched `utility` call per episode. Everything else stays deterministic.
  - Regenerate pinyin for any line whose `zh` a human edits.

### 5.10 Scene windowing (`stages/windows.py`)

- Split events into windows at gaps > `windows.gap_ms` or at `windows.max_lines`.
- Each window carries `context_overlap` previous lines (already translated) as read-only context.

### 5.11 Translator (`stages/translate.py`)

- **Responsibility:** translate a window into Vietnamese and decide speaker and listener per line.
- **Prompt layout:**
  1. Static system prompt (`prompts/translator_system.md`): subtitle style, register from `show.genre_register`, xưng hô rules, length limits, output schema.
  2. Memory prefix (built once per episode): characters (archived ones left out; aliases shown as "called: …", 5.15c), full glossary, pronoun matrix (pairs with archived characters left out), `story_so_far.md`, `style_rules.md`, then the episode's new voices (id, line count, first time; a returning candidate also with its name, description and aliases) and the known characters without a voice sample.
  3. Variable: previous context lines, then window lines as JSON with `event_id`, `zh`, `speaker_candidates` and their status.
- **Output per line:** `speaker`, `listener`, `speaker_conf`, `vi`, optional `proposals` (new glossary terms, new or changed pronoun pairs, new characters) with evidence event ids.
- **Rules given to the model:**
  - `fixed` speaker: keep it unless the dialogue makes it impossible, then say why in `notes`.
  - `confusable`: choose between the listed candidates only.
  - `disputed` (picture veto, `translate.picture_veto`): before translation, a line whose voice match is `fixed` / `new_voice` / `confusable` becomes `disputed` when the clearly talking sprite (5.8b) is a recognised character other than the voice's top candidate (or, for `confusable`, not among its candidates); with `any`, also when the talker is unrecognised (`fixed` / `new_voice` only). The recognised talker is added to the candidates. The translator chooses between the candidates by the dialogue, or leaves the speaker null when neither fits; it does not follow the voice by default. Off by default (measured: `knowledge_vault/decisions/đo lường - nhận diện nhân vật và giọng.md`).
  - `new_voice`: keep the new voice id unless the dialogue shows it is a known character (e.g. one without a voice sample).
  - `unknown` / `too_short`: choose a character present in the scene only when the dialogue makes it clear; otherwise speaker null. Never guess.
  - Speaker / listener ids: the Characters table or the episode's new voices (rule checks accept both).
  - An automatic character (`npc_…`) whose identity the dialogue reveals (name, title, role, form of address): propose a `character` with the same id and `name_zh`, `name_vi`, `description`. Never a new id.
  - Use the pronoun matrix for the (speaker, listener) pair. If no pair exists, propose one.
  - Glossary terms must be used exactly.
  - `on_screen` / `unrecognised_on_screen` / `talking` (5.8b): weak evidence, weaker than the voice and the dialogue (user decision 2026-10-02: the talking sprite made the translator override sure voices). Never a reason to change a `fixed` or `new_voice` speaker; a tie-breaker between `confusable` candidates, or for `unknown` / `too_short` lines together with a clear dialogue clue; never a speaker from the picture alone. With `translate.picture_evidence: tiebreak` (default) the picture fields are left out of `fixed` / `new_voice` lines entirely; `all` shows them everywhere, `off` nowhere.
  - `non_dialogue_suspect`: decide whether the line is dialogue. If not, set `line_type` to `sign`, `title` or `sfx`, leave speaker and listener empty, and translate it as on-screen text.
- **Translation styles (registers)** (`subagent/registers.py`; user decision 2026-10-11): one file per style, `prompts/registers/<id>.md`, shared by every series: YAML front matter (`name`, `pronoun_terms`) and the register section of the translator prompt. A series selects one with `show.genre_register`; `{{register}}` in `prompts/translator_system.md` is replaced by its text (`translate.translator_static`; a prompt with inline `<!-- register:… -->` blocks still works). The translate stage's prompt hash covers the style file. The style's `pronoun_terms` become `translate.pronoun_terms` when the merged config sets none (`load_config`), so the pronoun rule check and the benchmark use the words of the series' style; an explicit list in config.yaml / series.yaml overrides. New styles are created in the app (New series… → New style…: id, name, pronoun words, instructions prefilled from a template) or by adding a file; an existing style file is never overwritten (series may use it).
- **Register for cổ trang / tiên hiệp** (`prompts/registers/co_trang_tien_hiep.md`, the built-in style; moved out of the translator prompt 2026-10-11 with the assembled prompt byte-identical):
  - Names, titles, sects, places, cultivation realms, techniques and items use Hán-Việt readings (e.g. 筑基 → Trúc Cơ), recorded in the glossary with the matching `type`.
  - Classical pronoun system: ta / ngươi, huynh / đệ / tỷ / muội, sư phụ / đồ nhi, sư huynh / sư muội, tại hạ, bổn tọa, lão phu, and similar. The pronoun matrix decides which pair applies; the prompt only lists the system.
  - Keep a classical tone but readable subtitle Vietnamese; avoid modern slang and modern pronouns (anh / em, tôi / bạn) unless the matrix says so.
  - Chengyu (成语) are translated by meaning, or by an established Hán-Việt form when one exists; recurring ones go into the glossary as `idiom`.
- **Reviewer corrections:** the memory prefix ends with up to `memory.correction_examples` recent `vi` edits from finished reviews (zh, machine vi → reviewer vi; newest episodes first, deduplicated). The translator applies the same preferences; the evaluator gets the same block (5.12).
- **Retry input:** on a failed evaluation, only the failed lines are resent, with `earlier_attempts` (each earlier translation with its feedback), the `evaluator_suggestion`, and the rest of the window as context. A line that returns an answer it already tried keeps that verdict and is not retried again.
- The prefix actually sent is saved to `work/<episode>/memory_prefix.md` for inspection.

### 5.12 Evaluator (`stages/evaluate.py`)

- **Responsibility:** decide whether each translated line is acceptable.
- **Two layers:**
  1. Rule checks in code, run first (free): line length ≤ `max_line_chars`, lines per event ≤ `max_lines_per_event`, characters per second ≤ `max_cps`, every glossary zh term present in the line **as a whole word** has its vi form in the translation (jieba segmentation with multi-character glossary terms kept whole and HMM on, so runs of unknown characters such as the show's coinages 降鱼钓法 / 何罗鱼 form one word; a term that starts or ends inside a longer word does not count, e.g. 鱼 inside 钓鱼 / 鱼钩; built when the rule context is created), pronoun terms (`translate.pronoun_terms`) used match the matrix for the chosen pair, speaker / listener are known ids (or the episode's new voices), a `confusable` speaker is one of the candidates, a `disputed` speaker is one of the candidates or null.
     - Reading speed (`cps`) is a soft failure unless `translate.retry_on_cps`: it is flagged `cps_exceeded` for review, never retried.
     - Lines with a hard rule failure skip the LLM rubric for that attempt.
  2. LLM rubric (`evaluator` role, different model family, `evaluate.criteria`): meaning, pronouns, register, naturalness, speaker. Scores 1–5; a line fails if any criterion < `evaluate.min_score` or a hard rule check failed. A line with any score below 4 gets the evaluator's corrected `suggestion`; it is kept on the evaluation even when the line passes (a 3 passes at `min_score: 3`), so the reviewer sees it (6.4). Only failed lines are sent back to the translator with it. A line repeating a mistake from the reviewer corrections scores at most 2 on that criterion. A `fixed` / `new_voice` line whose speaker is not the voice's first candidate scores at most 2 on `speaker` unless the dialogue itself shows who speaks (the picture or a guess is no reason; the evaluator sees the translator's `notes`).
- **Loop:** failed lines go back to the translator with feedback, max `translate.max_retries`. After the cap, keep the best attempt (passed, then no rule failures, then total score) and flag `retry_cap` plus the matching rule flags (`line_too_long`, `glossary_mismatch`, `pronoun_mismatch`, `speaker_invalid`, `missing_translation`).
- Other flags set on the final line: `cps_exceeded` (soft), `not_evaluated` (the rubric returned no score), `speaker_override` (translator changed a `fixed` voice speaker), `low_speaker_conf` (`speaker_conf < sprite.trigger_conf_below`).

### 5.13a Script review (`stages/script_review.py`)

- **Responsibility:** catch low-value lines the per-line evaluator cannot see, using the whole episode: repeats, OCR noise, unrelated text. Precision first: only lossless merges, the reviewer's own repeated decisions and confident model verdicts remove a line; everything else is flagged.
- **Rules (free):**
  - Identical text back to back with a gap ≤ `repeat_merge_gap_ms` is one subtitle split in two: `remove` (reason `repeat`, `keep_id` = the earlier line, which takes over the removed line's time). The display is unchanged.
  - A similar line (≥ `repeat_similarity`) within `repeat_window_ms` is only flagged.
- **Memory:** a text with at most `memory_max_han` Chinese characters that the reviewer removed ≥ `memory_auto_remove_min` times and never kept is removed (reason `noise`, source `memory`). Counts come from the `line_decisions` table.
- **Model pass:** one call per episode (`script_review.role`, task `script_review`, prompt `prompts/script_review_system.md` with general checks, plus the series' notes with this show's font misreadings, stray characters and slang, 5.2a) with the whole script (zh, vi, speaker, time) and the reviewer's past decisions (`example_limit` per kind). It returns only lines to remove or check. A removal needs confidence ≥ `remove_confidence`, otherwise it becomes a flag. At most `max_remove_share` of the episode's lines (min 1) are removed; the most confident are kept and the rest become flags.
- **OCR errors in real dialogue** (same call; user decision 2026-10-03): a line that is real dialogue but whose Chinese has an OCR error is not noise. The model returns `action: fix`, `reason: ocr`, the whole corrected line (`zh_fix`) and its context check (`evidence`); the prompt spells out the checks: a 7 becomes 了 only where the particle fits the grammar and a number does not (never deleted, never kept beside an added 了); a character such as 楚 / 姬 / 史 is stray screen text only at the edge of the line, outside its grammar, with the line complete without it, while the same character inside the sentence is the show's wording (euphemism, slang, a name); similar-looking characters and edge doubles only when the context makes the word clear. When it cannot write the corrected line it returns `check` / `ocr`. Code accepts a fix only with evidence, changing at most `fix_max_change_share` of the line, and refuses a 7 that is dropped, kept beside an added 了, or reads as a number (next to a digit, after 第, before one of `measure_words`); a refused fix becomes a `check` flag. Fixes are never applied: the line gets flag `script_ocr` and the editor's notes show the suggested Chinese and the evidence; the reviewer edits the Chinese (pinyin follows) and checks the Vietnamese, which was translated from the wrong text.
- **Output:** `script_review.jsonl` (`ScriptDecision`). The review draft applies it (5.14): removed lines arrive deleted (restorable) with flag `script_<reason>`; flagged lines get `script_suspect`, fixes `script_ocr`, and the note is shown in the editor. In auto mode removed lines are left out of the video; fixes are only listed.
- **Its memory:** after each finished review, the Memory Manager counts per normalized text what the reviewer removed and kept (`record_line_decisions`). Lossless repeat merges are not the reviewer's decision; short lines kept and pre-deleted lines restored count as kept. Locked rows (edited in the Memory screen) are not changed. Each episode's share is kept in `line_decision_episodes`, so finishing a review again replaces that episode's share instead of adding to it.

### 5.14 Review gate and review data (`stages/review.py`)

- **Draft:** one `ReviewedLine` per event, built from events, translations and pinyin, `approved=false`, flags merged from all stages. Two kinds of lines arrive already deleted (restorable):
  - noisy OCR fragments: `ocr_fragment` and at most `review.noise_max_han` Chinese characters or stray digits (`review.predelete_fragments`);
  - the script review's removals (5.13a).
- **Auto mode:** all lines become `approved.jsonl` (deleted ones stay deleted and are not rendered), `edits.jsonl` is empty; flagged lines are listed in `report.md`.
- **Human mode:** the stage writes `review_draft.jsonl`, sets the episode status to `awaiting_review`, and the pipeline stops. The gate reruns only when its inputs changed or it is forced, so an unchanged episode keeps work in progress.
- Review happens in the desktop app (6.4), which only edits `review_draft.jsonl` (autosaved, atomic writes).
- **Finish review:** `finish_review(episode_id)`, called by the app or by `python -m subagent finish-review EPISODE`:
  - Validate, skipping deleted lines: every line approved, speaker/listener ids exist (memory characters, the episode's new voices, NPCs created in review with this episode's number, or candidates whose probation window includes this episode), no empty `vi`.
  - Write `approved.jsonl` and `edits.jsonl` (per changed field, including `deleted`: before, after, event id), compared with the pipeline's original draft.
  - Continue with memory update and render.
- Review never calls an LLM. Pinyin for an edited `zh` is regenerated locally with pypinyin; polyphones in that line get the flag `check_pinyin` instead of an LLM call.

History, measurements and reasons for this area (for the owner; not needed to code): `knowledge_vault/decisions/đo lường - script review.md`, `knowledge_vault/decisions/đo lường - nhận diện nhân vật và giọng.md`.
