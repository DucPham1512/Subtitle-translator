# Graph Report - Subtitle-translator  (2026-11-03)

## Corpus Check
- 214 files · ~169,287 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .qm 2, .example 1)

## Summary
- 3313 nodes · 11380 edges · 136 communities (108 shown, 28 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 687 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `340d68a9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- write_jsonl
- make_llm
- App Package & Jobs
- test_ocr_preprocess.py
- Memory Screen
- Band & Cast Panel Views
- ReviewedLine
- Memory Manager Rows
- bench/audit.py
- test_feedback_loop.py
- Memory Manager Tests
- Bootstrap Wizard View
- test_review_state.py
- models.py
- Benchmark Suite
- Config Schema
- test_pinyin_voice_windows.py
- Series Management
- CastLine
- Video Preview (mpv)
- test_cast.py
- Memory Store
- test_suite.py
- core.py
- LineHistory
- OCR Engine & Geometry
- Subtitle Style
- Pipeline Runner & Locks
- util.py
- Episodes Screen
- Memory Proposals Apply
- render.py
- Voice Learning & Evidence
- core.py
- Audit & Dreaming Screens
- Settings & Run Panel
- Script Review & OCR Fix
- Frozen Baseline
- Bootstrap Seed
- YAML Comment-Preserving Edit
- ._load_editor
- test_render_delivery.py
- ocr_benchmark.py
- Episode
- read_jsonl
- Ingest & Change Detection
- Character Browser
- Runner
- memory/__init__.py
- Dreaming
- character_updates.py
- .probation
- New Series Dialog
- ._show_card
- Voice Match
- Bench Run Sandbox
- load_config
- Series-1 Voice Config
- ReviewView
- Band
- Series-1 Cast Config
- test_parser_stages.py
- conftest.py
- Architecture Guard Test
- ._loaded
- Frame Selector Widget
- Pinned Requirements
- Briefings & Style Rules
- delivery.py
- Top-level Config Keys
- FileLock
- Settings Schema Introspection
- NewCharacterDialog
- test_translate_review.py
- Memory Banks Writing
- LLM Provider Config
- probation.py
- kernel/__init__.py
- Voice Learning Tests
- Render Config
- device.py
- prefix.py
- Memory & Translation Prompts
- DropTable
- ._field
- Tag Editor Widget
- character_proposals
- Series-1 Band Config
- test_character_lifecycle.py
- runner.py
- .episode_update
- briefing_gen.py
- Flow Layout
- Prices Editor
- CastEngine
- AuditBar
- Settings Form
- Price Table Keys
- Memory Config Keys
- Series-1 series.yaml
- balanced_wrap
- save
- HistoryMixin
- group_map
- Series-1 OCR Config
- Series-1 Script Review Config
- joblock.py
- JobRunner
- test_new_voices.py
- sprite.py
- Translate Config
- measure.py
- migrate
- Background Workers
- _no_real_ffmpeg
- Vietnamese UI Fill
- Series-1 Cast
- Raw YAML Dialog
- Audit Config
- Sprite Config
- Series-1 Review Prompt
- Audio Config
- Output Config
- Review Config
- Windows Config
- Briefing & Story Prompts
- Project Metadata

## God Nodes (most connected - your core abstractions)
1. `ReviewedLine` - 162 edges
2. `Config` - 140 edges
3. `Paths` - 138 edges
4. `read_jsonl()` - 127 edges
5. `MemoryStore` - 112 edges
6. `seed_memory()` - 107 edges
7. `write_jsonl()` - 102 edges
8. `ReviewView` - 99 edges
9. `Registry` - 91 edges
10. `EpisodeContext` - 88 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `find_root()`  [INFERRED]
  app/__main__.py → subagent/settings/config.py
- `_same()` --calls--> `parse_aliases()`  [INFERRED]
  app/views/memory.py → subagent/memory/store.py
- `load()` --calls--> `voice_clips()`  [INFERRED]
  app/views/memory.py → subagent/voice/voice.py
- `load()` --indirect_call--> `episode_id()`  [INFERRED]
  app/views/review.py → subagent/workspace/episodes.py
- `check()` --calls--> `rule_checks()`  [INFERRED]
  app/views/review.py → subagent/translation/evaluate.py

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

## Communities (136 total, 28 thin omitted)

### Community 0 - "write_jsonl"
Cohesion: 0.07
Nodes (27): MainWindow, EpisodeRow, script_note(), Services, validate(), LineTranslation, PinyinLine, write_jsonl() (+19 more)

### Community 1 - "make_llm"
Cohesion: 0.08
Nodes (30): CostRecord, build_messages(), compute_cost(), _daily_quota(), _describe(), LLMClient, missing_prices(), record_cost() (+22 more)

### Community 2 - "App Package & Jobs"
Cohesion: 0.06
Nodes (13): choose_platform(), install_fonts(), install_translator(), main(), agent_label(), error_message(), stage_label(), status_label() (+5 more)

### Community 3 - "test_ocr_preprocess.py"
Cohesion: 0.14
Nodes (14): crop_view(), prepare(), save_sample(), subtitle_mask(), to_band_coords(), _band(), _event(), _gold() (+6 more)

### Community 4 - "Memory Screen"
Cohesion: 0.05
Nodes (9): EntryTable, _item(), MemoryView, done(), PairDialog, text(), _same(), _update_text() (+1 more)

### Community 5 - "Band & Cast Panel Views"
Cohesion: 0.07
Nodes (7): BandView, CastCanvas, CastPanel, ScaledImage, to_pixmap(), test_cast_panel_shows_boxes_and_records_corrections(), test_greyscale_images_can_be_shown()

### Community 6 - "ReviewedLine"
Cohesion: 0.07
Nodes (37): ReviewIncompleteError, PartialSuggestion, ReviewedLine, partial_review(), PartialResult, _session_bank(), _sprites(), suggest() (+29 more)

### Community 7 - "Memory Manager Rows"
Cohesion: 0.18
Nodes (22): merge_proposals(), replaced_term(), reviewed_glossary(), CommitInfo, Conflict, describe_update(), dumps_aliases(), held_updates() (+14 more)

### Community 8 - "bench/audit.py"
Cohesion: 0.06
Nodes (45): auditable(), auditable_lines(), AuditReport, build_report(), disagreements(), draw_sample(), EpisodeAudit, gold_speakers() (+37 more)

### Community 9 - "test_feedback_loop.py"
Cohesion: 0.20
Nodes (20): run(), user_json(), _rubric(), evaluator(), test_a_passing_line_keeps_the_evaluators_suggestion_for_the_reviewer(), test_reading_speed_is_flagged_not_retried(), test_retry_sends_history_and_suggestion(), vi_for() (+12 more)

### Community 10 - "Memory Manager Tests"
Cohesion: 0.08
Nodes (46): MemoryManager, save_line_voices(), seed_memory(), _line(), _llm(), _npc(), test_a_candidate_keeps_its_updates_when_promoted(), finish() (+38 more)

### Community 12 - "test_review_state.py"
Cohesion: 0.12
Nodes (20): all_correct_mark(), line_matches(), LineFilter, marked_count(), next_npc_number(), next_pending(), next_unmarked(), review_counts() (+12 more)

### Community 13 - "models.py"
Cohesion: 0.08
Nodes (22): freeze_finished(), Progress, collect_metrics(), episode_status(), test_pipeline_reports_script_reviewer_spending(), calls(), _handlers(), evaluator() (+14 more)

### Community 14 - "Benchmark Suite"
Cohesion: 0.15
Nodes (27): align(), _approved(), _auto_pattern(), characters_at(), _decisions(), _events(), Gold, gold_boxes() (+19 more)

### Community 15 - "Config Schema"
Cohesion: 0.08
Nodes (35): active_series(), AudioConfig, AuditConfig, BaselineConfig, BenchConfig, BudgetConfig, CleanupConfig, EpisodesConfig (+27 more)

### Community 16 - "test_pinyin_voice_windows.py"
Cohesion: 0.09
Nodes (20): is_han(), Character, GlossaryEntry, LogEntry, PronounPair, VoiceEntry, _word_tokenizer(), heteronyms() (+12 more)

### Community 17 - "Series Management"
Cohesion: 0.09
Nodes (35): cmd_series(), BudgetExceeded, ConfigError, JobRunningError, LLMCallError, LLMOutputError, StageError, SubagentError (+27 more)

### Community 18 - "CastLine"
Cohesion: 0.08
Nodes (22): crop(), _ffmpeg(), frame_path(), frame_time_ms(), get_engine(), group_unknowns(), keep_boxes(), line_motion() (+14 more)

### Community 19 - "Video Preview (mpv)"
Cohesion: 0.07
Nodes (6): fmt_time(), load_mpv(), PreviewWidget, TimelineSlider, _FakePlayer, test_preview_transport_controls()

### Community 20 - "test_cast.py"
Cohesion: 0.08
Nodes (28): _apply_labels(), apply_review_edits(), _check_talkers(), learn_sprites(), _name_unknowns(), plan(), _Plan, SpriteLearnResult (+20 more)

### Community 21 - "Memory Store"
Cohesion: 0.09
Nodes (12): build_bank(), _pairs_block(), glossary_zh_block(), new_voices_block(), MemoryStore, SpriteExemplar, test_bootstrap_seed_and_approve(), test_dreaming_proposals_and_apply() (+4 more)

### Community 22 - "test_suite.py"
Cohesion: 0.10
Nodes (21): candidates_for(), CastBoxEdit, CastDetection, CastLine, EditRecord, ScriptDecision, SpeakerCandidates, picture_veto() (+13 more)

### Community 23 - "core.py"
Cohesion: 0.12
Nodes (21): card_info(), card_media(), CharacterCard, confirmed_box(), _cut_clip(), _cut_picture(), _episode_ids(), _frame() (+13 more)

### Community 24 - "LineHistory"
Cohesion: 0.18
Nodes (4): LineHistory, _Clock, test_steps_are_per_line_and_copies(), test_undo_and_redo_restore_the_line_and_break_the_merge()

### Community 25 - "OCR Engine & Geometry"
Cohesion: 0.08
Nodes (16): onnx_use_cuda(), OcrBox, line_span(), symmetric_span(), create_engine(), _engine_key(), filter_boxes(), get_engine() (+8 more)

### Community 26 - "Subtitle Style"
Cohesion: 0.11
Nodes (19): calibrate(), grow_line(), labels_near(), load_style(), propose_regions(), _region_features(), save_style(), segment_mask() (+11 more)

### Community 27 - "Pipeline Runner & Locks"
Cohesion: 0.10
Nodes (9): _learn(), job_lock(), StageState, counts_text(), _pct(), write_report(), BatchItem, _episode_log (+1 more)

### Community 28 - "util.py"
Cohesion: 0.18
Nodes (9): _atomic_write(), hash_path(), lock_holder(), pid_alive(), _replace_with_retry(), sha256_bytes(), sha256_json(), run() (+1 more)

### Community 29 - "Episodes Screen"
Cohesion: 0.11
Nodes (5): job_busy(), AddDialog, EpisodesView, done(), confirm()

### Community 30 - "Memory Proposals Apply"
Cohesion: 0.17
Nodes (6): MemoryProposal, atomic_write_text(), ApplyMixin, ApplyResult, test_a_different_suggestion_for_the_same_term_still_comes_through(), gloss()

### Community 31 - "render.py"
Cohesion: 0.24
Nodes (11): _ass_text(), check_fonts(), choose_encoder(), encoder_args(), ffmpeg_args(), font_files(), preview_ass(), render() (+3 more)

### Community 32 - "Voice Learning & Evidence"
Cohesion: 0.13
Nodes (21): trusted_auto_lines(), usable_line(), _voices(), Config, auto_clips(), auto_gate(), AutoGate, build_centroids() (+13 more)

### Community 33 - "core.py"
Cohesion: 0.17
Nodes (18): available_encoders(), extract_clip(), extract_frame(), git(), has_video_stream(), imread(), imwrite_png(), iter_gray_frames() (+10 more)

### Community 34 - "Audit & Dreaming Screens"
Cohesion: 0.10
Nodes (5): AuditView, done(), DreamingView, _summary(), show_error()

### Community 35 - "Settings & Run Panel"
Cohesion: 0.09
Nodes (5): label(), reset_all(), save(), sequence(), SettingsView

### Community 36 - "Script Review & OCR Fix"
Cohesion: 0.11
Nodes (20): LineDecision, ScriptReviewConfig, examples_block(), find_repeats(), han_count(), memory_removals(), model_pass(), plausible_fix() (+12 more)

### Community 37 - "Frozen Baseline"
Cohesion: 0.16
Nodes (15): baseline_dir(), complete(), freeze(), freeze_episode(), _git_head(), _manifest(), memory_at_run(), _save_manifest() (+7 more)

### Community 38 - "Bootstrap Seed"
Cohesion: 0.09
Nodes (23): approve_seed(), _episode1_lines(), generate_seed(), load_seed(), name_pinyin(), save_clip(), save_seed(), seed_path() (+15 more)

### Community 39 - "YAML Comment-Preserving Edit"
Cohesion: 0.14
Nodes (17): file_comment(), _block_end(), delete_key(), _dump(), _find(), _get(), _is_child(), _path() (+9 more)

### Community 40 - "._load_editor"
Cohesion: 0.15
Nodes (4): _bullets(), check(), show(), _section()

### Community 41 - "test_render_delivery.py"
Cohesion: 0.17
Nodes (11): build_ass(), _color(), Layout, _style(), _line(), test_ass_has_two_events_per_line_with_same_timing(), test_deleted_lines_are_not_rendered(), test_deliver_moves_and_never_overwrites_silently() (+3 more)

### Community 42 - "ocr_benchmark.py"
Cohesion: 0.12
Nodes (16): _covered(), EpisodeOcrScore, _existing_events(), gold_lines(), load_key(), _norm(), OcrBenchResult, _overlap() (+8 more)

### Community 43 - "Episode"
Cohesion: 0.10
Nodes (18): EpisodeNotFoundError, SourceMissingError, Episode, AddCandidate, derived_status(), detect_number(), fingerprint(), Registry (+10 more)

### Community 44 - "read_jsonl"
Cohesion: 0.15
Nodes (23): run(), run(), frame_reader(), read_jsonl(), reviewer_corrections(), run(), crop_path(), run() (+15 more)

### Community 45 - "Ingest & Change Detection"
Cohesion: 0.17
Nodes (19): ChangeRecord, binarize(), Change, change_fraction(), detect_changes(), draw_band(), fuse(), has_subtitle() (+11 more)

### Community 46 - "Character Browser"
Cohesion: 0.12
Nodes (6): CharacterBrowser, CharacterStrip, describe(), _pixmap(), ClipPlayer, test_character_browser_lists_cards_and_assigns()

### Community 47 - "Runner"
Cohesion: 0.35
Nodes (3): Runner, StageDef, ocr_hash()

### Community 48 - "memory/__init__.py"
Cohesion: 0.09
Nodes (23): _kept_evaluation(), Evaluation, SubtitleEvent, judge(), llm_rubric(), max_chars_for(), rubric_payload(), RubricLine (+15 more)

### Community 49 - "Dreaming"
Cohesion: 0.10
Nodes (27): read_json(), apply_dream(), approved_lines(), describe(), done_episodes(), dream(), _dream_variable(), DreamGlossary (+19 more)

### Community 50 - "character_updates.py"
Cohesion: 0.13
Nodes (14): _alias_zh(), CharacterChange, CharacterUpdateResponse, check(), _clip(), _has_word(), _introduces(), _positions() (+6 more)

### Community 51 - ".probation"
Cohesion: 0.12
Nodes (5): load_line_voices(), CandidatesMixin, _Run, speaker_lines(), episode_number()

### Community 52 - "New Series Dialog"
Cohesion: 0.13
Nodes (5): NewSeriesDialog, StyleDialog, test_new_series_dialog_asks_for_the_default_pronoun_pair(), test_new_series_dialog_creates_a_translation_style(), test_new_series_work_folder_can_be_chosen()

### Community 53 - "._show_card"
Cohesion: 0.11
Nodes (8): done(), done(), failed(), load(), done(), done(), failed(), done()

### Community 54 - "Voice Match"
Cohesion: 0.16
Nodes (14): load(), VoiceConfig, all_similarities(), classify(), find_new_voices(), group_voices(), l2_normalize(), load_audio_any() (+6 more)

### Community 55 - "Bench Run Sandbox"
Cohesion: 0.16
Nodes (13): checkout_memory(), _drop_heavy(), _frozen_inputs(), _install_review(), _null(), _rerun_episode(), run(), _run_info() (+5 more)

### Community 56 - "load_config"
Cohesion: 0.18
Nodes (13): prompt_hash(), check_id(), list_registers(), load_register(), _parse(), Register, register_dir(), save_register() (+5 more)

### Community 57 - "Series-1 Voice Config"
Cohesion: 0.08
Nodes (24): voice, accept_score, confusable_similarity, learn_auto_allowed_flags, learn_auto_max_drop, learn_auto_min_margin, learn_auto_min_score, learn_auto_min_test_lines (+16 more)

### Community 59 - "Band"
Cohesion: 0.13
Nodes (6): center_in_band(), build_mask_filter(), Band, test_band_pixels_are_even_and_inside_frame(), test_band_centres_by_widening_the_short_side(), test_mask_filters()

### Community 60 - "Series-1 Cast Config"
Cohesion: 0.09
Nodes (23): cast, add_similarity, detector_model, embed_model, enabled, frame_width, learn, match_margin (+15 more)

### Community 61 - "test_parser_stages.py"
Cohesion: 0.12
Nodes (22): OcrReading, absorb_fragments(), build_events(), flag_non_dialogue(), frames_on_screen(), _Group, group_readings(), _median() (+14 more)

### Community 62 - "conftest.py"
Cohesion: 0.10
Nodes (8): build_parser(), _setup_logging(), FakeClient, FakeCompletions, _clip(), _fake_embed(), test_cli_errors_are_json_with_codes(), test_cli_status_and_add()

### Community 63 - "Architecture Guard Test"
Cohesion: 0.17
Nodes (8): _breaches(), _imports(), _module_of(), _submodules(), test_every_package_is_a_known_module_with_a_public_api(), test_modules_import_each_other_only_through_their_api_and_downwards(), test_the_app_reaches_the_core_only_through_its_services(), test_the_core_never_imports_the_app_or_qt()

### Community 64 - "._loaded"
Cohesion: 0.15
Nodes (3): flag_label(), loaded(), opened()

### Community 66 - "Pinned Requirements"
Cohesion: 0.10
Nodes (20): jieba 0.42.1, numpy 2.5.3, onnxruntime-gpu 1.30.0, openai 3.22.1, opencv-python-headless 5.0.0.93, pillow 12.3.0, pydantic 2.13.5, pypinyin 0.55.0 (+12 more)

### Community 67 - "Briefings & Style Rules"
Cohesion: 0.21
Nodes (12): briefings_dir(), cap_style_rules(), IndexEntry, list_episode_briefings(), _read(), read_index(), read_story(), read_style_rules() (+4 more)

### Community 68 - "delivery.py"
Cohesion: 0.14
Nodes (14): OutputExistsError, OutputFolderError, cleanup(), deliver(), keep_both_path(), output_folder(), output_name(), resolve_conflict() (+6 more)

### Community 69 - "Top-level Config Keys"
Cohesion: 0.10
Nodes (19): budget, max_cost_per_episode, cleanup, auto, device, episodes, number_patterns, video_extensions (+11 more)

### Community 71 - "Settings Schema Introspection"
Cohesion: 0.13
Nodes (10): add(), _code_notes(), fields(), walk(), FieldSpec, known_sets(), target(), _unwrap() (+2 more)

### Community 73 - "test_translate_review.py"
Cohesion: 0.15
Nodes (14): rule_checks(), RuleContext, sample_events(), test_predeleted_lines_are_not_reviewer_edits(), _line(), _review_ctx(), rules(), test_events_without_translation_are_flagged() (+6 more)

### Community 74 - "Memory Banks Writing"
Cohesion: 0.14
Nodes (6): _add_exemplars(), BanksMixin, _drop_exemplar(), _keep_best(), _record_votes(), _undo_episode()

### Community 75 - "LLM Provider Config"
Cohesion: 0.11
Nodes (18): api_key_env, base_url, model, llm, max_retries, max_retry_wait_s, providers, temperature (+10 more)

### Community 76 - "probation.py"
Cohesion: 0.20
Nodes (5): candidate_looks(), candidate_voice(), check_return(), ReturnCheck, _unit()

### Community 77 - "kernel/__init__.py"
Cohesion: 0.09
Nodes (21): MemoryLockedError, Window, contains_term(), edit_distance(), found_terms(), keep_cjk(), nfc(), normalize_zh() (+13 more)

### Community 78 - "Voice Learning Tests"
Cohesion: 0.28
Nodes (10): _auto_episode(), _episode(), _fake_embed(), test_auto_lines_pass_only_when_every_signal_agrees(), test_auto_lines_that_hurt_accuracy_are_not_learned(), test_auto_lines_that_keep_accuracy_are_learned(), test_auto_lines_wait_until_there_is_enough_to_measure(), test_learn_writes_bank_and_evaluate_reports_accuracy() (+2 more)

### Community 79 - "Render Config"
Cohesion: 0.12
Nodes (17): render, avg_char_width, blur_radius, encoder, font_dir, font_name, line_spacing, mask (+9 more)

### Community 80 - "device.py"
Cohesion: 0.19
Nodes (5): describe(), onnx_cuda_available(), torch_cuda_available(), torch_device(), Embedder

### Community 81 - "prefix.py"
Cohesion: 0.35
Nodes (8): characters_block(), corrections_block(), evaluator_prefix(), glossary_block(), pronoun_block(), story_block(), style_block(), translator_prefix()

### Community 82 - "Memory & Translation Prompts"
Cohesion: 0.19
Nodes (8): Style rules, Cổ trang / tiên hiệp register (Hán-Việt terms), identify / default_pair template toggle, Memory proposals (glossary / pronoun_pair / character), Pronoun matrix, Retries with earlier_attempts and evaluator_suggestion, Reviewer corrections, Speaker rules per voice status (fixed/confusable/disputed/new_voice/unknown/too_short)

### Community 84 - "._field"
Cohesion: 0.25
Nodes (3): _decimals(), Field, set_float()

### Community 86 - "character_proposals"
Cohesion: 0.50
Nodes (3): character_proposals(), save(), episode_id()

### Community 87 - "Series-1 Band Config"
Cohesion: 0.13
Nodes (15): bottom, left, right, top, video, band_frames, change_threshold, empty_text_ratio (+7 more)

### Community 88 - "test_character_lifecycle.py"
Cohesion: 0.40
Nodes (11): CharacterFate, _lines(), _setup(), _status(), test_consecutive_episodes_keep_a_character(), test_first_run_counts_earlier_episodes(), test_generic_characters_are_never_matched_or_learned(), test_old_memory_gets_the_new_columns() (+3 more)

### Community 89 - "runner.py"
Cohesion: 0.19
Nodes (6): ModelUnavailableError, _lazy(), review_outputs(), _source_key(), test_finish_review_never_fails_on_missing_voice_model(), boom()

### Community 90 - ".episode_update"
Cohesion: 0.10
Nodes (4): now_iso(), EpisodeMixin, _next_status(), UpdatesMixin

### Community 91 - "briefing_gen.py"
Cohesion: 0.33
Nodes (6): BriefingResponse, compress_story(), generate_briefing(), script_text(), StoryResponse, word_count()

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

### Community 101 - "balanced_wrap"
Cohesion: 0.43
Nodes (4): balanced_wrap(), split_explicit_lines(), wrap_words(), wrap_lines()

### Community 102 - "save"
Cohesion: 0.47
Nodes (5): headline(), _r(), render(), save(), SuiteResult

### Community 104 - "group_map"
Cohesion: 0.50
Nodes (3): group_map(), mapping(), test_group_map_is_one_to_one_by_shared_lines()

### Community 105 - "Series-1 OCR Config"
Cohesion: 0.18
Nodes (11): ocr, fragment_max_samples, fragment_merge_similarity, mask_image, mask_scale, merge_max_edit_distance, min_confidence, preprocess (+3 more)

### Community 106 - "Series-1 Script Review Config"
Cohesion: 0.18
Nodes (11): script_review, enabled, example_limit, max_remove_share, memory_auto_remove_min, memory_max_han, remove_confidence, repeat_merge_gap_ms (+3 more)

### Community 107 - "joblock.py"
Cohesion: 0.17
Nodes (3): job_lock_path(), running_jobs(), EpisodeLockedError

### Community 108 - "JobRunner"
Cohesion: 0.20
Nodes (3): JobRunner, test_run_panel_has_a_script_review_step(), __init__()

### Community 109 - "test_new_voices.py"
Cohesion: 0.12
Nodes (19): NewVoice, draft_voice_ids(), episode_character_ids(), is_auto_id(), is_unnamed(), load_new_voices(), new_voice_id(), review_voice_ids() (+11 more)

### Community 110 - "sprite.py"
Cohesion: 0.14
Nodes (4): best_match(), decide(), load_templates(), save_template()

### Community 111 - "Translate Config"
Cohesion: 0.22
Nodes (9): translate, max_cps, max_line_chars, max_lines_per_event, max_retries, picture_evidence, picture_veto, pronoun_terms (+1 more)

### Community 112 - "measure.py"
Cohesion: 0.09
Nodes (35): _ask(), build_pipeline(), _interactive(), _output_exists(), _resolve_on_exists(), add_add(), add_batch(), add_calibrate() (+27 more)

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
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1026 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ReviewedLine` connect `ReviewedLine` to `write_jsonl`, `App Package & Jobs`, `test_ocr_preprocess.py`, `Memory Manager Rows`, `bench/audit.py`, `test_feedback_loop.py`, `Memory Manager Tests`, `test_review_state.py`, `models.py`, `Benchmark Suite`, `CastLine`, `test_cast.py`, `Memory Store`, `test_suite.py`, `core.py`, `LineHistory`, `Pipeline Runner & Locks`, `render.py`, `Voice Learning & Evidence`, `Script Review & OCR Fix`, `._load_editor`, `test_render_delivery.py`, `ocr_benchmark.py`, `Dreaming`, `character_updates.py`, `.probation`, `ReviewView`, `conftest.py`, `._loaded`, `Briefings & Style Rules`, `test_translate_review.py`, `probation.py`, `kernel/__init__.py`, `Voice Learning Tests`, `prefix.py`, `test_character_lifecycle.py`, `runner.py`, `.episode_update`, `briefing_gen.py`, `AuditBar`, `test_new_voices.py`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ReviewedLine` (e.g. with `_finish()` and `test_pipeline_records_what_the_reviewer_removed_and_kept()`) actually correct?**
  _`ReviewedLine` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `subagent`, `Font draws 了 like digit 7`, `Show wording that looks like stray text (史 for 屎, 鸡道, 姬叔)` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `write_jsonl` be split into smaller, more focused modules?**
  _Cohesion score 0.07192982456140351 - nodes in this community are weakly interconnected._
- **Why does `Config` connect `Voice Learning & Evidence` to `make_llm`, `ReviewedLine`, `Memory Manager Rows`, `bench/audit.py`, `Memory Manager Tests`, `Benchmark Suite`, `Config Schema`, `test_pinyin_voice_windows.py`, `Series Management`, `CastLine`, `test_cast.py`, `Memory Store`, `core.py`, `OCR Engine & Geometry`, `Pipeline Runner & Locks`, `render.py`, `Frozen Baseline`, `Bootstrap Seed`, `test_render_delivery.py`, `ocr_benchmark.py`, `Episode`, `memory/__init__.py`, `Dreaming`, `character_updates.py`, `Voice Match`, `Bench Run Sandbox`, `load_config`, `Band`, `test_parser_stages.py`, `conftest.py`, `delivery.py`, `Settings Schema Introspection`, `device.py`, `runner.py`, `briefing_gen.py`, `measure.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Config` (e.g. with `fields()` and `value_at()`) actually correct?**
  _`Config` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `make_llm` be split into smaller, more focused modules?**
  _Cohesion score 0.07936507936507936 - nodes in this community are weakly interconnected._