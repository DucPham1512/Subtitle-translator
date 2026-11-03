# Graph Report - Subtitle-translator  (2026-11-03)

## Corpus Check
- 214 files · ~168,623 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .qm 2, .example 1)

## Summary
- 3286 nodes · 11301 edges · 133 communities (107 shown, 26 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 684 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `677513a1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_app.py
- LLM Client & Costs
- App Package & Jobs
- test_ocr_preprocess.py
- Memory Screen
- Band & Cast Panel Views
- partial.py
- Memory Manager Rows
- test_audit.py
- test_feedback_loop.py
- Memory Manager Tests
- Bootstrap Wizard View
- test_dream_rejections.py
- register_episode
- Benchmark Suite
- Config Schema
- render.py
- Series Management
- Cast Engine
- Video Preview (mpv)
- test_cast.py
- Memory Store
- CastLine
- test_character_card.py
- Services
- OCR Engine & Geometry
- Subtitle Style
- Pipeline Runner & Locks
- CLI Episodes
- Episodes Screen
- Memory Proposals Apply
- report.py
- Voice Learning & Evidence
- Media (ffmpeg) Infra
- Audit & Dreaming Screens
- Settings & Run Panel
- Script Review & OCR Fix
- Frozen Baseline
- Bootstrap Seed
- YAML Comment-Preserving Edit
- ReviewView
- Speaker Benchmark
- ocr_benchmark.py
- Episode
- read_jsonl
- Ingest & Change Detection
- Character Browser
- conftest.py
- memory/__init__.py
- Dreaming
- character_updates.py
- Voice Candidates
- New Series Dialog
- cast/learning.py
- Voice Match
- Bench Run Sandbox
- Translation Registers
- Series-1 Voice Config
- ._loaded
- load_state
- Series-1 Cast Config
- test_parser_stages.py
- Paths
- Architecture Guard Test
- pytest
- Frame Selector Widget
- Pinned Requirements
- Briefings & Style Rules
- Review Character Editor
- Top-level Config Keys
- util.py
- Settings Schema Introspection
- ._show_card
- SpeakerCandidates
- Memory Banks Writing
- LLM Provider Config
- test_pinyin_voice_windows.py
- pinyin_gen.py
- Voice Learning Tests
- Render Config
- kernel/__init__.py
- numpy
- Memory & Translation Prompts
- SubtitleEvent
- ._field
- Tag Editor Widget
- subagent/__main__.py
- Series-1 Band Config
- test_character_lifecycle.py
- Runner
- test_parser_stages.py
- LineHistory
- Flow Layout
- Prices Editor
- Band
- AuditBar
- Settings Form
- Price Table Keys
- Memory Config Keys
- Series-1 series.yaml
- DropTable
- symmetric_span
- Device Detection
- Memory Aux Writes
- Series-1 OCR Config
- Series-1 Script Review Config
- main
- test_new_voices.py
- Translate Config
- measure.py
- Background Workers
- Vietnamese UI Fill
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
- `check()` --calls--> `rule_checks()`  [INFERRED]
  app/views/review.py → subagent/translation/evaluate.py
- `check()` --indirect_call--> `rules()`  [INFERRED]
  app/views/review.py → tests/test_translate_review.py
- `next_npc_number()` --calls--> `is_auto_id()`  [INFERRED]
  app/views/review_state.py → subagent/memory/characters.py

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

## Communities (133 total, 26 thin omitted)

### Community 0 - "test_app.py"
Cohesion: 0.10
Nodes (47): MainWindow, validate(), LineTranslation, PinyinLine, write_jsonl(), partial_review(), suggest(), draft_path() (+39 more)

### Community 1 - "LLM Client & Costs"
Cohesion: 0.05
Nodes (41): BudgetExceeded, LLMCallError, LLMOutputError, CostRecord, build_messages(), compute_cost(), _daily_quota(), _describe() (+33 more)

### Community 2 - "App Package & Jobs"
Cohesion: 0.07
Nodes (7): agent_label(), error_message(), stage_label(), status_label(), ReviewData, RunPanel, fmt_ms()

### Community 3 - "test_ocr_preprocess.py"
Cohesion: 0.16
Nodes (14): _norm(), score_episode(), to_band_coords(), _band(), _box(), _event(), _gold(), test_answer_key_corrects_and_excludes_lines() (+6 more)

### Community 4 - "Memory Screen"
Cohesion: 0.05
Nodes (9): EntryTable, _item(), MemoryView, done(), PairDialog, text(), _same(), _update_text() (+1 more)

### Community 5 - "Band & Cast Panel Views"
Cohesion: 0.07
Nodes (6): BandView, CastCanvas, CastPanel, ScaledImage, to_pixmap(), test_greyscale_images_can_be_shown()

### Community 6 - "partial.py"
Cohesion: 0.10
Nodes (20): ReviewIncompleteError, EditRecord, ReviewedLine, apply_script_review(), build_draft(), compute_edits(), finish_review(), flag_group() (+12 more)

### Community 7 - "Memory Manager Rows"
Cohesion: 0.15
Nodes (23): trusted_auto_lines(), HistoryMixin, merge_proposals(), replaced_term(), reviewed_glossary(), CommitInfo, Conflict, describe_update() (+15 more)

### Community 8 - "test_audit.py"
Cohesion: 0.13
Nodes (23): AuditReport, disagreements(), draw_sample(), EpisodeAudit, load_marks(), load_sample(), missing_answers(), _pct() (+15 more)

### Community 9 - "test_feedback_loop.py"
Cohesion: 0.12
Nodes (31): read_jsonl(), reviewer_corrections(), run(), user_json(), _reading(), _rubric(), evaluator(), test_a_passing_line_keeps_the_evaluators_suggestion_for_the_reviewer() (+23 more)

### Community 10 - "Memory Manager Tests"
Cohesion: 0.12
Nodes (29): MemoryManager, seed_memory(), _line(), _llm(), _npc(), test_a_candidate_keeps_its_updates_when_promoted(), finish(), test_auto_mode_holds_updates_from_unchecked_lines() (+21 more)

### Community 12 - "test_dream_rejections.py"
Cohesion: 0.18
Nodes (11): apply_dream(), forget_rejections(), load_proposals(), load_rejections(), test_dreaming_proposals_and_apply(), _response(), _setup(), test_auto_apply_does_not_count_as_rejection() (+3 more)

### Community 13 - "register_episode"
Cohesion: 0.14
Nodes (15): freeze_finished(), register_episode(), _pipeline(), ingest(), test_auto_mode_end_to_end_and_output_conflict(), test_batch_cost_limit(), test_batch_rerun_includes_finished_episodes(), test_batch_runs_in_episode_order_skips_finished_and_stops_on_failure() (+7 more)

### Community 14 - "Benchmark Suite"
Cohesion: 0.11
Nodes (35): gold_lines(), align(), _approved(), _auto_pattern(), characters_at(), _decisions(), _events(), Gold (+27 more)

### Community 15 - "Config Schema"
Cohesion: 0.13
Nodes (25): AudioConfig, AuditConfig, BaselineConfig, BenchConfig, BudgetConfig, CastConfig, CleanupConfig, EpisodesConfig (+17 more)

### Community 16 - "render.py"
Cohesion: 0.06
Nodes (44): add_check(), cmd_check(), OutputExistsError, OutputFolderError, balanced_wrap(), split_explicit_lines(), wrap_words(), cleanup() (+36 more)

### Community 17 - "Series Management"
Cohesion: 0.19
Nodes (11): cmd_series(), JobRunningError, _blocks(), check_slug(), migrate(), _refuse_while_jobs_run(), registers(), rename() (+3 more)

### Community 18 - "Cast Engine"
Cohesion: 0.08
Nodes (21): CastEngine, crop(), _ffmpeg(), frame_path(), frame_time_ms(), get_engine(), keep_boxes(), line_motion() (+13 more)

### Community 19 - "Video Preview (mpv)"
Cohesion: 0.08
Nodes (5): fmt_time(), load_mpv(), PreviewWidget, TimelineSlider, test_preview_transport_controls()

### Community 20 - "test_cast.py"
Cohesion: 0.14
Nodes (18): apply_review_edits(), learn_sprites(), EpisodeState, save_state(), FakeEngine, _frame(), _lines(), test_auto_mode_learns_only_from_trusted_lines() (+10 more)

### Community 21 - "Memory Store"
Cohesion: 0.06
Nodes (21): _pairs_block(), _present_block(), glossary_usage(), glossary_zh_block(), new_voices_block(), Candidate, Character, GlossaryEntry (+13 more)

### Community 22 - "CastLine"
Cohesion: 0.12
Nodes (15): gold_boxes(), group_map(), mapping(), CastDetection, CastLine, picture_veto(), test_cast_panel_shows_boxes_and_records_corrections(), test_picture_veto_disputes_the_voice() (+7 more)

### Community 23 - "test_character_card.py"
Cohesion: 0.16
Nodes (11): confirmed_box(), shown_talking_box(), _cast(), _line(), _no_real_ffmpeg(), _setup(), test_bootstrap_material_and_a_pinned_sample_come_first(), clip() (+3 more)

### Community 24 - "Services"
Cohesion: 0.05
Nodes (6): JobRunner, EpisodeRow, script_note(), Services, test_run_panel_has_a_script_review_step(), __init__()

### Community 25 - "OCR Engine & Geometry"
Cohesion: 0.08
Nodes (24): onnx_use_cuda(), ModelUnavailableError, OcrBox, keep_cjk(), center_in_band(), create_engine(), crop_path(), crop_view() (+16 more)

### Community 26 - "Subtitle Style"
Cohesion: 0.11
Nodes (19): calibrate(), grow_line(), labels_near(), load_style(), propose_regions(), _region_features(), save_style(), segment_mask() (+11 more)

### Community 27 - "Pipeline Runner & Locks"
Cohesion: 0.14
Nodes (4): job_lock(), BatchItem, _episode_log, Pipeline

### Community 28 - "CLI Episodes"
Cohesion: 0.11
Nodes (21): add_add(), add_batch(), add_calibrate(), add_clean(), add_finish_review(), add_partial_review(), add_relink(), add_render() (+13 more)

### Community 29 - "Episodes Screen"
Cohesion: 0.10
Nodes (7): choose_batch_on_exists(), choose_on_exists(), job_busy(), AddDialog, EpisodesView, done(), confirm()

### Community 30 - "Memory Proposals Apply"
Cohesion: 0.10
Nodes (8): MemoryProposal, now_iso(), ApplyMixin, EpisodeMixin, _next_status(), ApplyResult, test_a_different_suggestion_for_the_same_term_still_comes_through(), gloss()

### Community 31 - "report.py"
Cohesion: 0.15
Nodes (7): counts_text(), _pct(), write_report(), _lazy(), review_outputs(), _source_key(), _style_key()

### Community 32 - "Voice Learning & Evidence"
Cohesion: 0.12
Nodes (20): is_auto_episode(), usable_line(), auto_clips(), auto_gate(), AutoGate, build_centroids(), Clip, embed_clips() (+12 more)

### Community 33 - "Media (ffmpeg) Infra"
Cohesion: 0.11
Nodes (24): best_match(), candidates_for(), decide(), load_templates(), run(), frame_reader(), save_template(), available_encoders() (+16 more)

### Community 34 - "Audit & Dreaming Screens"
Cohesion: 0.10
Nodes (5): AuditView, done(), DreamingView, _summary(), show_error()

### Community 35 - "Settings & Run Panel"
Cohesion: 0.09
Nodes (5): label(), reset_all(), save(), sequence(), SettingsView

### Community 36 - "Script Review & OCR Fix"
Cohesion: 0.11
Nodes (23): ScriptDecision, is_han(), LineDecision, ScriptReviewConfig, examples_block(), find_repeats(), han_count(), memory_removals() (+15 more)

### Community 37 - "Frozen Baseline"
Cohesion: 0.18
Nodes (14): baseline_dir(), complete(), freeze(), freeze_episode(), _git_head(), _manifest(), memory_at_run(), _save_manifest() (+6 more)

### Community 38 - "Bootstrap Seed"
Cohesion: 0.09
Nodes (25): load(), approve_seed(), _episode1_lines(), generate_seed(), load_seed(), name_pinyin(), save_clip(), save_seed() (+17 more)

### Community 39 - "YAML Comment-Preserving Edit"
Cohesion: 0.14
Nodes (17): file_comment(), _block_end(), delete_key(), _dump(), _find(), _get(), _is_child(), _path() (+9 more)

### Community 40 - "ReviewView"
Cohesion: 0.08
Nodes (5): flag_label(), ReviewView, check(), show(), done()

### Community 41 - "Speaker Benchmark"
Cohesion: 0.13
Nodes (15): auditable_lines(), gold_speakers(), is_flagged(), stratified(), wilson(), _acc(), benchmark_episodes(), BenchmarkResult (+7 more)

### Community 42 - "ocr_benchmark.py"
Cohesion: 0.13
Nodes (12): _covered(), EpisodeOcrScore, _existing_events(), load_key(), OcrBenchResult, _overlap(), remap_ids(), remap_key() (+4 more)

### Community 43 - "Episode"
Cohesion: 0.10
Nodes (12): Episode, AddCandidate, derived_status(), fingerprint(), add(), scan_paths(), test_add_register_duplicates_and_numbers(), test_fingerprint_reads_head_and_tail() (+4 more)

### Community 44 - "read_jsonl"
Cohesion: 0.14
Nodes (17): _learn(), run(), calibrate(), _review_run(), run(), run(), EpisodeContext, make_episode() (+9 more)

### Community 45 - "Ingest & Change Detection"
Cohesion: 0.17
Nodes (19): binarize(), Change, change_fraction(), detect_changes(), draw_band(), fuse(), has_subtitle(), outlined_ratio() (+11 more)

### Community 46 - "Character Browser"
Cohesion: 0.12
Nodes (6): CharacterBrowser, CharacterStrip, describe(), _pixmap(), ClipPlayer, test_character_browser_lists_cards_and_assigns()

### Community 47 - "conftest.py"
Cohesion: 0.17
Nodes (18): ConfigError, main(), prompt_hash(), load_config(), parse_config(), ShowConfig, add(), test_new_series_asks_how_pronouns_are_decided() (+10 more)

### Community 48 - "memory/__init__.py"
Cohesion: 0.15
Nodes (12): _kept_evaluation(), Evaluation, _best(), context_row(), ProposalDraft, rank_attempt(), _same(), to_translation() (+4 more)

### Community 49 - "Dreaming"
Cohesion: 0.09
Nodes (31): load_prompt(), BriefingResponse, compress_story(), generate_briefing(), script_text(), StoryResponse, word_count(), approved_lines() (+23 more)

### Community 50 - "character_updates.py"
Cohesion: 0.12
Nodes (14): contains_term(), _alias_zh(), CharacterChange, CharacterUpdateResponse, check(), _clip(), _has_word(), _introduces() (+6 more)

### Community 51 - "Voice Candidates"
Cohesion: 0.12
Nodes (5): load_line_voices(), CandidatesMixin, _Run, speaker_lines(), episode_number()

### Community 52 - "New Series Dialog"
Cohesion: 0.13
Nodes (5): NewSeriesDialog, StyleDialog, test_new_series_dialog_asks_for_the_default_pronoun_pair(), test_new_series_dialog_creates_a_translation_style(), test_new_series_work_folder_can_be_chosen()

### Community 53 - "cast/learning.py"
Cohesion: 0.18
Nodes (8): group_unknowns(), _apply_labels(), _check_talkers(), _name_unknowns(), plan(), _Plan, SpriteLearnResult, trusted_speakers()

### Community 54 - "Voice Match"
Cohesion: 0.14
Nodes (15): new_voice_id(), PartialResult, _session_bank(), _sprites(), VoiceConfig, classify(), Embedder, find_new_voices() (+7 more)

### Community 55 - "Bench Run Sandbox"
Cohesion: 0.16
Nodes (13): checkout_memory(), _drop_heavy(), _frozen_inputs(), _install_review(), _null(), _rerun_episode(), run(), _run_info() (+5 more)

### Community 56 - "Translation Registers"
Cohesion: 0.09
Nodes (23): EpisodeLockedError, EpisodeNotFoundError, MemoryLockedError, SourceMissingError, StageError, SubagentError, check_id(), list_registers() (+15 more)

### Community 57 - "Series-1 Voice Config"
Cohesion: 0.08
Nodes (24): voice, accept_score, confusable_similarity, learn_auto_allowed_flags, learn_auto_max_drop, learn_auto_min_margin, learn_auto_min_score, learn_auto_min_test_lines (+16 more)

### Community 59 - "load_state"
Cohesion: 0.31
Nodes (5): auditable(), build_report(), ocr_episodes(), job_lock_path(), load_state()

### Community 60 - "Series-1 Cast Config"
Cohesion: 0.09
Nodes (23): cast, add_similarity, detector_model, embed_model, enabled, frame_width, learn, match_margin (+15 more)

### Community 61 - "test_parser_stages.py"
Cohesion: 0.12
Nodes (16): edit_distance(), normalize_zh(), relatedness(), absorb_fragments(), build_events(), flag_non_dialogue(), frames_on_screen(), _Group (+8 more)

### Community 62 - "Paths"
Cohesion: 0.16
Nodes (11): card_info(), card_media(), CharacterCard, _cut_clip(), _cut_picture(), _episode_ids(), _frame(), pin_card() (+3 more)

### Community 63 - "Architecture Guard Test"
Cohesion: 0.17
Nodes (8): _breaches(), _imports(), _module_of(), _submodules(), test_every_package_is_a_known_module_with_a_public_api(), test_modules_import_each_other_only_through_their_api_and_downwards(), test_the_app_reaches_the_core_only_through_its_services(), test_the_core_never_imports_the_app_or_qt()

### Community 64 - "pytest"
Cohesion: 0.15
Nodes (11): active_series(), find_root(), list_series(), merge_sections(), _read_yaml(), save_config_text(), save_settings(), series_data() (+3 more)

### Community 66 - "Pinned Requirements"
Cohesion: 0.10
Nodes (20): jieba 0.42.1, numpy 2.5.3, onnxruntime-gpu 1.30.0, openai 3.22.1, opencv-python-headless 5.0.0.93, pillow 12.3.0, pydantic 2.13.5, pypinyin 0.55.0 (+12 more)

### Community 67 - "Briefings & Style Rules"
Cohesion: 0.21
Nodes (12): briefings_dir(), cap_style_rules(), IndexEntry, list_episode_briefings(), _read(), read_index(), read_story(), read_style_rules() (+4 more)

### Community 68 - "Review Character Editor"
Cohesion: 0.12
Nodes (6): character_proposals(), NewCharacterDialog, done(), save(), load(), episode_id()

### Community 69 - "Top-level Config Keys"
Cohesion: 0.10
Nodes (19): budget, max_cost_per_episode, cleanup, auto, device, episodes, number_patterns, video_extensions (+11 more)

### Community 70 - "util.py"
Cohesion: 0.16
Nodes (8): running_jobs(), _atomic_write(), atomic_write_json(), atomic_write_text(), lock_holder(), pid_alive(), _replace_with_retry(), sha256_bytes()

### Community 71 - "Settings Schema Introspection"
Cohesion: 0.10
Nodes (9): _code_notes(), fields(), walk(), known_sets(), target(), _unwrap(), value_at(), with_known_sets() (+1 more)

### Community 72 - "._show_card"
Cohesion: 0.15
Nodes (6): done(), failed(), done(), done(), failed(), done()

### Community 73 - "SpeakerCandidates"
Cohesion: 0.10
Nodes (18): SpeakerCandidates, visible_chars(), judge(), llm_rubric(), max_chars_for(), rubric_payload(), RubricLine, RubricResponse (+10 more)

### Community 74 - "Memory Banks Writing"
Cohesion: 0.14
Nodes (6): _add_exemplars(), BanksMixin, _drop_exemplar(), _keep_best(), _record_votes(), _undo_episode()

### Community 75 - "LLM Provider Config"
Cohesion: 0.11
Nodes (18): api_key_env, base_url, model, llm, max_retries, max_retry_wait_s, providers, temperature (+10 more)

### Community 76 - "test_pinyin_voice_windows.py"
Cohesion: 0.22
Nodes (9): build_windows(), run(), write_silence(), _engine(), test_pinyin_uses_glossary_and_attaches_punctuation(), test_pinyin_words_are_joined_within_and_spaced_between(), test_polyphones_outside_known_phrases_are_reported(), test_render_applies_overrides() (+1 more)

### Community 77 - "pinyin_gen.py"
Cohesion: 0.17
Nodes (8): nfc(), heteronyms(), PinyinEngine, PolyphoneChoice, PolyphoneResponse, resolve_polyphones(), run(), Token

### Community 78 - "Voice Learning Tests"
Cohesion: 0.28
Nodes (10): _auto_episode(), _episode(), _fake_embed(), test_auto_lines_pass_only_when_every_signal_agrees(), test_auto_lines_that_hurt_accuracy_are_not_learned(), test_auto_lines_that_keep_accuracy_are_learned(), test_auto_lines_wait_until_there_is_enough_to_measure(), test_learn_writes_bank_and_evaluate_reports_accuracy() (+2 more)

### Community 79 - "Render Config"
Cohesion: 0.12
Nodes (17): render, avg_char_width, blur_radius, encoder, font_dir, font_name, line_spacing, mask (+9 more)

### Community 80 - "kernel/__init__.py"
Cohesion: 0.18
Nodes (8): AuditSample, CastBoxEdit, ChangeRecord, OcrReading, PartialSuggestion, StageState, VideoInfo, Window

### Community 81 - "numpy"
Cohesion: 0.21
Nodes (5): candidate_looks(), candidate_voice(), check_return(), ReturnCheck, _unit()

### Community 82 - "Memory & Translation Prompts"
Cohesion: 0.19
Nodes (8): Style rules, Cổ trang / tiên hiệp register (Hán-Việt terms), identify / default_pair template toggle, Memory proposals (glossary / pronoun_pair / character), Pronoun matrix, Retries with earlier_attempts and evaluator_suggestion, Reviewer corrections, Speaker rules per voice status (fixed/confusable/disputed/new_voice/unknown/too_short)

### Community 83 - "SubtitleEvent"
Cohesion: 0.19
Nodes (10): SubtitleEvent, chunked(), apply_fixes(), batch_payload(), OcrFixChange, OcrFixResponse, run(), test_answer_key_moves_to_renumbered_events_by_time() (+2 more)

### Community 84 - "._field"
Cohesion: 0.18
Nodes (5): _decimals(), Field, set_float(), add(), FieldSpec

### Community 87 - "Series-1 Band Config"
Cohesion: 0.13
Nodes (15): bottom, left, right, top, video, band_frames, change_threshold, empty_text_ratio (+7 more)

### Community 88 - "test_character_lifecycle.py"
Cohesion: 0.32
Nodes (12): build_bank(), CharacterFate, _lines(), _setup(), _status(), test_consecutive_episodes_keep_a_character(), test_first_run_counts_earlier_episodes(), test_generic_characters_are_never_matched_or_learned() (+4 more)

### Community 89 - "Runner"
Cohesion: 0.19
Nodes (3): FileLock, Runner, StageDef

### Community 90 - "test_parser_stages.py"
Cohesion: 0.26
Nodes (9): _band(), _box(), _r(), test_detect_changes_emits_text_and_empty(), test_events_merge_similar_readings_and_pick_the_most_frequent(), test_reading_detects_multiple_rows_and_low_confidence(), test_reading_joins_boxes_left_to_right_and_filters(), test_single_misread_between_matching_readings_is_absorbed() (+1 more)

### Community 91 - "LineHistory"
Cohesion: 0.10
Nodes (16): all_correct_mark(), line_matches(), LineFilter, LineHistory, marked_count(), next_npc_number(), next_unmarked(), _Clock (+8 more)

### Community 93 - "Prices Editor"
Cohesion: 0.16
Nodes (3): _num_text(), PricesEditor, ProvidersEditor

### Community 98 - "Price Table Keys"
Cohesion: 0.15
Nodes (13): input, input_cached, output, input, input_cached, output, input, input_cached (+5 more)

### Community 99 - "Memory Config Keys"
Cohesion: 0.15
Nodes (13): memory, aliases_max, archive_after_absent, character_lifecycle, character_updates, correction_examples, description_max_chars, dream_max_lines (+5 more)

### Community 100 - "Series-1 series.yaml"
Cohesion: 0.15
Nodes (12): baseline, name, bench, baseline, non_dialogue, box_center_tolerance, box_height_tolerance, enabled (+4 more)

### Community 102 - "symmetric_span"
Cohesion: 0.25
Nodes (3): line_span(), symmetric_span(), test_symmetric_span_trims_the_far_side_beyond_half_a_line()

### Community 103 - "Device Detection"
Cohesion: 0.18
Nodes (5): describe(), onnx_cuda_available(), torch_cuda_available(), torch_device(), Config

### Community 105 - "Series-1 OCR Config"
Cohesion: 0.18
Nodes (11): ocr, fragment_max_samples, fragment_merge_similarity, mask_image, mask_scale, merge_max_edit_distance, min_confidence, preprocess (+3 more)

### Community 106 - "Series-1 Script Review Config"
Cohesion: 0.18
Nodes (11): script_review, enabled, example_limit, max_remove_share, memory_auto_remove_min, memory_max_han, remove_confidence, repeat_merge_gap_ms (+3 more)

### Community 108 - "main"
Cohesion: 0.25
Nodes (4): choose_platform(), install_fonts(), install_translator(), main()

### Community 109 - "test_new_voices.py"
Cohesion: 0.10
Nodes (31): NewVoice, draft_voice_ids(), episode_character_ids(), is_auto_id(), is_unnamed(), load_new_voices(), review_voice_ids(), save_new_voices() (+23 more)

### Community 111 - "Translate Config"
Cohesion: 0.22
Nodes (9): translate, max_cps, max_line_chars, max_lines_per_event, max_retries, picture_evidence, picture_veto, pronoun_terms (+1 more)

### Community 112 - "measure.py"
Cohesion: 0.16
Nodes (14): _ask(), build_pipeline(), _interactive(), _output_exists(), _resolve_on_exists(), cmd_batch(), add_audit(), add_dream() (+6 more)

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
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1019 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ReviewedLine` connect `partial.py` to `test_app.py`, `App Package & Jobs`, `test_ocr_preprocess.py`, `Memory Manager Rows`, `test_audit.py`, `test_feedback_loop.py`, `Memory Manager Tests`, `test_dream_rejections.py`, `Benchmark Suite`, `render.py`, `test_cast.py`, `Memory Store`, `CastLine`, `test_character_card.py`, `Services`, `Memory Proposals Apply`, `report.py`, `Voice Learning & Evidence`, `Script Review & OCR Fix`, `ReviewView`, `Speaker Benchmark`, `ocr_benchmark.py`, `read_jsonl`, `Dreaming`, `character_updates.py`, `Voice Candidates`, `cast/learning.py`, `Voice Match`, `._loaded`, `Paths`, `Briefings & Style Rules`, `Voice Learning Tests`, `kernel/__init__.py`, `numpy`, `test_character_lifecycle.py`, `LineHistory`, `Memory Aux Writes`, `test_new_voices.py`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ReviewedLine` (e.g. with `_finish()` and `test_pipeline_records_what_the_reviewer_removed_and_kept()`) actually correct?**
  _`ReviewedLine` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `subagent`, `Font draws 了 like digit 7`, `Show wording that looks like stray text (史 for 屎, 鸡道, 姬叔)` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09663087745279526 - nodes in this community are weakly interconnected._
- **Why does `ReviewView` connect `ReviewView` to `test_app.py`, `AuditBar`, `App Package & Jobs`, `Settings & Run Panel`, `Review Character Editor`, `Band & Cast Panel Views`, `Memory Screen`, `._show_card`, `LineHistory`, `Character Browser`, `Video Preview (mpv)`, `._loaded`, `.open_episode`, `AuditBar`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Config` (e.g. with `fields()` and `value_at()`) actually correct?**
  _`Config` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `LLM Client & Costs` be split into smaller, more focused modules?**
  _Cohesion score 0.05346164127238706 - nodes in this community are weakly interconnected._