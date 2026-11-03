# Graph Report - Subtitle-translator  (2026-11-03)

## Corpus Check
- 214 files · ~169,345 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .qm 2, .example 1)

## Summary
- 3316 nodes · 11388 edges · 137 communities (109 shown, 28 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 687 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `91fb64bd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Services
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
- workspace/series.py
- cast.py
- Video Preview (mpv)
- test_cast.py
- Memory Store
- conftest.py
- core.py
- LineHistory
- OCR Engine & Geometry
- Subtitle Style
- Pipeline Runner & Locks
- now_iso
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
- voice.py
- Bench Run Sandbox
- load_config
- Series-1 Voice Config
- ReviewView
- Band
- Series-1 Cast Config
- test_parser_stages.py
- load_config
- Architecture Guard Test
- ._load_editor
- Frame Selector Widget
- Pinned Requirements
- Briefings & Style Rules
- delivery.py
- Top-level Config Keys
- kernel/__init__.py
- Settings Schema Introspection
- NewCharacterDialog
- test_translate_review.py
- Memory Banks Writing
- LLM Provider Config
- probation.py
- SubtitleEvent
- Voice Learning Tests
- Render Config
- device.py
- prefix.py
- Memory & Translation Prompts
- DropTable
- ._field
- Tag Editor Widget
- read_jsonl
- Series-1 Band Config
- test_character_lifecycle.py
- runner.py
- .episode_update
- briefing_gen.py
- Flow Layout
- Prices Editor
- partial.py
- AuditBar
- Settings Form
- Price Table Keys
- Memory Config Keys
- Series-1 series.yaml
- Registry
- settings/__init__.py
- HistoryMixin
- benchmark.py
- Series-1 OCR Config
- Series-1 Script Review Config
- pinyin_gen.py
- JobRunner
- app/__main__.py
- sprite.py
- Translate Config
- measure.py
- symmetric_span
- migrate
- Background Workers
- ReviewedVerdict
- _bands
- Vietnamese UI Fill
- _style_key
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
- `review_counts()` --calls--> `needs_attention()`  [INFERRED]
  app/views/review_state.py → subagent/review/review.py
- `row_state()` --calls--> `needs_attention()`  [INFERRED]
  app/views/review_state.py → subagent/review/review.py
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

## Communities (137 total, 28 thin omitted)

### Community 1 - "make_llm"
Cohesion: 0.11
Nodes (13): BudgetExceeded, LLMCallError, LLMOutputError, compute_cost(), _daily_quota(), _describe(), LLMClient, _retryable() (+5 more)

### Community 2 - "App Package & Jobs"
Cohesion: 0.07
Nodes (10): agent_label(), error_message(), stage_label(), status_label(), ReviewData, choose_on_exists(), RunPanel, ClipPlayer (+2 more)

### Community 3 - "test_ocr_preprocess.py"
Cohesion: 0.14
Nodes (16): crop_view(), prepare(), subtitle_mask(), to_band_coords(), _band(), _box(), _event(), _gold() (+8 more)

### Community 4 - "Memory Screen"
Cohesion: 0.06
Nodes (8): EntryTable, _item(), MemoryView, done(), PairDialog, _same(), _update_text(), run_async()

### Community 5 - "Band & Cast Panel Views"
Cohesion: 0.07
Nodes (7): BandView, CastCanvas, CastPanel, ScaledImage, to_pixmap(), test_cast_panel_shows_boxes_and_records_corrections(), test_greyscale_images_can_be_shown()

### Community 6 - "ReviewedLine"
Cohesion: 0.10
Nodes (32): ReviewIncompleteError, PartialSuggestion, write_jsonl(), partial_review(), suggest(), draft_path(), finish_review(), flag_group() (+24 more)

### Community 7 - "Memory Manager Rows"
Cohesion: 0.18
Nodes (22): merge_proposals(), replaced_term(), reviewed_glossary(), CommitInfo, Conflict, describe_update(), dumps_aliases(), held_updates() (+14 more)

### Community 8 - "bench/audit.py"
Cohesion: 0.10
Nodes (33): auditable(), auditable_lines(), AuditReport, build_report(), disagreements(), draw_sample(), EpisodeAudit, gold_speakers() (+25 more)

### Community 9 - "test_feedback_loop.py"
Cohesion: 0.12
Nodes (28): OcrReading, user_json(), _reading(), _rubric(), evaluator(), test_a_passing_line_keeps_the_evaluators_suggestion_for_the_reviewer(), test_reading_speed_is_flagged_not_retried(), test_retry_sends_history_and_suggestion() (+20 more)

### Community 10 - "Memory Manager Tests"
Cohesion: 0.06
Nodes (65): candidates_for(), NewVoice, SpeakerCandidates, draft_voice_ids(), episode_character_ids(), is_auto_id(), is_unnamed(), load_new_voices() (+57 more)

### Community 12 - "test_review_state.py"
Cohesion: 0.12
Nodes (19): all_correct_mark(), line_matches(), LineFilter, marked_count(), next_npc_number(), next_pending(), next_unmarked(), review_counts() (+11 more)

### Community 13 - "models.py"
Cohesion: 0.12
Nodes (19): VideoInfo, Progress, mode_prompt(), register_episode(), test_mode_blocks_in_prompts(), test_turning_it_on_again_runs_the_stages(), calls(), _pipeline() (+11 more)

### Community 14 - "Benchmark Suite"
Cohesion: 0.08
Nodes (44): gold_lines(), align(), _approved(), _auto_pattern(), characters_at(), _decisions(), _events(), Gold (+36 more)

### Community 15 - "Config Schema"
Cohesion: 0.11
Nodes (28): AudioConfig, AuditConfig, BaselineConfig, BenchConfig, BudgetConfig, CastConfig, CleanupConfig, EpisodesConfig (+20 more)

### Community 16 - "test_pinyin_voice_windows.py"
Cohesion: 0.13
Nodes (13): Character, GlossaryEntry, LogEntry, VoiceEntry, _word_tokenizer(), build_windows(), run(), _engine() (+5 more)

### Community 17 - "workspace/series.py"
Cohesion: 0.14
Nodes (13): add_series(), cmd_series(), running_jobs(), JobRunningError, _blocks(), check_slug(), migrate(), _refuse_while_jobs_run() (+5 more)

### Community 18 - "cast.py"
Cohesion: 0.15
Nodes (12): _ffmpeg(), frame_path(), group_unknowns(), keep_boxes(), line_motion(), middle_frames(), motion_in_boxes(), _residual() (+4 more)

### Community 19 - "Video Preview (mpv)"
Cohesion: 0.07
Nodes (7): fmt_time(), load_mpv(), PreviewWidget, TimelineSlider, text(), _FakePlayer, test_preview_transport_controls()

### Community 20 - "test_cast.py"
Cohesion: 0.07
Nodes (33): gold_boxes(), _apply_labels(), apply_review_edits(), _check_talkers(), learn_sprites(), _name_unknowns(), plan(), _Plan (+25 more)

### Community 21 - "Memory Store"
Cohesion: 0.07
Nodes (17): _alias_zh(), check(), _clip(), _pairs_block(), _present_block(), propose(), glossary_zh_block(), new_voices_block() (+9 more)

### Community 22 - "conftest.py"
Cohesion: 0.12
Nodes (5): EditRecord, FakeClient, FakeCompletions, _setup(), test_existing_rules_are_not_reproposed_and_terms_go_to_the_glossary()

### Community 23 - "core.py"
Cohesion: 0.08
Nodes (26): card_info(), card_media(), CharacterCard, confirmed_box(), _cut_clip(), _cut_picture(), _episode_ids(), _frame() (+18 more)

### Community 24 - "LineHistory"
Cohesion: 0.11
Nodes (7): loaded(), opened(), LineHistory, _Clock, test_steps_are_per_line_and_copies(), test_typing_in_one_field_is_one_undo_step(), test_undo_and_redo_restore_the_line_and_break_the_merge()

### Community 25 - "OCR Engine & Geometry"
Cohesion: 0.12
Nodes (13): onnx_use_cuda(), OcrBox, keep_cjk(), create_engine(), _engine_key(), filter_boxes(), get_engine(), group_rows() (+5 more)

### Community 26 - "Subtitle Style"
Cohesion: 0.14
Nodes (18): calibrate(), grow_line(), labels_near(), load_style(), propose_regions(), _region_features(), save_style(), segment_mask() (+10 more)

### Community 27 - "Pipeline Runner & Locks"
Cohesion: 0.13
Nodes (5): _pct(), write_report(), BatchItem, _episode_log, Pipeline

### Community 28 - "now_iso"
Cohesion: 0.18
Nodes (4): atomic_write_json(), now_iso(), read_json(), UpdatesMixin

### Community 29 - "Episodes Screen"
Cohesion: 0.11
Nodes (5): choose_batch_on_exists(), job_busy(), AddDialog, EpisodesView, done()

### Community 30 - "Memory Proposals Apply"
Cohesion: 0.19
Nodes (6): MemoryProposal, atomic_write_text(), ApplyMixin, ApplyResult, test_a_different_suggestion_for_the_same_term_still_comes_through(), gloss()

### Community 31 - "render.py"
Cohesion: 0.29
Nodes (10): check_fonts(), choose_encoder(), encoder_args(), ffmpeg_args(), font_files(), preview_ass(), render(), _run_ffmpeg() (+2 more)

### Community 32 - "Voice Learning & Evidence"
Cohesion: 0.08
Nodes (30): trusted_speakers(), is_auto_episode(), trusted_auto_lines(), usable_line(), _voices(), Config, auto_clips(), auto_gate() (+22 more)

### Community 33 - "core.py"
Cohesion: 0.14
Nodes (17): save_clip(), available_encoders(), extract_clip(), extract_frame(), git(), has_video_stream(), imread(), iter_gray_frames() (+9 more)

### Community 34 - "Audit & Dreaming Screens"
Cohesion: 0.09
Nodes (5): AuditView, done(), DreamingView, _summary(), show_error()

### Community 35 - "Settings & Run Panel"
Cohesion: 0.10
Nodes (5): label(), reset_all(), save(), sequence(), SettingsView

### Community 36 - "Script Review & OCR Fix"
Cohesion: 0.08
Nodes (31): script_note(), ScriptDecision, edit_distance(), is_han(), normalize_zh(), relatedness(), LineDecision, apply_script_review() (+23 more)

### Community 37 - "Frozen Baseline"
Cohesion: 0.12
Nodes (18): baseline_dir(), complete(), freeze(), freeze_episode(), freeze_finished(), _git_head(), _manifest(), memory_at_run() (+10 more)

### Community 38 - "Bootstrap Seed"
Cohesion: 0.08
Nodes (26): load(), approve_seed(), _episode1_lines(), generate_seed(), load_seed(), name_pinyin(), save_seed(), seed_path() (+18 more)

### Community 39 - "YAML Comment-Preserving Edit"
Cohesion: 0.14
Nodes (17): file_comment(), _block_end(), delete_key(), _dump(), _find(), _get(), _is_child(), _path() (+9 more)

### Community 40 - "._load_editor"
Cohesion: 0.18
Nodes (4): flag_label(), _bullets(), show(), _section()

### Community 41 - "test_render_delivery.py"
Cohesion: 0.17
Nodes (6): _ass_text(), build_ass(), _color(), Layout, _style(), test_long_pinyin_shrinks_then_wraps()

### Community 42 - "ocr_benchmark.py"
Cohesion: 0.12
Nodes (16): _covered(), EpisodeOcrScore, _existing_events(), load_key(), _norm(), ocr_episodes(), OcrBenchResult, _overlap() (+8 more)

### Community 43 - "Episode"
Cohesion: 0.09
Nodes (14): SourceMissingError, Episode, AddCandidate, derived_status(), fingerprint(), add(), scan_paths(), test_add_register_duplicates_and_numbers() (+6 more)

### Community 44 - "read_jsonl"
Cohesion: 0.18
Nodes (17): _mark_talking(), run(), run(), frame_reader(), run(), _review_run(), run(), EpisodeContext (+9 more)

### Community 45 - "Ingest & Change Detection"
Cohesion: 0.14
Nodes (22): imwrite_png(), ChangeRecord, binarize(), calibrate(), Change, change_fraction(), detect_changes(), draw_band() (+14 more)

### Community 46 - "Character Browser"
Cohesion: 0.13
Nodes (4): CharacterBrowser, CharacterStrip, describe(), _pixmap()

### Community 47 - "Runner"
Cohesion: 0.35
Nodes (3): Runner, StageDef, ocr_hash()

### Community 48 - "memory/__init__.py"
Cohesion: 0.09
Nodes (18): Evaluation, Window, judge(), llm_rubric(), rubric_payload(), RubricLine, RubricResponse, RuleFailure (+10 more)

### Community 49 - "Dreaming"
Cohesion: 0.09
Nodes (27): apply_dream(), approved_lines(), describe(), done_episodes(), dream(), _dream_variable(), DreamGlossary, DreamItem (+19 more)

### Community 50 - "character_updates.py"
Cohesion: 0.15
Nodes (8): contains_term(), CharacterChange, CharacterUpdateResponse, _has_word(), _introduces(), _positions(), PronounUse, detect_number()

### Community 51 - ".probation"
Cohesion: 0.12
Nodes (5): load_line_voices(), CandidatesMixin, _Run, speaker_lines(), episode_number()

### Community 52 - "New Series Dialog"
Cohesion: 0.11
Nodes (5): NewSeriesDialog, StyleDialog, test_new_series_dialog_asks_for_the_default_pronoun_pair(), test_new_series_dialog_creates_a_translation_style(), test_new_series_work_folder_can_be_chosen()

### Community 53 - "._show_card"
Cohesion: 0.15
Nodes (6): done(), failed(), done(), done(), failed(), done()

### Community 54 - "voice.py"
Cohesion: 0.16
Nodes (6): ModelUnavailableError, write_silence(), load_audio_any(), load_wav(), test_finish_review_never_fails_on_missing_voice_model(), boom()

### Community 55 - "Bench Run Sandbox"
Cohesion: 0.12
Nodes (16): checkout_memory(), _drop_heavy(), _frozen_inputs(), _install_review(), _null(), _rerun_episode(), run(), _run_info() (+8 more)

### Community 56 - "load_config"
Cohesion: 0.16
Nodes (16): MemoryLockedError, StageError, SubagentError, check_id(), list_registers(), load_register(), _parse(), Register (+8 more)

### Community 57 - "Series-1 Voice Config"
Cohesion: 0.08
Nodes (24): voice, accept_score, confusable_similarity, learn_auto_allowed_flags, learn_auto_max_drop, learn_auto_min_margin, learn_auto_min_score, learn_auto_min_test_lines (+16 more)

### Community 59 - "Band"
Cohesion: 0.20
Nodes (3): center_in_band(), Band, test_band_pixels_are_even_and_inside_frame()

### Community 60 - "Series-1 Cast Config"
Cohesion: 0.09
Nodes (23): cast, add_similarity, detector_model, embed_model, enabled, frame_width, learn, match_margin (+15 more)

### Community 61 - "test_parser_stages.py"
Cohesion: 0.13
Nodes (19): absorb_fragments(), build_events(), flag_non_dialogue(), frames_on_screen(), _Group, group_readings(), _median(), _merge_flicker() (+11 more)

### Community 62 - "load_config"
Cohesion: 0.11
Nodes (18): build_parser(), main(), _setup_logging(), prompt_hash(), load_config(), _load_env(), add(), project() (+10 more)

### Community 63 - "Architecture Guard Test"
Cohesion: 0.17
Nodes (8): _breaches(), _imports(), _module_of(), _submodules(), test_every_package_is_a_known_module_with_a_public_api(), test_modules_import_each_other_only_through_their_api_and_downwards(), test_the_app_reaches_the_core_only_through_its_services(), test_the_core_never_imports_the_app_or_qt()

### Community 66 - "Pinned Requirements"
Cohesion: 0.10
Nodes (20): jieba 0.42.1, numpy 2.5.3, onnxruntime-gpu 1.30.0, openai 3.22.1, opencv-python-headless 5.0.0.93, pillow 12.3.0, pydantic 2.13.5, pypinyin 0.55.0 (+12 more)

### Community 67 - "Briefings & Style Rules"
Cohesion: 0.21
Nodes (12): briefings_dir(), cap_style_rules(), IndexEntry, list_episode_briefings(), _read(), read_index(), read_story(), read_style_rules() (+4 more)

### Community 68 - "delivery.py"
Cohesion: 0.12
Nodes (22): OutputExistsError, OutputFolderError, _atomic_write(), _replace_with_retry(), deliver(), keep_both_path(), output_folder(), output_name() (+14 more)

### Community 69 - "Top-level Config Keys"
Cohesion: 0.10
Nodes (19): budget, max_cost_per_episode, cleanup, auto, device, episodes, number_patterns, video_extensions (+11 more)

### Community 70 - "kernel/__init__.py"
Cohesion: 0.12
Nodes (9): EpisodeLockedError, balanced_wrap(), split_explicit_lines(), visible_chars(), wrap_words(), FileLock, lock_holder(), pid_alive() (+1 more)

### Community 71 - "Settings Schema Introspection"
Cohesion: 0.11
Nodes (11): EpisodeNotFoundError, add(), _code_notes(), fields(), walk(), FieldSpec, known_sets(), _unwrap() (+3 more)

### Community 72 - "NewCharacterDialog"
Cohesion: 0.15
Nodes (6): character_proposals(), NewCharacterDialog, done(), save(), load(), episode_id()

### Community 73 - "test_translate_review.py"
Cohesion: 0.12
Nodes (12): check(), new_voice_id(), regenerate_pinyin(), rule_checks(), RuleContext, _line(), rules(), test_glossary_rule_matches_whole_words_only() (+4 more)

### Community 74 - "Memory Banks Writing"
Cohesion: 0.14
Nodes (6): _add_exemplars(), BanksMixin, _drop_exemplar(), _keep_best(), _record_votes(), _undo_episode()

### Community 75 - "LLM Provider Config"
Cohesion: 0.11
Nodes (18): api_key_env, base_url, model, llm, max_retries, max_retry_wait_s, providers, temperature (+10 more)

### Community 76 - "probation.py"
Cohesion: 0.18
Nodes (5): candidate_looks(), candidate_voice(), check_return(), ReturnCheck, _unit()

### Community 77 - "SubtitleEvent"
Cohesion: 0.17
Nodes (12): SubtitleEvent, chunked(), ocr_fix_prefix(), crop_path(), apply_fixes(), batch_payload(), OcrFixChange, OcrFixResponse (+4 more)

### Community 78 - "Voice Learning Tests"
Cohesion: 0.28
Nodes (10): _auto_episode(), _episode(), _fake_embed(), test_auto_lines_pass_only_when_every_signal_agrees(), test_auto_lines_that_hurt_accuracy_are_not_learned(), test_auto_lines_that_keep_accuracy_are_learned(), test_auto_lines_wait_until_there_is_enough_to_measure(), test_learn_writes_bank_and_evaluate_reports_accuracy() (+2 more)

### Community 79 - "Render Config"
Cohesion: 0.12
Nodes (17): render, avg_char_width, blur_radius, encoder, font_dir, font_name, line_spacing, mask (+9 more)

### Community 80 - "device.py"
Cohesion: 0.13
Nodes (6): add_check(), cmd_check(), describe(), onnx_cuda_available(), torch_cuda_available(), torch_device()

### Community 81 - "prefix.py"
Cohesion: 0.29
Nodes (8): corrections_block(), evaluator_prefix(), glossary_block(), pronoun_block(), reviewer_corrections(), story_block(), style_block(), translator_prefix()

### Community 82 - "Memory & Translation Prompts"
Cohesion: 0.19
Nodes (8): Style rules, Cổ trang / tiên hiệp register (Hán-Việt terms), identify / default_pair template toggle, Memory proposals (glossary / pronoun_pair / character), Pronoun matrix, Retries with earlier_attempts and evaluator_suggestion, Reviewer corrections, Speaker rules per voice status (fixed/confusable/disputed/new_voice/unknown/too_short)

### Community 84 - "._field"
Cohesion: 0.25
Nodes (3): _decimals(), Field, set_float()

### Community 86 - "read_jsonl"
Cohesion: 0.13
Nodes (24): CostRecord, read_jsonl(), build_messages(), missing_prices(), record_cost(), _server_delay(), collect_metrics(), episode_status() (+16 more)

### Community 87 - "Series-1 Band Config"
Cohesion: 0.13
Nodes (15): bottom, left, right, top, video, band_frames, change_threshold, empty_text_ratio (+7 more)

### Community 88 - "test_character_lifecycle.py"
Cohesion: 0.36
Nodes (13): characters_block(), _lines(), _setup(), _status(), test_archived_voices_are_not_matched(), test_consecutive_episodes_keep_a_character(), test_first_run_counts_earlier_episodes(), test_generic_characters_are_never_matched_or_learned() (+5 more)

### Community 89 - "runner.py"
Cohesion: 0.11
Nodes (14): _learn(), EpisodeState, StageState, cleanup(), counts_text(), _lazy(), review_outputs(), _source_key() (+6 more)

### Community 91 - "briefing_gen.py"
Cohesion: 0.27
Nodes (8): load_prompt(), BriefingResponse, CharacterFate, compress_story(), generate_briefing(), script_text(), StoryResponse, word_count()

### Community 93 - "Prices Editor"
Cohesion: 0.16
Nodes (3): _num_text(), PricesEditor, ProvidersEditor

### Community 94 - "partial.py"
Cohesion: 0.12
Nodes (8): build_bank(), CastEngine, get_engine(), match(), _recognise(), PartialResult, _session_bank(), _sprites()

### Community 98 - "Price Table Keys"
Cohesion: 0.15
Nodes (13): input, input_cached, output, input, input_cached, output, input, input_cached (+5 more)

### Community 99 - "Memory Config Keys"
Cohesion: 0.15
Nodes (13): memory, aliases_max, archive_after_absent, character_lifecycle, character_updates, correction_examples, description_max_chars, dream_max_lines (+5 more)

### Community 100 - "Series-1 series.yaml"
Cohesion: 0.15
Nodes (12): baseline, name, bench, baseline, non_dialogue, box_center_tolerance, box_height_tolerance, enabled (+4 more)

### Community 101 - "Registry"
Cohesion: 0.19
Nodes (24): MainWindow, validate(), LineTranslation, PinyinLine, Registry, sample_events(), write_events(), qapp() (+16 more)

### Community 102 - "settings/__init__.py"
Cohesion: 0.12
Nodes (14): ConfigError, active_series(), find_root(), list_series(), merge_sections(), parse_config(), _read_yaml(), save_config_text() (+6 more)

### Community 104 - "benchmark.py"
Cohesion: 0.14
Nodes (13): _acc(), benchmark_episodes(), BenchmarkResult, _copy_reviewer_context(), _drop_heavy_files(), EpisodeScore, render(), run_benchmark() (+5 more)

### Community 105 - "Series-1 OCR Config"
Cohesion: 0.18
Nodes (11): ocr, fragment_max_samples, fragment_merge_similarity, mask_image, mask_scale, merge_max_edit_distance, min_confidence, preprocess (+3 more)

### Community 106 - "Series-1 Script Review Config"
Cohesion: 0.18
Nodes (11): script_review, enabled, example_limit, max_remove_share, memory_auto_remove_min, memory_max_han, remove_confidence, repeat_merge_gap_ms (+3 more)

### Community 107 - "pinyin_gen.py"
Cohesion: 0.19
Nodes (8): nfc(), heteronyms(), PinyinEngine, PolyphoneChoice, PolyphoneResponse, resolve_polyphones(), run(), Token

### Community 108 - "JobRunner"
Cohesion: 0.20
Nodes (3): JobRunner, test_run_panel_has_a_script_review_step(), __init__()

### Community 109 - "app/__main__.py"
Cohesion: 0.27
Nodes (4): choose_platform(), install_fonts(), install_translator(), main()

### Community 110 - "sprite.py"
Cohesion: 0.24
Nodes (4): best_match(), decide(), load_templates(), save_template()

### Community 111 - "Translate Config"
Cohesion: 0.22
Nodes (9): translate, max_cps, max_line_chars, max_lines_per_event, max_retries, picture_evidence, picture_veto, pronoun_terms (+1 more)

### Community 112 - "measure.py"
Cohesion: 0.11
Nodes (32): _ask(), build_pipeline(), _interactive(), _output_exists(), _resolve_on_exists(), add_add(), add_batch(), add_calibrate() (+24 more)

### Community 113 - "symmetric_span"
Cohesion: 0.25
Nodes (3): line_span(), symmetric_span(), test_symmetric_span_trims_the_far_side_beyond_half_a_line()

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
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1027 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ReviewedLine` connect `test_cast.py` to `Services`, `App Package & Jobs`, `test_ocr_preprocess.py`, `ReviewedLine`, `Memory Manager Rows`, `bench/audit.py`, `test_feedback_loop.py`, `Memory Manager Tests`, `test_review_state.py`, `Benchmark Suite`, `Memory Store`, `conftest.py`, `core.py`, `LineHistory`, `now_iso`, `render.py`, `Voice Learning & Evidence`, `Script Review & OCR Fix`, `._load_editor`, `test_render_delivery.py`, `ocr_benchmark.py`, `memory/__init__.py`, `Dreaming`, `character_updates.py`, `.probation`, `ReviewView`, `._load_editor`, `Briefings & Style Rules`, `delivery.py`, `kernel/__init__.py`, `test_translate_review.py`, `probation.py`, `Voice Learning Tests`, `prefix.py`, `read_jsonl`, `test_character_lifecycle.py`, `runner.py`, `.episode_update`, `briefing_gen.py`, `partial.py`, `AuditBar`, `Registry`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ReviewedLine` (e.g. with `_finish()` and `test_pipeline_records_what_the_reviewer_removed_and_kept()`) actually correct?**
  _`ReviewedLine` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `subagent`, `Font draws 了 like digit 7`, `Show wording that looks like stray text (史 for 屎, 鸡道, 姬叔)` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Services` be split into smaller, more focused modules?**
  _Cohesion score 0.07781649245063879 - nodes in this community are weakly interconnected._
- **Why does `Config` connect `Voice Learning & Evidence` to `make_llm`, `ReviewedLine`, `Memory Manager Rows`, `bench/audit.py`, `Memory Manager Tests`, `models.py`, `Benchmark Suite`, `Config Schema`, `cast.py`, `test_cast.py`, `Memory Store`, `conftest.py`, `core.py`, `OCR Engine & Geometry`, `now_iso`, `render.py`, `core.py`, `Frozen Baseline`, `Bootstrap Seed`, `test_render_delivery.py`, `ocr_benchmark.py`, `Episode`, `memory/__init__.py`, `Dreaming`, `character_updates.py`, `voice.py`, `Bench Run Sandbox`, `load_config`, `test_parser_stages.py`, `load_config`, `delivery.py`, `Settings Schema Introspection`, `SubtitleEvent`, `device.py`, `read_jsonl`, `runner.py`, `briefing_gen.py`, `partial.py`, `settings/__init__.py`, `benchmark.py`, `pinyin_gen.py`, `measure.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Config` (e.g. with `fields()` and `value_at()`) actually correct?**
  _`Config` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `make_llm` be split into smaller, more focused modules?**
  _Cohesion score 0.112375533428165 - nodes in this community are weakly interconnected._