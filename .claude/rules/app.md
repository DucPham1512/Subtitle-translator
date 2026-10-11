---
paths:
  - "app/**"
---
## 6. Desktop app (UI/UX)

The app covers everything: episodes and runs, review, bootstrap, memory and dreaming. The CLI stays fully usable without it.

### 6.1 Architecture

- Separate package `app/` (PySide6). The core package `subagent/` has no Qt imports.
- **Long jobs** (run, render, bootstrap, dream) run as child processes via `QProcess`, calling the CLI with `--progress json`. The UI parses progress lines. A crash or GPU error in a job cannot freeze or kill the app, and cancelling (terminating the process) is safe because stages resume.
- **Short operations** (reading memory, saving the review draft, pinyin for one line, rule checks) run in-process on a `QThreadPool` worker, never on the UI thread.
- **What the app writes:** `review_draft.jsonl`, audit samples and marks (`audit_sample.jsonl`, `audit_marks.jsonl`, 6.11), bootstrap inputs (`cast.md`, clips, sprites, `seed_draft.json`), config and `.env` through the settings screen, and memory only through `MemoryManager`. Nothing else.
- **Refresh:** the app watches `work/<episode>/state.json` with `QFileSystemWatcher` to update statuses.
- **UI preferences** (language, window layout, splitter sizes, shortcuts, last opened line) are stored with `QSettings`, not in `config.yaml`.

### 6.2 Navigation

- Left sidebar: Episodes, Review, Memory, Bootstrap, Dreaming, Audit, Settings. Episodes is the start screen.
- **Series picker** at the top of the sidebar (5.2a; hidden in the single-series layout): the series this window shows. Choosing another one sets `series.default` and rebuilds the window around it (every screen reloads; refused while a job runs). **New series…** asks for an id, a name, the translation style (register; listed by name from `prompts/registers/`, **New style…** creates one: id, name, pronoun words, translator instructions prefilled from a template, 5.11) and an optional work folder (typed, or **Choose…** for a folder picker that opens at the shared work folder), creates the series and opens its Bootstrap screen. Jobs run for the window's series (`$SUBAGENT_SERIES`).
- Status bar: running job and stage, running cost vs budget, device in use (GPU / CPU).

### 6.3 Episodes and run screens

- **Episode table:** id, file, stage progress, status (`new`, `running`, `awaiting_review`, `done`, `failed`, `missing`), flag count, cost (`+ ?` when some calls have no price; the tooltip names the models and gives the cost per agent).
- **Add episodes:** Add files (multi-select), Add folder (with an "include subfolders" checkbox), or drag and drop files and folders onto the table. A confirmation dialog lists file → detected episode number (editable), flags duplicates and files without a detected number, and registers nothing until confirmed (5.21).
- **Missing videos:** rows with status `missing` show a Relink button.
- **Order warning:** running an episode while an earlier one is not done shows a warning dialog.
- **Batch:** the table allows selecting several episodes; Run (auto / human review) with more than one selected starts one `batch --rerun` job in episode order after a confirmation listing the episodes to run, the ones that run again (done or waiting for review: drafts replaced), earlier unfinished episodes left out, and what happens on a failure; in auto mode one Overwrite / Keep both / Cancel choice covers every episode whose output exists. The run panel shows the current episode ("episode ep007 (3/12)") and resets the stage bars for each.
- **Actions:** Run (auto / human): always processes the episode again (`run --rerun`, user decision 2026-10-02); for a `done` or `awaiting_review` episode a confirmation lists the results that will be replaced. Resume does only what is missing (a waiting review opens instead). Rerun from stage (with confirmation listing the results that will be discarded), Render, Open output folder (selects the finished video in Explorer), Open report, Clean temporary files.
- **Output conflict:** when the output file already exists, the dialog from 5.22 (Overwrite / Keep both / Cancel) appears before rendering starts.
- **Run panel:** per-stage progress bars (every pipeline stage including Script review, plus memory, voices, render, report, cleanup), live log tail, cost so far vs budget, Cancel. On failure: the error in plain language and the stage to resume from.

