# Graph Report - Subtitle-translator  (2026-11-03)

## Corpus Check
- 214 files · ~169,200 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .qm 2, .example 1)

## Summary
- 3306 nodes · 11359 edges · 134 communities (106 shown, 28 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 687 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `80e38a97`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_app.py
- LLMClient
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
- PinyinEngine
- Series Management
- CastLine
- Video Preview (mpv)
- test_cast.py
- Memory Store
- test_suite.py
- card.py
- Services
- OCR Engine & Geometry
- Subtitle Style
- Pipeline Runner & Locks
- conftest.py
- Episodes Screen
- Memory Proposals Apply
- benchmark.py
- Voice Learning & Evidence
- core.py
- Audit & Dreaming Screens
- Settings & Run Panel
- Script Review & OCR Fix
- Frozen Baseline
- Bootstrap Seed
- YAML Comment-Preserving Edit
- ._load_editor
- render.py
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
- .__init__
- Series-1 Cast Config
- test_parser_stages.py
- subagent/__main__.py
- Architecture Guard Test
- pytest
- Frame Selector Widget
- Pinned Requirements
- Briefings & Style Rules
- kernel/__init__.py
- Top-level Config Keys
- FileLock
- Settings Schema Introspection
- NewCharacterDialog
- rule_checks
- Memory Banks Writing
- LLM Provider Config
- symmetric_span
- evaluate.py
- Voice Learning Tests
- Render Config
- test_probation.py
- Memory & Translation Prompts
- json
- ._field
- Tag Editor Widget
- character_dialog.py
- Series-1 Band Config
- memory/__init__.py
- runner.py
- .episode_update
- cv2
- Flow Layout
- Prices Editor
- AuditMark
- Settings Form
- Price Table Keys
- Memory Config Keys
- Series-1 series.yaml
- workspace/episodes.py
- test_partial_review.py
- .effective_status
- Progress
- Series-1 OCR Config
- Series-1 Script Review Config
- HistoryMixin
- JobRunner
- test_new_voices.py
- sprite.py
- Translate Config
- measure.py
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
1. `ReviewedLine` - 159 edges
2. `Config` - 140 edges
3. `Paths` - 138 edges
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
- `review_counts()` --calls--> `needs_attention()`  [INFERRED]
  app/views/review_state.py → subagent/review/review.py
- `row_state()` --calls--> `needs_attention()`  [INFERRED]
  app/views/review_state.py → subagent/review/review.py

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

## Communities (134 total, 28 thin omitted)

### Community 0 - "test_app.py"
Cohesion: 0.19
Nodes (24): MainWindow, LineTranslation, PinyinLine, write_jsonl(), gate(), sample_events(), write_events(), qapp() (+16 more)

### Community 1 - "LLMClient"
Cohesion: 0.13
Nodes (9): compute_cost(), _daily_quota(), _describe(), LLMClient, _retryable(), schema_instruction(), _short_error(), _strip_fence() (+1 more)

### Community 2 - "App Package & Jobs"
Cohesion: 0.07
Nodes (10): choose_platform(), install_fonts(), install_translator(), main(), agent_label(), status_label(), ReviewData, choose_batch_on_exists() (+2 more)

### Community 3 - "test_ocr_preprocess.py"
Cohesion: 0.11
Nodes (22): load_key(), _norm(), score_episode(), crop_view(), prepare(), save_sample(), subtitle_mask(), _band() (+14 more)

### Community 4 - "Memory Screen"
Cohesion: 0.06
Nodes (7): EntryTable, _item(), MemoryView, PairDialog, _same(), _update_text(), run_async()

### Community 5 - "Band & Cast Panel Views"
Cohesion: 0.07
Nodes (7): BandView, CastCanvas, CastPanel, ScaledImage, to_pixmap(), test_cast_panel_shows_boxes_and_records_corrections(), test_greyscale_images_can_be_shown()

### Community 6 - "ReviewedLine"
Cohesion: 0.08
Nodes (37): check(), ReviewIncompleteError, ReviewedLine, ScriptDecision, apply_script_review(), build_draft(), compute_edits(), finish_review() (+29 more)

### Community 7 - "Memory Manager Rows"
Cohesion: 0.18
Nodes (21): merge_proposals(), replaced_term(), reviewed_glossary(), CommitInfo, Conflict, describe_update(), held_updates(), MemoryDiff (+13 more)

### Community 8 - "bench/audit.py"
Cohesion: 0.10
Nodes (32): auditable(), auditable_lines(), AuditReport, build_report(), disagreements(), draw_sample(), EpisodeAudit, gold_speakers() (+24 more)

### Community 9 - "test_feedback_loop.py"
Cohesion: 0.14
Nodes (25): run(), user_json(), _reading(), _rubric(), evaluator(), test_a_passing_line_keeps_the_evaluators_suggestion_for_the_reviewer(), test_fragments_merge_by_time_on_screen_and_noise_is_predeleted(), test_reading_speed_is_flagged_not_retried() (+17 more)

### Community 10 - "Memory Manager Tests"
Cohesion: 0.11
Nodes (34): EditRecord, MemoryManager, save_line_voices(), seed_memory(), test_dreaming_proposals_and_apply(), _line(), _llm(), _npc() (+26 more)

### Community 12 - "test_review_state.py"
Cohesion: 0.11
Nodes (16): line_matches(), LineFilter, LineHistory, next_npc_number(), next_pending(), review_counts(), ReviewCounts, _Clock (+8 more)

### Community 13 - "models.py"
Cohesion: 0.14
Nodes (20): episode_status(), register_episode(), test_pipeline_reports_script_reviewer_spending(), test_mode_blocks_in_prompts(), test_off_skips_identification_and_learns_no_characters(), test_turning_it_on_again_runs_the_stages(), calls(), _handlers() (+12 more)

### Community 14 - "Benchmark Suite"
Cohesion: 0.10
Nodes (37): align(), _approved(), _auto_pattern(), characters_at(), _decisions(), _events(), Gold, gold_boxes() (+29 more)

### Community 15 - "Config Schema"
Cohesion: 0.08
Nodes (30): AudioConfig, AuditConfig, Band, BaselineConfig, BenchConfig, BudgetConfig, CastConfig, CleanupConfig (+22 more)

### Community 16 - "PinyinEngine"
Cohesion: 0.12
Nodes (10): Character, LogEntry, VoiceEntry, PinyinEngine, Token, _engine(), test_pinyin_uses_glossary_and_attaches_punctuation(), test_pinyin_words_are_joined_within_and_spaced_between() (+2 more)

### Community 17 - "Series Management"
Cohesion: 0.12
Nodes (21): add_series(), cmd_series(), find_root(), load_config(), _load_env(), add(), _blocks(), check_slug() (+13 more)

### Community 18 - "CastLine"
Cohesion: 0.05
Nodes (36): build_bank(), CastEngine, crop(), _ffmpeg(), frame_path(), frame_time_ms(), get_engine(), group_unknowns() (+28 more)

### Community 19 - "Video Preview (mpv)"
Cohesion: 0.06
Nodes (7): fmt_time(), load_mpv(), PreviewWidget, TimelineSlider, text(), _FakePlayer, test_preview_transport_controls()

### Community 20 - "test_cast.py"
Cohesion: 0.17
Nodes (16): EpisodeState, save_state(), FakeEngine, _frame(), _lines(), test_auto_mode_learns_only_from_trusted_lines(), test_backfill_runs_cast_where_missing_then_learns(), fake_cast() (+8 more)

### Community 21 - "Memory Store"
Cohesion: 0.09
Nodes (10): _present_block(), glossary_zh_block(), new_voices_block(), ocr_fix_prefix(), MemoryStore, _voices(), _clip(), _fake_embed() (+2 more)

### Community 22 - "test_suite.py"
Cohesion: 0.11
Nodes (20): confirmed_box(), CastBoxEdit, CastDetection, test_picture_veto_disputes_the_voice(), line(), _cast(), _line(), _setup() (+12 more)

### Community 23 - "card.py"
Cohesion: 0.22
Nodes (9): card_info(), card_media(), CharacterCard, _cut_clip(), _cut_picture(), _episode_ids(), pin_card(), pin_dir() (+1 more)

### Community 25 - "OCR Engine & Geometry"
Cohesion: 0.08
Nodes (16): describe(), onnx_cuda_available(), onnx_use_cuda(), torch_cuda_available(), OcrBox, center_in_band(), create_engine(), _engine_key() (+8 more)

### Community 26 - "Subtitle Style"
Cohesion: 0.15
Nodes (16): calibrate(), grow_line(), labels_near(), load_style(), propose_regions(), _region_features(), save_style(), segment_mask() (+8 more)

### Community 27 - "Pipeline Runner & Locks"
Cohesion: 0.12
Nodes (5): _learn(), job_lock(), StageState, _episode_log, Pipeline

### Community 28 - "conftest.py"
Cohesion: 0.08
Nodes (26): CostRecord, build_messages(), missing_prices(), record_cost(), _server_delay(), _usage_numbers(), FakeClient, FakeCompletions (+18 more)

### Community 29 - "Episodes Screen"
Cohesion: 0.09
Nodes (5): job_busy(), AddDialog, DropTable, EpisodesView, done()

### Community 30 - "Memory Proposals Apply"
Cohesion: 0.17
Nodes (7): MemoryProposal, atomic_write_text(), now_iso(), ApplyMixin, ApplyResult, test_a_different_suggestion_for_the_same_term_still_comes_through(), gloss()

### Community 31 - "benchmark.py"
Cohesion: 0.16
Nodes (12): _acc(), benchmark_episodes(), BenchmarkResult, _copy_reviewer_context(), _drop_heavy_files(), EpisodeScore, render(), run_benchmark() (+4 more)

### Community 32 - "Voice Learning & Evidence"
Cohesion: 0.11
Nodes (23): trusted_auto_lines(), usable_line(), Config, auto_clips(), auto_gate(), AutoGate, build_centroids(), Clip (+15 more)

### Community 33 - "core.py"
Cohesion: 0.08
Nodes (27): job_lock_path(), running_jobs(), available_encoders(), extract_clip(), extract_frame(), git(), has_video_stream(), imread() (+19 more)

### Community 34 - "Audit & Dreaming Screens"
Cohesion: 0.09
Nodes (8): error_message(), AuditView, done(), DreamingView, _summary(), done(), confirm(), show_error()

### Community 35 - "Settings & Run Panel"
Cohesion: 0.12
Nodes (4): reset_all(), save(), sequence(), SettingsView

### Community 36 - "Script Review & OCR Fix"
Cohesion: 0.13
Nodes (17): edit_distance(), normalize_zh(), relatedness(), LineDecision, ScriptReviewConfig, examples_block(), find_repeats(), han_count() (+9 more)

### Community 37 - "Frozen Baseline"
Cohesion: 0.21
Nodes (11): baseline_dir(), complete(), freeze(), freeze_episode(), _git_head(), _manifest(), memory_at_run(), _save_manifest() (+3 more)

### Community 38 - "Bootstrap Seed"
Cohesion: 0.11
Nodes (18): approve_seed(), _episode1_lines(), generate_seed(), load_seed(), name_pinyin(), save_clip(), save_seed(), seed_path() (+10 more)

### Community 39 - "YAML Comment-Preserving Edit"
Cohesion: 0.14
Nodes (17): file_comment(), _block_end(), delete_key(), _dump(), _find(), _get(), _is_child(), _path() (+9 more)

### Community 41 - "render.py"
Cohesion: 0.06
Nodes (36): _atomic_write(), _replace_with_retry(), deliver(), keep_both_path(), output_folder(), output_name(), resolve_conflict(), reveal_in_explorer() (+28 more)

### Community 42 - "ocr_benchmark.py"
Cohesion: 0.11
Nodes (16): _covered(), EpisodeOcrScore, _existing_events(), gold_lines(), ocr_episodes(), OcrBenchResult, _overlap(), remap_ids() (+8 more)

### Community 43 - "Episode"
Cohesion: 0.18
Nodes (10): cmd_add(), Episode, derived_status(), Registry, add(), test_add_register_duplicates_and_numbers(), test_missing_source_and_relink(), test_no_video_stream_is_skipped() (+2 more)

### Community 44 - "read_jsonl"
Cohesion: 0.08
Nodes (41): run(), SpeakerCandidates, SubtitleEvent, keep_cjk(), chunked(), read_jsonl(), load_prompt(), reviewer_corrections() (+33 more)

### Community 45 - "Ingest & Change Detection"
Cohesion: 0.18
Nodes (17): binarize(), Change, change_fraction(), detect_changes(), has_subtitle(), outlined_ratio(), text_ratio(), VideoConfig (+9 more)

### Community 46 - "Character Browser"
Cohesion: 0.12
Nodes (6): CharacterBrowser, CharacterStrip, describe(), _pixmap(), ClipPlayer, test_character_browser_lists_cards_and_assigns()

### Community 47 - "Runner"
Cohesion: 0.27
Nodes (5): hash_path(), sha256_json(), Runner, StageDef, ocr_hash()

### Community 48 - "memory/__init__.py"
Cohesion: 0.13
Nodes (15): _kept_evaluation(), Evaluation, Window, judge(), RuleFailure, _best(), context_row(), ProposalDraft (+7 more)

### Community 49 - "Dreaming"
Cohesion: 0.09
Nodes (29): _frame(), trusted_speakers(), compress_story(), apply_dream(), approved_lines(), describe(), done_episodes(), dream() (+21 more)

### Community 50 - "character_updates.py"
Cohesion: 0.16
Nodes (14): _alias_zh(), CharacterChange, CharacterUpdateResponse, check(), _clip(), _has_word(), _introduces(), _pairs_block() (+6 more)

### Community 51 - ".probation"
Cohesion: 0.08
Nodes (10): load_line_voices(), CandidatesMixin, _Run, candidate_looks(), candidate_voice(), check_return(), ReturnCheck, speaker_lines() (+2 more)

### Community 52 - "New Series Dialog"
Cohesion: 0.13
Nodes (5): NewSeriesDialog, StyleDialog, test_new_series_dialog_asks_for_the_default_pronoun_pair(), test_new_series_dialog_creates_a_translation_style(), test_new_series_work_folder_can_be_chosen()

### Community 53 - "._show_card"
Cohesion: 0.15
Nodes (6): done(), failed(), done(), done(), failed(), done()

### Community 54 - "Voice Match"
Cohesion: 0.10
Nodes (17): load(), update_voices(), torch_device(), new_voice_id(), all_similarities(), compute_centroids(), Embedder, find_new_voices() (+9 more)

### Community 55 - "Bench Run Sandbox"
Cohesion: 0.16
Nodes (13): checkout_memory(), _drop_heavy(), _frozen_inputs(), _install_review(), _null(), _rerun_episode(), run(), _run_info() (+5 more)

### Community 56 - "load_config"
Cohesion: 0.21
Nodes (13): check_id(), list_registers(), load_register(), _parse(), Register, register_dir(), save_register(), split_terms() (+5 more)

### Community 57 - "Series-1 Voice Config"
Cohesion: 0.08
Nodes (24): voice, accept_score, confusable_similarity, learn_auto_allowed_flags, learn_auto_max_drop, learn_auto_min_margin, learn_auto_min_score, learn_auto_min_test_lines (+16 more)

### Community 58 - "ReviewView"
Cohesion: 0.08
Nodes (4): flag_label(), ReviewView, loaded(), opened()

### Community 59 - ".__init__"
Cohesion: 0.21
Nodes (3): stage_label(), label(), RunPanel

### Community 60 - "Series-1 Cast Config"
Cohesion: 0.09
Nodes (23): cast, add_similarity, detector_model, embed_model, enabled, frame_width, learn, match_margin (+15 more)

### Community 61 - "test_parser_stages.py"
Cohesion: 0.15
Nodes (17): OcrReading, absorb_fragments(), build_events(), flag_non_dialogue(), frames_on_screen(), _Group, group_readings(), _median() (+9 more)

### Community 62 - "subagent/__main__.py"
Cohesion: 0.21
Nodes (6): build_parser(), main(), _setup_logging(), test_cli_errors_are_json_with_codes(), test_cli_status_and_add(), test_new_series_asks_how_pronouns_are_decided()

### Community 63 - "Architecture Guard Test"
Cohesion: 0.17
Nodes (8): _breaches(), _imports(), _module_of(), _submodules(), test_every_package_is_a_known_module_with_a_public_api(), test_modules_import_each_other_only_through_their_api_and_downwards(), test_the_app_reaches_the_core_only_through_its_services(), test_the_core_never_imports_the_app_or_qt()

### Community 64 - "pytest"
Cohesion: 0.14
Nodes (13): ConfigError, active_series(), list_series(), merge_sections(), parse_config(), _read_yaml(), save_config_text(), save_settings() (+5 more)

### Community 66 - "Pinned Requirements"
Cohesion: 0.10
Nodes (20): jieba 0.42.1, numpy 2.5.3, onnxruntime-gpu 1.30.0, openai 3.22.1, opencv-python-headless 5.0.0.93, pillow 12.3.0, pydantic 2.13.5, pypinyin 0.55.0 (+12 more)

### Community 67 - "Briefings & Style Rules"
Cohesion: 0.18
Nodes (15): generate_briefing(), script_text(), briefings_dir(), cap_style_rules(), IndexEntry, list_episode_briefings(), _read(), read_index() (+7 more)

### Community 68 - "kernel/__init__.py"
Cohesion: 0.15
Nodes (18): BudgetExceeded, EpisodeLockedError, EpisodeNotFoundError, JobRunningError, LLMCallError, LLMOutputError, MemoryLockedError, MissingBinaryError (+10 more)

### Community 69 - "Top-level Config Keys"
Cohesion: 0.10
Nodes (19): budget, max_cost_per_episode, cleanup, auto, device, episodes, number_patterns, video_extensions (+11 more)

### Community 70 - "FileLock"
Cohesion: 0.24
Nodes (3): FileLock, lock_holder(), pid_alive()

### Community 71 - "Settings Schema Introspection"
Cohesion: 0.12
Nodes (11): add(), _code_notes(), fields(), walk(), FieldSpec, known_sets(), target(), _unwrap() (+3 more)

### Community 72 - "NewCharacterDialog"
Cohesion: 0.15
Nodes (5): NewCharacterDialog, done(), save(), load(), episode_id()

### Community 73 - "rule_checks"
Cohesion: 0.16
Nodes (6): GlossaryEntry, max_chars_for(), rule_checks(), RuleContext, _word_tokenizer(), test_glossary_rule_matches_whole_words_only()

### Community 74 - "Memory Banks Writing"
Cohesion: 0.14
Nodes (6): _add_exemplars(), BanksMixin, _drop_exemplar(), _keep_best(), _record_votes(), _undo_episode()

### Community 75 - "LLM Provider Config"
Cohesion: 0.11
Nodes (18): api_key_env, base_url, model, llm, max_retries, max_retry_wait_s, providers, temperature (+10 more)

### Community 76 - "symmetric_span"
Cohesion: 0.25
Nodes (3): line_span(), symmetric_span(), test_symmetric_span_trims_the_far_side_beyond_half_a_line()

### Community 77 - "evaluate.py"
Cohesion: 0.12
Nodes (12): balanced_wrap(), contains_term(), found_terms(), nfc(), split_explicit_lines(), visible_chars(), wrap_words(), llm_rubric() (+4 more)

### Community 78 - "Voice Learning Tests"
Cohesion: 0.28
Nodes (10): _auto_episode(), _episode(), _fake_embed(), test_auto_lines_pass_only_when_every_signal_agrees(), test_auto_lines_that_hurt_accuracy_are_not_learned(), test_auto_lines_that_keep_accuracy_are_learned(), test_auto_lines_wait_until_there_is_enough_to_measure(), test_learn_writes_bank_and_evaluate_reports_accuracy() (+2 more)

### Community 79 - "Render Config"
Cohesion: 0.12
Nodes (17): render, avg_char_width, blur_radius, encoder, font_dir, font_name, line_spacing, mask (+9 more)

### Community 80 - "test_probation.py"
Cohesion: 0.25
Nodes (14): NewVoice, Candidate, _finish(), _lines(), _talks(), test_a_candidate_not_back_in_time_is_dropped(), test_a_new_voice_waits_on_probation_and_is_promoted_when_it_comes_back(), test_a_review_npc_goes_on_probation_at_finish() (+6 more)

### Community 82 - "Memory & Translation Prompts"
Cohesion: 0.19
Nodes (8): Style rules, Cổ trang / tiên hiệp register (Hán-Việt terms), identify / default_pair template toggle, Memory proposals (glossary / pronoun_pair / character), Pronoun matrix, Retries with earlier_attempts and evaluator_suggestion, Reviewer corrections, Speaker rules per voice status (fixed/confusable/disputed/new_voice/unknown/too_short)

### Community 83 - "json"
Cohesion: 0.19
Nodes (4): read_json(), dumps_aliases(), UpdatesMixin, parse_aliases()

### Community 84 - "._field"
Cohesion: 0.25
Nodes (3): _decimals(), Field, set_float()

### Community 86 - "character_dialog.py"
Cohesion: 0.40
Nodes (3): character_proposals(), validate(), is_han()

### Community 87 - "Series-1 Band Config"
Cohesion: 0.13
Nodes (15): bottom, left, right, top, video, band_frames, change_threshold, empty_text_ratio (+7 more)

### Community 88 - "memory/__init__.py"
Cohesion: 0.15
Nodes (21): BriefingResponse, CharacterFate, StoryResponse, characters_block(), corrections_block(), evaluator_prefix(), glossary_block(), pronoun_block() (+13 more)

### Community 89 - "runner.py"
Cohesion: 0.08
Nodes (15): cleanup(), collect_metrics(), counts_text(), _pct(), write_report(), BatchItem, prompt_hash(), _lazy() (+7 more)

### Community 93 - "Prices Editor"
Cohesion: 0.16
Nodes (3): _num_text(), PricesEditor, ProvidersEditor

### Community 95 - "AuditMark"
Cohesion: 0.11
Nodes (9): AuditBar, all_correct_mark(), marked_count(), next_unmarked(), row_state(), AuditMark, test_audit_marking(), test_next_unmarked_wraps_and_waits_for_who_really_speaks() (+1 more)

### Community 98 - "Price Table Keys"
Cohesion: 0.15
Nodes (13): input, input_cached, output, input, input_cached, output, input, input_cached (+5 more)

### Community 99 - "Memory Config Keys"
Cohesion: 0.15
Nodes (13): memory, aliases_max, archive_after_absent, character_lifecycle, character_updates, correction_examples, description_max_chars, dream_max_lines (+5 more)

### Community 100 - "Series-1 series.yaml"
Cohesion: 0.15
Nodes (12): baseline, name, bench, baseline, non_dialogue, box_center_tolerance, box_height_tolerance, enabled (+4 more)

### Community 101 - "workspace/episodes.py"
Cohesion: 0.13
Nodes (7): sha256_bytes(), AddCandidate, detect_number(), fingerprint(), scan_paths(), test_detect_number(), test_fingerprint_reads_head_and_tail()

### Community 102 - "test_partial_review.py"
Cohesion: 0.15
Nodes (17): PartialSuggestion, partial_review(), suggest(), draft_path(), load_draft(), save_draft(), test_predeleted_lines_are_not_reviewer_edits(), _episode() (+9 more)

### Community 105 - "Series-1 OCR Config"
Cohesion: 0.18
Nodes (11): ocr, fragment_max_samples, fragment_merge_similarity, mask_image, mask_scale, merge_max_edit_distance, min_confidence, preprocess (+3 more)

### Community 106 - "Series-1 Script Review Config"
Cohesion: 0.18
Nodes (11): script_review, enabled, example_limit, max_remove_share, memory_auto_remove_min, memory_max_han, remove_confidence, repeat_merge_gap_ms (+3 more)

### Community 108 - "JobRunner"
Cohesion: 0.20
Nodes (3): JobRunner, test_run_panel_has_a_script_review_step(), __init__()

### Community 109 - "test_new_voices.py"
Cohesion: 0.15
Nodes (17): draft_voice_ids(), episode_character_ids(), is_auto_id(), is_unnamed(), load_new_voices(), review_voice_ids(), save_new_voices(), _approved() (+9 more)

### Community 110 - "sprite.py"
Cohesion: 0.17
Nodes (8): best_match(), candidates_for(), decide(), load_templates(), run(), frame_reader(), save_template(), atomic_write_json()

### Community 111 - "Translate Config"
Cohesion: 0.22
Nodes (9): translate, max_cps, max_line_chars, max_lines_per_event, max_retries, picture_evidence, picture_veto, pronoun_terms (+1 more)

### Community 112 - "measure.py"
Cohesion: 0.08
Nodes (35): freeze_finished(), _ask(), build_pipeline(), _interactive(), _output_exists(), _resolve_on_exists(), add_add(), add_batch() (+27 more)

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
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1024 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ReviewedLine` connect `ReviewedLine` to `test_app.py`, `App Package & Jobs`, `test_ocr_preprocess.py`, `Memory Manager Rows`, `bench/audit.py`, `test_feedback_loop.py`, `Memory Manager Tests`, `test_review_state.py`, `Benchmark Suite`, `CastLine`, `test_cast.py`, `Memory Store`, `test_suite.py`, `card.py`, `Services`, `conftest.py`, `Voice Learning & Evidence`, `core.py`, `._load_editor`, `render.py`, `ocr_benchmark.py`, `read_jsonl`, `Dreaming`, `character_updates.py`, `.probation`, `ReviewView`, `Briefings & Style Rules`, `kernel/__init__.py`, `Voice Learning Tests`, `test_probation.py`, `json`, `memory/__init__.py`, `runner.py`, `.episode_update`, `AuditMark`, `test_partial_review.py`, `test_new_voices.py`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ReviewedLine` (e.g. with `_finish()` and `test_pipeline_records_what_the_reviewer_removed_and_kept()`) actually correct?**
  _`ReviewedLine` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `subagent`, `Font draws 了 like digit 7`, `Show wording that looks like stray text (史 for 屎, 鸡道, 姬叔)` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `LLMClient` be split into smaller, more focused modules?**
  _Cohesion score 0.12873563218390804 - nodes in this community are weakly interconnected._
- **Why does `ReviewView` connect `ReviewView` to `test_app.py`, `AuditBar`, `App Package & Jobs`, `Memory Screen`, `Band & Cast Panel Views`, `NewCharacterDialog`, `._load_editor`, `test_review_state.py`, `Character Browser`, `Video Preview (mpv)`, `._show_card`, `.__init__`, `AuditMark`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Config` (e.g. with `fields()` and `value_at()`) actually correct?**
  _`Config` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `App Package & Jobs` be split into smaller, more focused modules?**
  _Cohesion score 0.06778846153846153 - nodes in this community are weakly interconnected._