# Graph Report - Subtitle-translator  (2026-11-03)

## Corpus Check
- 214 files · ~168,319 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .qm 2, .example 1)

## Summary
- 3278 nodes · 11277 edges · 137 communities (110 shown, 27 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 684 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `75cae19a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_app.py
- LLM Client & Costs
- App Package & Jobs
- CastLine
- Memory Screen
- Band & Cast Panel Views
- partial.py
- Memory Manager Rows
- Audit Sampling
- test_feedback_loop.py
- Memory Manager Tests
- Bootstrap Wizard View
- New Voices & Characters
- register_episode
- Benchmark Suite
- Config Schema
- Output Delivery & ASS
- Series Management
- Cast Engine
- Video Preview (mpv)
- cast/learning.py
- Memory Store
- test_translate_review.py
- Character Cards
- Services
- OCR Engine & Geometry
- Subtitle Style
- Pipeline Runner & Locks
- CLI Episodes
- Episodes Screen
- Memory Proposals Apply
- Stage Table & State
- Voice Learning & Evidence
- Media (ffmpeg) Infra
- Audit & Dreaming Screens
- Settings & Run Panel
- Script Review & OCR Fix
- Frozen Baseline
- Bootstrap Seed
- YAML Comment-Preserving Edit
- Review Screen Shell
- Speaker Benchmark
- OCR Benchmark
- Episode Registry
- read_jsonl
- Ingest & Change Detection
- Character Browser
- Kernel Errors
- Translate Stage
- Dreaming
- Character Updates
- Voice Candidates
- New Series Dialog
- Review On-Screen Cast
- Voice Match
- Bench Run Sandbox
- Translation Registers
- Series-1 Voice Config
- ._open_preview
- Series-1 Cast Config
- test_parser_stages.py
- Video Render
- Architecture Guard Test
- pytest
- Frame Selector Widget
- Pinned Requirements
- Briefings & Style Rules
- Review Character Editor
- Top-level Config Keys
- kernel/__init__.py
- Settings Schema Introspection
- delivery.py
- conftest.py
- Memory Banks Writing
- LLM Provider Config
- OCR Preprocess Crop
- Pinyin Engine
- Voice Learning Tests
- Render Config
- Text Utilities
- load_state
- Memory & Translation Prompts
- SubtitleEvent
- Episode Memory Update
- Tag Editor Widget
- subagent/__main__.py
- Series-1 Band Config
- test_character_lifecycle.py
- ReviewedLine
- Job Runner
- LineHistory
- Flow Layout
- Prices Editor
- workspace/__init__.py
- core.py
- Audit Bar
- Settings Form
- Price Table Keys
- Memory Config Keys
- Series-1 series.yaml
- memory/__init__.py
- Settings Field Controls
- Device Detection
- Memory Aux Writes
- Series-1 OCR Config
- Series-1 Script Review Config
- App Entry Point
- test_character_updates.py
- test_new_voices.py
- Drop Table
- Translate Config
- symmetric_span
- .locked
- _no_real_ffmpeg
- Background Workers
- Vietnamese UI Fill
- character_dialog.py
- Series-1 Cast
- Raw YAML Dialog
- Audit Config
- Sprite Config
- Series-1 Review Prompt
- Fake mpv Player
- Audio Config
- Output Config
- Review Config
- Windows Config
- Briefing & Story Prompts
- Project Metadata

## God Nodes (most connected - your core abstractions)
1. `ReviewedLine` - 153 edges
2. `Config` - 140 edges
3. `Paths` - 137 edges
4. `read_jsonl()` - 127 edges
5. `MemoryStore` - 112 edges
6. `seed_memory()` - 107 edges
7. `write_jsonl()` - 102 edges
8. `ReviewView` - 96 edges
9. `Registry` - 91 edges
10. `EpisodeContext` - 88 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `find_root()`  [INFERRED]
  app/__main__.py → subagent/settings/config.py
- `_same()` --calls--> `parse_aliases()`  [INFERRED]
  app/views/memory.py → subagent/memory/store.py
- `load()` --calls--> `all_similarities()`  [INFERRED]
  app/views/memory.py → subagent/voice/voice.py
- `load()` --calls--> `voice_clips()`  [INFERRED]
  app/views/memory.py → subagent/voice/voice.py
- `load()` --indirect_call--> `episode_id()`  [INFERRED]
  app/views/review.py → subagent/workspace/episodes.py

## Import Cycles
- 2-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/__init__.py`
- 3-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/briefing_gen.py -> subagent/memory/__init__.py`
- 3-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/manager/__init__.py -> subagent/memory/__init__.py`
- 3-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/prefix.py -> subagent/memory/__init__.py`
- 4-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/briefing_gen.py -> subagent/memory/prefix.py -> subagent/memory/__init__.py`
- 4-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/manager/__init__.py -> subagent/memory/manager/apply.py -> subagent/memory/__init__.py`
- 4-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/manager/__init__.py -> subagent/memory/manager/episode.py -> subagent/memory/__init__.py`
- 5-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/manager/__init__.py -> subagent/memory/manager/updates.py -> subagent/memory/character_updates.py -> subagent/memory/__init__.py`

## Hyperedges (group relationships)
- **LLM prompts that feed the Memory Manager** — prompts_briefing_system, prompts_character_update_system, prompts_dreaming_system, prompts_bootstrap_system, prompts_story_compress_system [INFERRED 0.85]
- **Translate / evaluate / retry loop** — prompts_translator_system, prompts_evaluator_system, prompts_translator_system_retries_earlier_attempts, prompts_registers_co_trang_tien_hiep [INFERRED 0.85]

## Communities (137 total, 27 thin omitted)

### Community 0 - "test_app.py"
Cohesion: 0.17
Nodes (19): MainWindow, PinyinLine, gate(), qapp(), settle(), test_audit_screen_and_audit_mode(), test_bootstrap_learns_the_subtitle_style_as_a_job(), test_character_browser_lists_cards_and_assigns() (+11 more)

### Community 1 - "LLM Client & Costs"
Cohesion: 0.07
Nodes (33): LLMCallError, CostRecord, build_messages(), compute_cost(), _daily_quota(), _describe(), LLMClient, missing_prices() (+25 more)

### Community 2 - "App Package & Jobs"
Cohesion: 0.08
Nodes (7): agent_label(), error_message(), stage_label(), status_label(), ReviewData, RunPanel, fmt_ms()

### Community 3 - "CastLine"
Cohesion: 0.11
Nodes (16): apply_review_edits(), CastBoxEdit, CastDetection, CastLine, test_sample_is_stratified_reproducible_and_adds_disagreements(), FakeEngine, line(), test_reviewer_box_edits_and_talking_mark_teach() (+8 more)

### Community 4 - "Memory Screen"
Cohesion: 0.05
Nodes (10): EntryTable, _item(), MemoryView, load(), done(), PairDialog, text(), _same() (+2 more)

### Community 5 - "Band & Cast Panel Views"
Cohesion: 0.06
Nodes (9): BandView, CastCanvas, CastPanel, ScaledImage, to_pixmap(), done(), failed(), test_cast_panel_shows_boxes_and_records_corrections() (+1 more)

### Community 6 - "partial.py"
Cohesion: 0.09
Nodes (29): ReviewIncompleteError, PartialSuggestion, partial_review(), PartialResult, _session_bank(), _sprites(), suggest(), draft_path() (+21 more)

### Community 7 - "Memory Manager Rows"
Cohesion: 0.15
Nodes (23): HistoryMixin, merge_proposals(), replaced_term(), reviewed_glossary(), CommitInfo, Conflict, describe_update(), dumps_aliases() (+15 more)

### Community 8 - "Audit Sampling"
Cohesion: 0.09
Nodes (29): auditable(), auditable_lines(), AuditReport, build_report(), disagreements(), draw_sample(), EpisodeAudit, gold_speakers() (+21 more)

### Community 9 - "test_feedback_loop.py"
Cohesion: 0.13
Nodes (22): EditRecord, user_json(), _rubric(), evaluator(), test_a_passing_line_keeps_the_evaluators_suggestion_for_the_reviewer(), test_retry_sends_history_and_suggestion(), vi_for(), test_reviewer_corrections_reach_both_prompts() (+14 more)

### Community 10 - "Memory Manager Tests"
Cohesion: 0.14
Nodes (25): MemoryManager, seed_memory(), test_learning_an_episode_again_replaces_what_it_learned(), P(), test_a_new_glossary_term_takes_the_form_the_reviewer_wrote(), test_conflicts_need_more_evidence(), test_deleted_lines_are_not_memory_evidence(), test_episode_update_applies_mines_briefs_and_commits() (+17 more)

### Community 12 - "New Voices & Characters"
Cohesion: 0.15
Nodes (19): NewVoice, draft_voice_ids(), episode_character_ids(), review_voice_ids(), save_new_voices(), Candidate, test_lines_may_use_the_episode_new_voices(), _finish() (+11 more)

### Community 13 - "register_episode"
Cohesion: 0.21
Nodes (13): Progress, register_episode(), test_pipeline_reports_script_reviewer_spending(), test_turning_it_on_again_runs_the_stages(), _pipeline(), test_auto_mode_end_to_end_and_output_conflict(), test_batch_cost_limit(), test_batch_rerun_includes_finished_episodes() (+5 more)

### Community 14 - "Benchmark Suite"
Cohesion: 0.10
Nodes (37): gold_lines(), align(), _approved(), _auto_pattern(), characters_at(), _decisions(), _events(), Gold (+29 more)

### Community 15 - "Config Schema"
Cohesion: 0.10
Nodes (26): AudioConfig, AuditConfig, Band, BaselineConfig, BenchConfig, BudgetConfig, CleanupConfig, EpisodesConfig (+18 more)

### Community 16 - "Output Delivery & ASS"
Cohesion: 0.18
Nodes (10): build_ass(), _color(), Layout, _style(), _line(), test_ass_has_two_events_per_line_with_same_timing(), test_deleted_lines_are_not_rendered(), test_font_sizes_scale_with_height() (+2 more)

### Community 17 - "Series Management"
Cohesion: 0.17
Nodes (13): cmd_series(), running_jobs(), list_series(), add(), _blocks(), check_slug(), migrate(), _refuse_while_jobs_run() (+5 more)

### Community 18 - "Cast Engine"
Cohesion: 0.09
Nodes (19): CastEngine, crop(), _ffmpeg(), frame_path(), get_engine(), keep_boxes(), line_motion(), _mark_talking() (+11 more)

### Community 19 - "Video Preview (mpv)"
Cohesion: 0.08
Nodes (5): fmt_time(), load_mpv(), PreviewWidget, TimelineSlider, test_preview_transport_controls()

### Community 20 - "cast/learning.py"
Cohesion: 0.18
Nodes (9): group_unknowns(), _apply_labels(), _check_talkers(), learn_sprites(), _name_unknowns(), plan(), _Plan, SpriteLearnResult (+1 more)

### Community 21 - "Memory Store"
Cohesion: 0.08
Nodes (11): _pairs_block(), _present_block(), glossary_zh_block(), new_voices_block(), MemoryStore, SpriteExemplar, _clip(), _fake_embed() (+3 more)

### Community 22 - "test_translate_review.py"
Cohesion: 0.09
Nodes (24): check(), SpeakerCandidates, visible_chars(), PronounPair, rule_checks(), RuleContext, RuleFailure, _word_tokenizer() (+16 more)

### Community 23 - "Character Cards"
Cohesion: 0.11
Nodes (21): card_info(), card_media(), CharacterCard, confirmed_box(), _cut_clip(), _cut_picture(), _episode_ids(), _frame() (+13 more)

### Community 24 - "Services"
Cohesion: 0.08
Nodes (3): EpisodeRow, script_note(), Services

### Community 25 - "OCR Engine & Geometry"
Cohesion: 0.08
Nodes (19): onnx_use_cuda(), ModelUnavailableError, OcrBox, center_in_band(), create_engine(), crop_path(), _engine_key(), filter_boxes() (+11 more)

### Community 26 - "Subtitle Style"
Cohesion: 0.12
Nodes (18): calibrate(), grow_line(), labels_near(), load_style(), propose_regions(), _region_features(), save_style(), segment_mask() (+10 more)

### Community 27 - "Pipeline Runner & Locks"
Cohesion: 0.12
Nodes (4): _learn(), job_lock(), _episode_log, Pipeline

### Community 28 - "CLI Episodes"
Cohesion: 0.09
Nodes (34): freeze_finished(), _ask(), build_pipeline(), _interactive(), _output_exists(), _resolve_on_exists(), add_add(), add_batch() (+26 more)

### Community 29 - "Episodes Screen"
Cohesion: 0.11
Nodes (5): choose_batch_on_exists(), choose_on_exists(), job_busy(), EpisodesView, confirm()

### Community 30 - "Memory Proposals Apply"
Cohesion: 0.21
Nodes (4): MemoryProposal, now_iso(), ApplyMixin, ApplyResult

### Community 31 - "Stage Table & State"
Cohesion: 0.12
Nodes (10): StageState, BatchItem, Runner, _lazy(), review_outputs(), run_stage(), _source_key(), StageDef (+2 more)

### Community 32 - "Voice Learning & Evidence"
Cohesion: 0.11
Nodes (22): trusted_speakers(), torch_device(), is_auto_episode(), trusted_auto_lines(), usable_line(), _voices(), Config, Paths (+14 more)

### Community 33 - "Media (ffmpeg) Infra"
Cohesion: 0.16
Nodes (17): available_encoders(), extract_clip(), extract_frame(), git(), has_video_stream(), imread(), imwrite_png(), iter_gray_frames() (+9 more)

### Community 34 - "Audit & Dreaming Screens"
Cohesion: 0.10
Nodes (5): AuditView, done(), DreamingView, _summary(), show_error()

### Community 35 - "Settings & Run Panel"
Cohesion: 0.11
Nodes (5): label(), reset_all(), save(), sequence(), SettingsView

### Community 36 - "Script Review & OCR Fix"
Cohesion: 0.11
Nodes (18): ScriptDecision, load_prompt(), LineDecision, build_draft(), ScriptReviewConfig, examples_block(), find_repeats(), han_count() (+10 more)

### Community 37 - "Frozen Baseline"
Cohesion: 0.16
Nodes (15): baseline_dir(), complete(), freeze(), freeze_episode(), _git_head(), _manifest(), memory_at_run(), _save_manifest() (+7 more)

### Community 38 - "Bootstrap Seed"
Cohesion: 0.11
Nodes (19): approve_seed(), _episode1_lines(), generate_seed(), load_seed(), name_pinyin(), save_clip(), save_seed(), seed_path() (+11 more)

### Community 39 - "YAML Comment-Preserving Edit"
Cohesion: 0.14
Nodes (17): file_comment(), _block_end(), delete_key(), _dump(), _find(), _get(), _is_child(), _path() (+9 more)

### Community 41 - "Speaker Benchmark"
Cohesion: 0.17
Nodes (11): stratified(), wilson(), _acc(), benchmark_episodes(), BenchmarkResult, _copy_reviewer_context(), _drop_heavy_files(), EpisodeScore (+3 more)

### Community 42 - "OCR Benchmark"
Cohesion: 0.15
Nodes (11): _covered(), EpisodeOcrScore, _existing_events(), ocr_episodes(), OcrBenchResult, _overlap(), remap_ids(), remap_key() (+3 more)

### Community 43 - "Episode Registry"
Cohesion: 0.11
Nodes (20): cmd_add(), EpisodeNotFoundError, SourceMissingError, Episode, AddCandidate, derived_status(), detect_number(), episode_id() (+12 more)

### Community 44 - "read_jsonl"
Cohesion: 0.13
Nodes (32): run(), ChangeRecord, read_jsonl(), write_jsonl(), run(), run(), run(), counts_text() (+24 more)

### Community 45 - "Ingest & Change Detection"
Cohesion: 0.14
Nodes (21): binarize(), calibrate(), Change, change_fraction(), detect_changes(), draw_band(), fuse(), has_subtitle() (+13 more)

### Community 46 - "Character Browser"
Cohesion: 0.13
Nodes (5): CharacterBrowser, CharacterStrip, describe(), _pixmap(), ClipPlayer

### Community 47 - "Kernel Errors"
Cohesion: 0.14
Nodes (12): BudgetExceeded, EpisodeLockedError, JobRunningError, LLMOutputError, MemoryLockedError, StageError, SubagentError, mode_prompt() (+4 more)

### Community 48 - "Translate Stage"
Cohesion: 0.10
Nodes (21): Evaluation, LineTranslation, Window, judge(), llm_rubric(), rubric_payload(), RubricLine, RubricResponse (+13 more)

### Community 49 - "Dreaming"
Cohesion: 0.12
Nodes (22): contains_term(), found_terms(), word_count(), apply_dream(), approved_lines(), describe(), done_episodes(), dream() (+14 more)

### Community 50 - "Character Updates"
Cohesion: 0.14
Nodes (10): _alias_zh(), CharacterChange, CharacterUpdateResponse, check(), _clip(), _has_word(), _introduces(), _positions() (+2 more)

### Community 51 - "Voice Candidates"
Cohesion: 0.12
Nodes (5): load_line_voices(), CandidatesMixin, _Run, speaker_lines(), episode_number()

### Community 52 - "New Series Dialog"
Cohesion: 0.11
Nodes (5): NewSeriesDialog, StyleDialog, test_new_series_dialog_asks_for_the_default_pronoun_pair(), test_new_series_dialog_creates_a_translation_style(), test_new_series_work_folder_can_be_chosen()

### Community 53 - "Review On-Screen Cast"
Cohesion: 0.10
Nodes (5): flag_label(), show(), done(), flag_group(), needs_attention()

### Community 54 - "Voice Match"
Cohesion: 0.11
Nodes (18): update_voices(), new_voice_id(), VoiceConfig, all_similarities(), classify(), compute_centroids(), Embedder, find_new_voices() (+10 more)

### Community 55 - "Bench Run Sandbox"
Cohesion: 0.16
Nodes (13): checkout_memory(), _drop_heavy(), _frozen_inputs(), _install_review(), _null(), _rerun_episode(), run(), _run_info() (+5 more)

### Community 56 - "Translation Registers"
Cohesion: 0.21
Nodes (11): check_id(), list_registers(), load_register(), _parse(), Register, register_dir(), save_register(), split_terms() (+3 more)

### Community 57 - "Series-1 Voice Config"
Cohesion: 0.08
Nodes (24): voice, accept_score, confusable_similarity, learn_auto_allowed_flags, learn_auto_max_drop, learn_auto_min_margin, learn_auto_min_score, learn_auto_min_test_lines (+16 more)

### Community 60 - "Series-1 Cast Config"
Cohesion: 0.09
Nodes (23): cast, add_similarity, detector_model, embed_model, enabled, frame_width, learn, match_margin (+15 more)

### Community 61 - "test_parser_stages.py"
Cohesion: 0.09
Nodes (25): OcrReading, edit_distance(), normalize_zh(), relatedness(), absorb_fragments(), build_events(), flag_non_dialogue(), frames_on_screen() (+17 more)

### Community 62 - "Video Render"
Cohesion: 0.18
Nodes (13): _ass_text(), build_mask_filter(), check_fonts(), choose_encoder(), encoder_args(), ffmpeg_args(), font_files(), preview_ass() (+5 more)

### Community 63 - "Architecture Guard Test"
Cohesion: 0.17
Nodes (8): _breaches(), _imports(), _module_of(), _submodules(), test_every_package_is_a_known_module_with_a_public_api(), test_modules_import_each_other_only_through_their_api_and_downwards(), test_the_app_reaches_the_core_only_through_its_services(), test_the_core_never_imports_the_app_or_qt()

### Community 64 - "pytest"
Cohesion: 0.12
Nodes (22): ConfigError, prompt_hash(), active_series(), find_root(), load_config(), _load_env(), merge_sections(), parse_config() (+14 more)

### Community 66 - "Pinned Requirements"
Cohesion: 0.10
Nodes (20): jieba 0.42.1, numpy 2.5.3, onnxruntime-gpu 1.30.0, openai 3.22.1, opencv-python-headless 5.0.0.93, pillow 12.3.0, pydantic 2.13.5, pypinyin 0.55.0 (+12 more)

### Community 67 - "Briefings & Style Rules"
Cohesion: 0.15
Nodes (18): BriefingResponse, compress_story(), generate_briefing(), script_text(), StoryResponse, briefings_dir(), cap_style_rules(), IndexEntry (+10 more)

### Community 68 - "Review Character Editor"
Cohesion: 0.08
Nodes (9): character_proposals(), NewCharacterDialog, done(), save(), load(), done(), done(), failed() (+1 more)

### Community 69 - "Top-level Config Keys"
Cohesion: 0.10
Nodes (19): budget, max_cost_per_episode, cleanup, auto, device, episodes, number_patterns, video_extensions (+11 more)

### Community 70 - "kernel/__init__.py"
Cohesion: 0.09
Nodes (14): append_jsonl(), _atomic_write(), atomic_write_bytes(), atomic_write_json(), atomic_write_text(), chunked(), FileLock, hash_path() (+6 more)

### Community 71 - "Settings Schema Introspection"
Cohesion: 0.13
Nodes (10): add(), _code_notes(), fields(), walk(), FieldSpec, known_sets(), target(), _unwrap() (+2 more)

### Community 72 - "delivery.py"
Cohesion: 0.14
Nodes (14): OutputExistsError, OutputFolderError, cleanup(), deliver(), keep_both_path(), output_folder(), output_name(), resolve_conflict() (+6 more)

### Community 73 - "conftest.py"
Cohesion: 0.12
Nodes (16): FakeClient, FakeCompletions, make_llm(), _response(), _setup(), test_a_different_suggestion_for_the_same_term_still_comes_through(), gloss(), test_auto_apply_does_not_count_as_rejection() (+8 more)

### Community 74 - "Memory Banks Writing"
Cohesion: 0.14
Nodes (6): _add_exemplars(), BanksMixin, _drop_exemplar(), _keep_best(), _record_votes(), _undo_episode()

### Community 75 - "LLM Provider Config"
Cohesion: 0.11
Nodes (18): api_key_env, base_url, model, llm, max_retries, max_retry_wait_s, providers, temperature (+10 more)

### Community 76 - "OCR Preprocess Crop"
Cohesion: 0.12
Nodes (19): load_key(), _norm(), score_episode(), crop_view(), prepare(), subtitle_mask(), to_band_coords(), _band() (+11 more)

### Community 77 - "Pinyin Engine"
Cohesion: 0.12
Nodes (16): Character, GlossaryEntry, LogEntry, VoiceEntry, heteronyms(), PinyinEngine, PolyphoneChoice, PolyphoneResponse (+8 more)

### Community 78 - "Voice Learning Tests"
Cohesion: 0.21
Nodes (13): learn_voices(), LearnResult, reviewed_clips(), _auto_episode(), _episode(), _fake_embed(), test_auto_lines_pass_only_when_every_signal_agrees(), test_auto_lines_that_hurt_accuracy_are_not_learned() (+5 more)

### Community 79 - "Render Config"
Cohesion: 0.12
Nodes (17): render, avg_char_width, blur_radius, encoder, font_dir, font_name, line_spacing, mask (+9 more)

### Community 80 - "Text Utilities"
Cohesion: 0.31
Nodes (5): balanced_wrap(), nfc(), split_explicit_lines(), wrap_words(), wrap_lines()

### Community 81 - "load_state"
Cohesion: 0.25
Nodes (9): EpisodeState, load_state(), save_state(), state_path(), _lines(), test_auto_mode_learns_only_from_trusted_lines(), test_backfill_runs_cast_where_missing_then_learns(), fake_cast() (+1 more)

### Community 82 - "Memory & Translation Prompts"
Cohesion: 0.19
Nodes (8): Style rules, Cổ trang / tiên hiệp register (Hán-Việt terms), identify / default_pair template toggle, Memory proposals (glossary / pronoun_pair / character), Pronoun matrix, Retries with earlier_attempts and evaluator_suggestion, Reviewer corrections, Speaker rules per voice status (fixed/confusable/disputed/new_voice/unknown/too_short)

### Community 83 - "SubtitleEvent"
Cohesion: 0.14
Nodes (14): SubtitleEvent, keep_cjk(), ocr_fix_prefix(), apply_fixes(), batch_payload(), OcrFixChange, OcrFixResponse, max_chars_for() (+6 more)

### Community 86 - "subagent/__main__.py"
Cohesion: 0.19
Nodes (7): build_parser(), main(), _setup_logging(), test_cli_errors_are_json_with_codes(), test_cli_status_and_add(), test_new_series_asks_how_pronouns_are_decided(), test_cli_series_commands()

### Community 87 - "Series-1 Band Config"
Cohesion: 0.13
Nodes (15): bottom, left, right, top, video, band_frames, change_threshold, empty_text_ratio (+7 more)

### Community 88 - "test_character_lifecycle.py"
Cohesion: 0.19
Nodes (19): build_bank(), CharacterFate, characters_block(), evaluator_prefix(), glossary_block(), pronoun_block(), story_block(), style_block() (+11 more)

### Community 89 - "ReviewedLine"
Cohesion: 0.10
Nodes (16): ReviewedLine, present_ids(), propose(), _script(), candidate_looks(), candidate_voice(), check_return(), ReturnCheck (+8 more)

### Community 90 - "Job Runner"
Cohesion: 0.20
Nodes (3): JobRunner, test_run_panel_has_a_script_review_step(), __init__()

### Community 91 - "LineHistory"
Cohesion: 0.14
Nodes (9): line_matches(), LineFilter, LineHistory, _Clock, _line(), test_line_filter(), test_steps_are_per_line_and_copies(), test_typing_in_one_field_is_one_undo_step() (+1 more)

### Community 93 - "Prices Editor"
Cohesion: 0.16
Nodes (3): _num_text(), PricesEditor, ProvidersEditor

### Community 95 - "core.py"
Cohesion: 0.19
Nodes (5): frame_time_ms(), load_frame(), frame_embedder(), embed(), job_lock_path()

### Community 98 - "Price Table Keys"
Cohesion: 0.15
Nodes (13): input, input_cached, output, input, input_cached, output, input, input_cached (+5 more)

### Community 99 - "Memory Config Keys"
Cohesion: 0.15
Nodes (13): memory, aliases_max, archive_after_absent, character_lifecycle, character_updates, correction_examples, description_max_chars, dream_max_lines (+5 more)

### Community 100 - "Series-1 series.yaml"
Cohesion: 0.15
Nodes (12): baseline, name, bench, baseline, non_dialogue, box_center_tolerance, box_height_tolerance, enabled (+4 more)

### Community 101 - "memory/__init__.py"
Cohesion: 0.10
Nodes (10): best_match(), candidates_for(), decide(), load_templates(), run(), frame_reader(), save_template(), load_new_voices() (+2 more)

### Community 102 - "Settings Field Controls"
Cohesion: 0.25
Nodes (3): _decimals(), Field, set_float()

### Community 103 - "Device Detection"
Cohesion: 0.31
Nodes (3): describe(), onnx_cuda_available(), torch_cuda_available()

### Community 105 - "Series-1 OCR Config"
Cohesion: 0.18
Nodes (11): ocr, fragment_max_samples, fragment_merge_similarity, mask_image, mask_scale, merge_max_edit_distance, min_confidence, preprocess (+3 more)

### Community 106 - "Series-1 Script Review Config"
Cohesion: 0.18
Nodes (11): script_review, enabled, example_limit, max_remove_share, memory_auto_remove_min, memory_max_han, remove_confidence, repeat_merge_gap_ms (+3 more)

### Community 107 - "App Entry Point"
Cohesion: 0.27
Nodes (4): choose_platform(), install_fonts(), install_translator(), main()

### Community 108 - "test_character_updates.py"
Cohesion: 0.29
Nodes (10): save_line_voices(), _line(), _llm(), _npc(), test_a_candidate_keeps_its_updates_when_promoted(), finish(), test_auto_mode_holds_updates_from_unchecked_lines(), test_check_keeps_only_what_the_lines_show() (+2 more)

### Community 109 - "test_new_voices.py"
Cohesion: 0.27
Nodes (8): is_auto_id(), is_unnamed(), _e(), _results(), test_auto_ids(), test_group_voices_keeps_alike_voices_together(), test_new_voice_needs_enough_lines_and_an_unfamiliar_voice(), _unit()

### Community 110 - "Drop Table"
Cohesion: 0.13
Nodes (3): AddDialog, DropTable, done()

### Community 111 - "Translate Config"
Cohesion: 0.22
Nodes (9): translate, max_cps, max_line_chars, max_lines_per_event, max_retries, picture_evidence, picture_veto, pronoun_terms (+1 more)

### Community 112 - "symmetric_span"
Cohesion: 0.25
Nodes (3): line_span(), symmetric_span(), test_symmetric_span_trims_the_far_side_beyond_half_a_line()

### Community 119 - "character_dialog.py"
Cohesion: 0.40
Nodes (3): validate(), is_han(), looks_like_noise()

### Community 120 - "Series-1 Cast"
Cohesion: 0.52
Nodes (7): series-1 cast.md, Bắc Tỵ, Cơ Bá Thường, Cơ Tử, Sở Lưu Cần, Sử Thượng Phi, Tiểu Lượng

### Community 122 - "Audit Config"
Cohesion: 0.33
Nodes (6): audit, ignore_flags, include_human, max_disagreements, min_per_stratum, sample_size

### Community 124 - "Sprite Config"
Cohesion: 0.40
Nodes (5): sprite, enabled, match_threshold, scales, trigger_conf_below

### Community 125 - "Series-1 Review Prompt"
Cohesion: 0.40
Nodes (5): series-1 script review prompt notes, Font draws 了 like digit 7, Show wording that looks like stray text (史 for 屎, 鸡道, 姬叔), Similar-looking misreadings (干, 参/善, 美), Stray screen text (楚, 姬, 史, 林, 绝密, 000)

### Community 128 - "Audio Config"
Cohesion: 0.50
Nodes (4): audio, min_event_ms, pad_ms, sample_rate

### Community 129 - "Output Config"
Cohesion: 0.50
Nodes (4): output, folder, name_suffix, on_exists

### Community 130 - "Review Config"
Cohesion: 0.50
Nodes (4): review, mode, noise_max_han, predelete_fragments

### Community 131 - "Windows Config"
Cohesion: 0.50
Nodes (4): windows, context_overlap, gap_ms, max_lines

## Knowledge Gaps
- **28 isolated node(s):** `subagent`, `Font draws 了 like digit 7`, `Show wording that looks like stray text (史 for 屎, 鸡道, 姬叔)`, `Similar-looking misreadings (干, 参/善, 美)`, `Stray screen text (楚, 姬, 史, 林, 绝密, 000)` (+23 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1016 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ReviewedLine` connect `ReviewedLine` to `test_app.py`, `App Package & Jobs`, `CastLine`, `partial.py`, `Memory Manager Rows`, `Audit Sampling`, `test_feedback_loop.py`, `Memory Manager Tests`, `New Voices & Characters`, `Benchmark Suite`, `Output Delivery & ASS`, `cast/learning.py`, `Memory Store`, `test_translate_review.py`, `Character Cards`, `Services`, `Stage Table & State`, `Voice Learning & Evidence`, `Script Review & OCR Fix`, `Review Screen Shell`, `OCR Benchmark`, `read_jsonl`, `Translate Stage`, `Dreaming`, `Character Updates`, `Voice Candidates`, `Review On-Screen Cast`, `Video Render`, `Briefings & Style Rules`, `kernel/__init__.py`, `conftest.py`, `OCR Preprocess Crop`, `Voice Learning Tests`, `load_state`, `Episode Memory Update`, `test_character_lifecycle.py`, `LineHistory`, `workspace/__init__.py`, `core.py`, `Audit Bar`, `Memory Aux Writes`, `test_character_updates.py`, `test_new_voices.py`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ReviewedLine` (e.g. with `_finish()` and `test_pipeline_records_what_the_reviewer_removed_and_kept()`) actually correct?**
  _`ReviewedLine` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `subagent`, `Font draws 了 like digit 7`, `Show wording that looks like stray text (史 for 屎, 鸡道, 姬叔)` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `LLM Client & Costs` be split into smaller, more focused modules?**
  _Cohesion score 0.06758832565284179 - nodes in this community are weakly interconnected._
- **Why does `SubagentError` connect `Kernel Errors` to `LLM Client & Costs`, `App Package & Jobs`, `CastLine`, `partial.py`, `Memory Manager Rows`, `Series Management`, `test_translate_review.py`, `OCR Engine & Geometry`, `CLI Episodes`, `Memory Proposals Apply`, `Stage Table & State`, `Media (ffmpeg) Infra`, `Bootstrap Seed`, `Episode Registry`, `Translate Stage`, `Voice Match`, `Bench Run Sandbox`, `Translation Registers`, `Video Render`, `pytest`, `kernel/__init__.py`, `delivery.py`, `subagent/__main__.py`, `Memory Aux Writes`, `App Entry Point`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Config` (e.g. with `fields()` and `value_at()`) actually correct?**
  _`Config` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `App Package & Jobs` be split into smaller, more focused modules?**
  _Cohesion score 0.07923497267759563 - nodes in this community are weakly interconnected._