### 6.4 Review screen

Three regions:

- **Line list (left):** columns: state (approved / flagged / pending), time, speaker → listener, zh, vi.
  - Order: always chronological (user decision). Flagged lines are found with the flag filter.
  - Filters: flag group (`retry_cap`, `sprite_unresolved`, `low_speaker_conf`, `non_dialogue_suspect`, `script_ocr`, `script_suspect`, `ocr_uncertain`, `check_pinyin`, rule warnings), deleted, speaker, unapproved only. Search across zh and vi.
  - Header counter: flagged remaining (deleted lines excluded), approved / total, deleted.
- **Preview (top right):** mpv player showing the video with the mask applied and the draft subtitles rendered (6.5). Selecting a line seeks to 0.5 s before its start and plays it once. Controls: timeline slider (click or drag), back / forward 5 s, previous / next frame, play / pause, replay line, loop line, speed 0.5× / 1×.
- **Editor (bottom right):**
  - Editable: zh, pinyin (auto-generated; editing it sets `pinyin_overridden`; Regenerate discards the override), vi (Vietnamese input methods work), speaker and listener (dropdowns of known characters and the episode's new voices), line type.
  - **New character…:** creates a character without leaving review (id, Chinese and Vietnamese names, description), saved through the Memory Manager as a human edit (locked), and assigns it to the line's speaker or listener.
  - **Who is this character?** Under the speaker / listener row, a card for the line's speaker: its picture, "first seen epXXX", description, aliases ("called …"), and ▶ playing a voice sample. **Browse characters…** opens every id the line can take (characters, the episode's new voices, NPCs created in review, candidates on probation) with the same card per row; "Use as speaker" / "Use as listener" assigns one (one undo step). Cards come from `subagent/character_card.py`: name and description from memory (or the candidate), first episode from appearances (or the candidate, or the first reviewed episode it speaks in). The sample, most trusted first: the reviewer's choice; the bootstrap voice clips and sprite templates the reviewer curated (`data/bootstrap/voices|sprites/<id>/`); a line the reviewer approved (finished episodes, or approved in the review under way) with that speaker, the longest ≥ `voice.learn_min_ms`, preferring one with a confirmed box (marked talking or named this character by the reviewer in On screen, or recognised as it by the sprite bank; the machine's talking sprite alone is not trusted). Unreviewed lines are never used (user decision 2026-10-04: an unreviewed guess gave the narrator another character's sprite). From a reviewed line a ≤ 4 s WAV clip (`media.extract_clip`) and the box's picture (the analysed frame, else the video frame) are cut once into `cache/character_cards/<id>/`. **Use this line** on the card makes the current line its speaker's sample: its voice, and the box shown as talking in On screen (nobody marked talking: no picture, e.g. a narrator), kept in `data/character_cards/<id>/` (`pin.json`, `sample.wav`, `picture.png`); it changes the card only, memory learns nothing from it. Loaded in workers.
  - **New NPC:** gives the line's speaker the next free automatic id of the episode (`npc_<ep>_<n>`, after the voice stage's new voices), shown as "(new NPC)"; nothing is written to memory. The reviewer uses the same id on the character's other lines; at finish it is treated like a new voice of the episode and goes on probation (5.15b) when it speaks ≥ `memory.probation_min_lines` approved lines. The speaker / listener dropdowns also offer candidates on probation that may come back in this episode ("on probation since ep005"), so a return the voice stage missed can be assigned by hand.
  - **Original:** under the Chinese field, the original subtitle pixels (the subtitle band of the frame the cast stage used: the line's middle on the `cast.sample_fps` grid, `video.subtitle_band`), unmasked, to check the OCR text. Loaded in a worker (`Services.line_frame`), the last 40 lines cached; shows why when the video is missing. Below it, **OCR read**: what the recognizer read for the line after pre-processing (`Services.line_ocr_crop`: the line's first reading with the line's raw text, from `ocr_crops/`), at its position in the band, grey where nothing was read; after cleanup or without pre-processing it says so.
  - Read-only context: flags with reasons, script review note, evaluator feedback per attempt (with "Evaluator suggests: …" when its suggestion differs from the current Vietnamese, also on lines that passed), glossary terms found in the line with their required vi forms, and the pronoun pair for the chosen speaker → listener.
- **Right side views** (tabs): **Line** (preview player + editor, as above) and **On screen** (5.8b), where the frame the cast stage used fills the player's place and the recognition table the editor's place (same split sizes). The frame shows every character box: green recognised, orange unknown sprite (`u…`), red outline the talking sprite, each labelled with its position and name. Each table row shows the box's recognised name and similarity, a Talking checkbox (one at most; unticking records "nobody on screen talks"), and a "Correct to" dropdown (as recognised / a character / Not a character). On the picture (boxes drawn at screen scale, labels 11 px): drag a box to move it, a corner to resize it, empty space to draw a box around a missed character (blue, row "A1": choose its character; "Remove this box" or Delete removes it). All of it is one editable part of the line (`cast_labels`, `cast_boxes`, `cast_added`, `cast_talking`: autosaved, one undo step per change, edits.jsonl) and teaches the sprite bank at finish review. **On screen checked** (checkbox under the table, Ctrl+K; `cast_checked`, an edit like the others): the reviewer confirms the line's boxes, names and talking mark as they now stand, so a box left alone counts as confirmed rather than unchecked; such lines are the gold for measuring character recognition (user decision 2026-10-04: checked on every line of 5 replay episodes, the other 11 kept for tests and tuning). The picture is the saved analysed frame when present. The action buttons stay below both views.
  - Live rule checks while typing (line length, CPS, glossary terms, pronoun terms), shown as warnings.
- **Actions:**
  - Approve and next; Approve all remaining non-flagged lines (with confirmation); Finish review (enabled when every non-deleted line is approved; validates, then starts memory update, voice learning and render as a job).
  - Delete line / Restore line: a deleted line is not rendered and not used as memory evidence; it stays in the list, greyed out.
  - Reset line: undo every review change to this line (back to the pipeline's version).
  - Discard review…: replace the whole draft with the pipeline's output, after confirmation. Rerunning a stage (6.3) replaces the draft too.
- **No retranslation:** the review screen never calls an LLM. The user edits lines directly.
- **Draft safety:** every change autosaves to `review_draft.jsonl` (debounced 1 s, atomic write). Undo / redo per line. Reopening an episode restores the draft and the last selected line.

Keyboard shortcuts (defaults; configurable in Settings). The whole review is doable without the mouse.

| Action | Shortcut |
|---|---|
| Approve and next | Ctrl+Enter |
| Next / previous line | Ctrl+↓ / Ctrl+↑ |
| Replay line | Ctrl+R |
| Play / pause | Ctrl+Space |
| Toggle loop | Ctrl+L |
| Focus vi field | Ctrl+E |
| Undo / redo | Ctrl+Z / Ctrl+Y |
| Search | Ctrl+F |
| On screen checked (tick / untick) | Ctrl+K |

### 6.4b Partial review (`partial_review.py`, `python -m subagent partial-review EPISODE`)

- **Start:** the review screen's "Partial review…" button (enabled with some lines approved and some remaining) saves the draft synchronously and runs the job (QProcess, `--progress json`). Approved, non-deleted lines are "reviewed"; unapproved ones are "remaining". It can run any number of times.
- **Session-only learning:** nothing is written to memory; the real learning happens once at finish review (no double counting, no half-learned later edits).
  - Sprites: sprite bank + `sprite_learning.plan` over the reviewed lines (their speakers, talking marks, box names, moved/drawn boxes via `apply_review_edits`); every character in the remaining lines is matched again against that session bank (stored descriptions: seconds, no detection rerun).
  - Voices: voice bank (archived left out) + this episode's reviewed lines (≥ `voice.learn_min_ms`; a character not in the bank needs `voice.learn_min_clips` lines, e.g. the episode's `npc_…` voices; a known one is the clip-count-weighted mean with its centroid); remaining lines' audio is matched again (`stages/voice.match_events`) when at least one voice changed; otherwise the pipeline's voice match (`speakers.jsonl`) is used.
- **Suggestions** (`partial_review.suggest`; never for a line whose speaker the reviewer already changed, or non-dialogue):
  - voice sure (`fixed` / `new_voice`): suggest its speaker unless the talking character disagrees ("picture and voice agree" / "voice");
  - voice `confusable`: the talking character, only if it is one of the voice candidates;
  - no usable voice: the talking character alone ("talking on screen").
- **Output** `partial_review.jsonl` (`PartialSuggestion`: per remaining line, the characters on screen now, talking character, voice match, suggested speaker and reason).
- **In the review screen:** each remaining line with a suggestion gets it as its speaker (user decision 2026-10-02), flagged `partial_speaker` + `check_pronouns` (the Vietnamese pronouns may follow the old speaker; no LLM is called); one undo step per line restores speaker and flags. Notes show the suggestion, talking character and voice; the On screen view shows the session names. A later partial review may change a `partial_speaker` line again (it is still the machine's choice); a speaker the reviewer set is never changed. The "Use <name>" button remains for drafts from before this change (flag `partial_suggestion`).

### 6.5 Live preview

- Uses `render.build_ass()` and `render.build_mask_filter()` (5.19), so the preview matches the final burn-in.
- mpv loads the source video with `vf=lavfi=[<mask filter>]` and the draft ASS written to `work/<episode>/preview.ass`, with `sub-fonts-dir` pointing at `fonts/`.
- After an edit, regenerate `preview.ass` (debounced 300 ms) and send mpv `sub-reload`.
- If libmpv cannot load, the review screen still works without the preview and shows how to fix it.

### 6.6 Bootstrap wizard

1. **Calibrate:** show a frame; the user drags a rectangle over the subtitle band; on release it snaps to be symmetric around the frame's vertical centre line (subtitles are centred; the side closer to the centre widens, so nothing selected is lost; top and bottom stay as drawn; `Band.centered`); fractions are saved to config. Below it, **Subtitle style** (5.4a): the learned style (episode, date, polarity, fill, outline, stroke, letter height) or "not learned yet", "Learn subtitle style from this episode" (runs `calibrate EPISODE --style` as a job; replacing a learned style asks first) and "Show style preview" (the episode's `calibration/style.png`, opened when the job ends). (The CLI `calibrate` command stays for headless use.)
2. **Cast and synopsis:** edit `cast.md` in an editor pane, or import a file.
3. **Voice clips:** per character, mark in / out points on an episode timeline in the preview (timeline slider, ±5 s, frame step), or import WAV files. Play each clip back. A counter shows clips per character (3–5 recommended).
4. **Sprites:** per character, pause the preview and drag a rectangle to crop a template; thumbnails list. Shown only when `sprite.enabled`.
5. **Generate seed:** runs the bootstrap job.
6. **Review seed:** editable tables for characters, pronoun pairs and glossary; confusable pairs read-only with similarity scores and clip playback. Approve writes everything as locked.

Steps 3–4 can be reopened later to add a new character.

### 6.7 Memory screen

Tabs:

- **Characters, Glossary:** searchable, sortable tables; inline edit, add, delete; lock toggle; source and last-updated columns. Characters have an "Also called" column (aliases, edited as "a; b"). Deleting a locked entry asks for confirmation. Characters also show `status` (active / kept / archived) and its reason; editing them sets the status by hand.
- **Pronoun matrix:** grid of speaker (rows) × listener (columns). Each cell shows `self_term / address_term`; click to edit. Cells with context variants show a count badge.
- **Briefings, Style rules:** Markdown view with an edit mode.
- **Voice bank:** clip counts per character, similarity heatmap highlighting confusable pairs, clip playback, recompute button.
- **Line decisions:** the script reviewer's memory (text, removed, kept, last episode); editable, edited rows become locked.
- **Conflicts:** entries from `conflicts.json`, each with accept / reject.
- **Character updates:** waiting updates from `character_updates.json` (5.15c): episode, character or pair, field, current, proposed, why it waits (locked / auto mode unchecked); the evidence lines of the selected row below; Accept change / Reject change.
- **History:** memory commits (date, message, number of changes). Selecting one shows a per-table diff (rows added / changed / removed, from `memory_log`). "Roll back to this version" asks for confirmation and explains that a new commit is created and nothing is lost. Any table row also has a History action (right-click) showing that entry's changes.

All edits go through `MemoryManager.apply(source="human")` and become locked. Editing and rollback are disabled while a job is running.

### 6.8 Dreaming screen

- Run dream as a job.
- Proposals grouped by kind, each showing before / after and its evidence (click to open the line read-only in that episode's review).
- Unlocked proposals are preselected as accepted; proposals touching locked entries are preselected as rejected and highlighted.
- Apply writes the checked ones through the Memory Manager in one commit; unchecked ones are rejected and never proposed again (5.18).
- The header shows how many proposals were left out because they were rejected before. "Forget rejected proposals…" clears that list after confirmation.

### 6.9 Settings screen

- **General:** default review mode, device, budget, sprite check on / off, render encoder and quality, font sizes.
- **Files:** output folder (folder picker; required before the first render), output name suffix, working folder location, automatic cleanup on / off, video extensions, episode-number patterns with a test field that shows the number detected from a sample file name.
- **Advanced** (`app/views/settings_form.py`; user decisions 2026-10-11): every config field as a form, built from the config model (`subagent/settings_schema.py`). Sections listed on the left with a search box (filters fields by key or help text across sections); per field its control, a tag "this series" / "shared" (where a change is saved, 5.2a) and its help: the comment on its line in config.yaml / series.yaml, then the note next to the field in `config.py`. Controls: fixed values (Literal) and known sets (`show.genre_register` → the translation styles; `bench.baseline` / `baseline.name` → the baselines, "(none)", the latter editable) → dropdown; lists → tags (Enter or comma adds, × or Backspace removes; suggestions where known, e.g. flag names for `voice.learn_auto_allowed_flags`; numbers only for `sprite.scales`); int / float → number boxes; on/off → checkbox; text → text box; `output.folder`, `paths.work_dir`, `render.font_dir` → text box + Choose…; `llm.providers` → one group per role (base URL, key name, model); `llm.prices` → a table (model, input, cached input, output) with Add / Remove row. `series.default` is not shown (the series picker sets it). **Save changes** writes only the changed values (`config.save_settings`), **Discard changes** reloads; **Edit as YAML…** opens the raw editor for config.yaml or series.yaml (validated merged before saving). Values saved in the other tabs go to the right file (5.2a).
- **API keys:** masked fields saved to `.env`; a test-connection button sends one minimal request.
- **Language:** English / Tiếng Việt; applied after restart (the app offers to restart).
- **Theme:** follows the Windows light / dark setting.
- **Shortcuts:** remap review shortcuts.

### 6.10 Interface language (i18n)

- Every user-visible string goes through `self.tr()`. Translations live in `app/i18n/app_en.ts` and `app_vi.ts`, compiled to `.qm` and loaded with `QTranslator` at startup.
- Only the UI is translated. Data (zh, pinyin, vi, memory content, logs) is shown as is.
- Pipeline errors carry stable `error_code` values; the app maps codes to translated messages and falls back to the English message.

History, measurements and reasons for this area (for the owner; not needed to code): `knowledge_vault/decisions/thiết kế - lý do các lựa chọn.md`, `knowledge_vault/decisions/đo lường - nhận diện nhân vật và giọng.md`.
