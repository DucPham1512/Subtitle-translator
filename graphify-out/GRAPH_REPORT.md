# Graph Report - Subtitle-translator  (2026-11-03)

## Corpus Check
- 214 files · ~168,879 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .qm 2, .example 1)

## Summary
- 3296 nodes · 11336 edges · 138 communities (109 shown, 29 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 687 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `573cf3b5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_app.py
- client.py
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
- test_review_state.py
- models.py
- Benchmark Suite
- Config Schema
- workspace/__init__.py
- Series Management
- Cast Engine
- Video Preview (mpv)
- test_cast.py
- Memory Store
- test_suite.py
- test_character_card.py
- Services
- OCR Engine & Geometry
- Subtitle Style
- Pipeline Runner & Locks
- conftest.py
- Episodes Screen
- Memory Proposals Apply
- runner.py
- Voice Learning & Evidence
- Media (ffmpeg) Infra
- Audit & Dreaming Screens
- Settings & Run Panel
- Script Review & OCR Fix
- Frozen Baseline
- Bootstrap Seed
- YAML Comment-Preserving Edit
- ReviewView
- build_ass
- ocr_benchmark.py
- Episode
- read_jsonl
- Ingest & Change Detection
- Character Browser
- make_llm
- memory/__init__.py
- Dreaming
- character_updates.py
- Voice Candidates
- New Series Dialog
- memory/__init__.py
- Voice Match
- Bench Run Sandbox
- load_config
- Series-1 Voice Config
- ._loaded
- partial.py
- Series-1 Cast Config
- test_parser_stages.py
- Paths
- Architecture Guard Test
- pytest
- Frame Selector Widget
- Pinned Requirements
- Briefings & Style Rules
- NewCharacterDialog
- Top-level Config Keys
- kernel/__init__.py
- Settings Schema Introspection
- ._show_card
- rule_checks
- Memory Banks Writing
- LLM Provider Config
- test_pinyin_voice_windows.py
- pinyin_gen.py
- Voice Learning Tests
- Render Config
- test_probation.py
- numpy
- Memory & Translation Prompts
- SubtitleEvent
- ._field
- Tag Editor Widget
- test_bootstrap_dream_cli.py
- Series-1 Band Config
- test_character_lifecycle.py
- Runner
- .episode_update
- LineHistory
- Flow Layout
- Prices Editor
- render.py
- AuditBar
- Settings Form
- Price Table Keys
- Memory Config Keys
- Series-1 series.yaml
- DropTable
- test_partial_review.py
- Device Detection
- json
- Series-1 OCR Config
- Series-1 Script Review Config
- HistoryMixin
- JobRunner
- test_new_voices.py
- sprite.py
- Translate Config
- measure.py
- textutil.py
- rules
- Background Workers
- _no_real_ffmpeg
- migrate
- Vietnamese UI Fill
- _lazy
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
1. `ReviewedLine` - 156 edges
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

## Communities (138 total, 29 thin omitted)

### Community 0 - "test_app.py"
Cohesion: 0.13
Nodes (27): MainWindow, LineTranslation, PinyinLine, write_jsonl(), gate(), register_episode(), qapp(), settle() (+19 more)

### Community 1 - "client.py"
Cohesion: 0.12
Nodes (12): LLMCallError, compute_cost(), _daily_quota(), _describe(), LLMClient, _retryable(), schema_instruction(), _server_delay() (+4 more)

### Community 2 - "App Package & Jobs"
Cohesion: 0.07
Nodes (11): choose_platform(), install_fonts(), install_translator(), main(), agent_label(), error_message(), flag_label(), stage_label() (+3 more)

### Community 3 - "test_ocr_preprocess.py"
Cohesion: 0.13
Nodes (16): crop_view(), prepare(), save_sample(), subtitle_mask(), to_band_coords(), _band(), _box(), _event() (+8 more)

### Community 4 - "Memory Screen"
Cohesion: 0.06
Nodes (7): EntryTable, _item(), MemoryView, PairDialog, _same(), _update_text(), run_async()

### Community 5 - "Band & Cast Panel Views"
Cohesion: 0.06
Nodes (9): BandView, CastCanvas, CastPanel, ScaledImage, to_pixmap(), done(), failed(), test_cast_panel_shows_boxes_and_records_corrections() (+1 more)

### Community 6 - "partial.py"
Cohesion: 0.09
Nodes (29): row_state(), ReviewIncompleteError, ReviewedLine, apply_script_review(), build_draft(), compute_edits(), draft_path(), finish_review() (+21 more)

### Community 7 - "Memory Manager Rows"
Cohesion: 0.19
Nodes (21): merge_proposals(), replaced_term(), reviewed_glossary(), CommitInfo, Conflict, describe_update(), held_updates(), MemoryDiff (+13 more)

### Community 8 - "test_audit.py"
Cohesion: 0.08
Nodes (40): auditable(), auditable_lines(), AuditReport, build_report(), disagreements(), draw_sample(), EpisodeAudit, gold_speakers() (+32 more)

### Community 9 - "test_feedback_loop.py"
Cohesion: 0.12
Nodes (29): read_jsonl(), mode_prompt(), run(), user_json(), _rubric(), evaluator(), test_a_passing_line_keeps_the_evaluators_suggestion_for_the_reviewer(), test_reading_speed_is_flagged_not_retried() (+21 more)

### Community 10 - "Memory Manager Tests"
Cohesion: 0.12
Nodes (31): MemoryManager, save_line_voices(), seed_memory(), _line(), _llm(), _npc(), test_a_candidate_keeps_its_updates_when_promoted(), finish() (+23 more)

### Community 12 - "test_review_state.py"
Cohesion: 0.13
Nodes (17): all_correct_mark(), line_matches(), LineFilter, marked_count(), next_npc_number(), next_pending(), next_unmarked(), review_counts() (+9 more)

### Community 13 - "models.py"
Cohesion: 0.09
Nodes (20): AuditSample, ChangeRecord, EditRecord, PartialSuggestion, VideoInfo, Window, Progress, test_turning_it_on_again_runs_the_stages() (+12 more)

### Community 14 - "Benchmark Suite"
Cohesion: 0.11
Nodes (36): align(), _approved(), _auto_pattern(), characters_at(), _decisions(), _events(), Gold, headline() (+28 more)

### Community 15 - "Config Schema"
Cohesion: 0.08
Nodes (31): center_in_band(), AudioConfig, AuditConfig, Band, BaselineConfig, BenchConfig, BudgetConfig, CleanupConfig (+23 more)

### Community 16 - "workspace/__init__.py"
Cohesion: 0.11
Nodes (20): OutputExistsError, OutputFolderError, cleanup(), deliver(), keep_both_path(), output_folder(), output_name(), resolve_conflict() (+12 more)

### Community 17 - "Series Management"
Cohesion: 0.13
Nodes (20): add_series(), cmd_series(), JobRunningError, StageError, SubagentError, keep(), add(), add() (+12 more)

### Community 18 - "Cast Engine"
Cohesion: 0.08
Nodes (23): CastEngine, crop(), _ffmpeg(), frame_path(), frame_time_ms(), get_engine(), group_unknowns(), keep_boxes() (+15 more)

### Community 19 - "Video Preview (mpv)"
Cohesion: 0.07
Nodes (7): fmt_time(), load_mpv(), PreviewWidget, TimelineSlider, text(), _FakePlayer, test_preview_transport_controls()

### Community 20 - "test_cast.py"
Cohesion: 0.10
Nodes (23): _apply_labels(), apply_review_edits(), _check_talkers(), learn_sprites(), _name_unknowns(), plan(), _Plan, SpriteLearnResult (+15 more)

### Community 21 - "Memory Store"
Cohesion: 0.08
Nodes (15): card_info(), _pairs_block(), _present_block(), glossary_zh_block(), new_voices_block(), ocr_fix_prefix(), GlossaryEntry, LogEntry (+7 more)

### Community 22 - "test_suite.py"
Cohesion: 0.19
Nodes (8): group_map(), mapping(), CastBoxEdit, _line(), make_baseline(), test_cast_gold_follows_the_review_edits(), test_group_map_is_one_to_one_by_shared_lines(), test_translation_and_evaluator_scores()

### Community 23 - "test_character_card.py"
Cohesion: 0.13
Nodes (16): gold_boxes(), confirmed_box(), shown_talking_box(), CastDetection, CastLine, picture_veto(), test_picture_veto_disputes_the_voice(), line() (+8 more)

### Community 24 - "Services"
Cohesion: 0.07
Nodes (6): EpisodeRow, ReviewData, script_note(), Services, test_run_panel_has_a_script_review_step(), __init__()

### Community 25 - "OCR Engine & Geometry"
Cohesion: 0.08
Nodes (16): OcrBox, keep_cjk(), line_span(), symmetric_span(), create_engine(), crop_path(), _engine_key(), filter_boxes() (+8 more)

### Community 26 - "Subtitle Style"
Cohesion: 0.11
Nodes (19): calibrate(), grow_line(), labels_near(), load_style(), propose_regions(), _region_features(), save_style(), segment_mask() (+11 more)

### Community 27 - "Pipeline Runner & Locks"
Cohesion: 0.11
Nodes (7): _learn(), job_lock(), StageState, hash_path(), sha256_json(), _episode_log, Pipeline

### Community 28 - "conftest.py"
Cohesion: 0.12
Nodes (9): SourceMissingError, Episode, sha256_bytes(), detect_number(), fingerprint(), FakeClient, FakeCompletions, test_detect_number() (+1 more)

### Community 29 - "Episodes Screen"
Cohesion: 0.10
Nodes (7): choose_batch_on_exists(), choose_on_exists(), job_busy(), AddDialog, EpisodesView, done(), confirm()

### Community 30 - "Memory Proposals Apply"
Cohesion: 0.21
Nodes (4): MemoryProposal, now_iso(), ApplyMixin, ApplyResult

### Community 31 - "runner.py"
Cohesion: 0.16
Nodes (6): counts_text(), _pct(), write_report(), BatchItem, review_outputs(), run_stage()

### Community 32 - "Voice Learning & Evidence"
Cohesion: 0.14
Nodes (18): Config, auto_clips(), auto_gate(), AutoGate, build_centroids(), Clip, embed_clips(), episode_samples() (+10 more)

### Community 33 - "Media (ffmpeg) Infra"
Cohesion: 0.17
Nodes (17): available_encoders(), extract_clip(), extract_frame(), git(), has_video_stream(), imread(), imwrite_png(), iter_gray_frames() (+9 more)

### Community 34 - "Audit & Dreaming Screens"
Cohesion: 0.07
Nodes (13): AuditView, done(), character_proposals(), DreamingView, _summary(), done(), done(), save() (+5 more)

### Community 35 - "Settings & Run Panel"
Cohesion: 0.09
Nodes (5): label(), reset_all(), save(), sequence(), SettingsView

### Community 36 - "Script Review & OCR Fix"
Cohesion: 0.09
Nodes (26): ScriptDecision, edit_distance(), normalize_zh(), relatedness(), LineDecision, examples_block(), find_repeats(), han_count() (+18 more)

### Community 37 - "Frozen Baseline"
Cohesion: 0.17
Nodes (13): baseline_dir(), complete(), freeze(), freeze_episode(), freeze_finished(), _git_head(), _manifest(), memory_at_run() (+5 more)

### Community 38 - "Bootstrap Seed"
Cohesion: 0.10
Nodes (22): approve_seed(), _episode1_lines(), generate_seed(), load_seed(), name_pinyin(), save_clip(), save_seed(), seed_path() (+14 more)

### Community 39 - "YAML Comment-Preserving Edit"
Cohesion: 0.14
Nodes (17): file_comment(), _block_end(), delete_key(), _dump(), _find(), _get(), _is_child(), _path() (+9 more)

### Community 41 - "build_ass"
Cohesion: 0.15
Nodes (10): build_ass(), _color(), Layout, _style(), _line(), test_ass_has_two_events_per_line_with_same_timing(), test_deleted_lines_are_not_rendered(), test_font_sizes_scale_with_height() (+2 more)

### Community 42 - "ocr_benchmark.py"
Cohesion: 0.11
Nodes (17): _sandbox_paths(), _covered(), EpisodeOcrScore, _existing_events(), gold_lines(), load_key(), _norm(), ocr_episodes() (+9 more)

### Community 43 - "Episode"
Cohesion: 0.11
Nodes (13): add_add(), add_status(), cmd_add(), cmd_status(), AddCandidate, derived_status(), Registry, scan_paths() (+5 more)

### Community 44 - "read_jsonl"
Cohesion: 0.18
Nodes (23): frame_reader(), SpeakerCandidates, run(), render(), _review_run(), _source_key(), run(), run() (+15 more)

### Community 45 - "Ingest & Change Detection"
Cohesion: 0.16
Nodes (20): binarize(), calibrate(), Change, change_fraction(), detect_changes(), draw_band(), fuse(), has_subtitle() (+12 more)

### Community 46 - "Character Browser"
Cohesion: 0.11
Nodes (5): CharacterBrowser, CharacterStrip, describe(), _pixmap(), ClipPlayer

### Community 47 - "make_llm"
Cohesion: 0.17
Nodes (22): CostRecord, build_messages(), missing_prices(), record_cost(), collect_metrics(), episode_status(), make_llm(), test_each_call_records_its_agent() (+14 more)

### Community 48 - "memory/__init__.py"
Cohesion: 0.10
Nodes (16): Evaluation, judge(), llm_rubric(), rubric_payload(), RubricLine, RubricResponse, RuleFailure, _best() (+8 more)

### Community 49 - "Dreaming"
Cohesion: 0.09
Nodes (33): contains_term(), apply_dream(), describe(), dream(), DreamGlossary, DreamItem, DreamOutput, DreamPronoun (+25 more)

### Community 50 - "character_updates.py"
Cohesion: 0.18
Nodes (12): _alias_zh(), CharacterChange, CharacterUpdateResponse, check(), _clip(), _has_word(), _introduces(), _positions() (+4 more)

### Community 51 - "Voice Candidates"
Cohesion: 0.12
Nodes (5): load_line_voices(), CandidatesMixin, _Run, speaker_lines(), episode_number()

### Community 52 - "New Series Dialog"
Cohesion: 0.13
Nodes (5): NewSeriesDialog, StyleDialog, test_new_series_dialog_asks_for_the_default_pronoun_pair(), test_new_series_dialog_creates_a_translation_style(), test_new_series_work_folder_can_be_chosen()

### Community 53 - "memory/__init__.py"
Cohesion: 0.14
Nodes (6): trusted_speakers(), is_auto_episode(), trusted_auto_lines(), usable_line(), corrections_block(), reviewer_corrections()

### Community 54 - "Voice Match"
Cohesion: 0.15
Nodes (15): load(), new_voice_id(), all_similarities(), classify(), Embedder, find_new_voices(), group_voices(), l2_normalize() (+7 more)

### Community 55 - "Bench Run Sandbox"
Cohesion: 0.16
Nodes (13): checkout_memory(), _drop_heavy(), _frozen_inputs(), _install_review(), _null(), _rerun_episode(), run(), _run_info() (+5 more)

### Community 56 - "load_config"
Cohesion: 0.16
Nodes (17): prompt_hash(), load_config(), _load_env(), check_id(), list_registers(), load_register(), _parse(), Register (+9 more)

### Community 57 - "Series-1 Voice Config"
Cohesion: 0.08
Nodes (24): voice, accept_score, confusable_similarity, learn_auto_allowed_flags, learn_auto_max_drop, learn_auto_min_margin, learn_auto_min_score, learn_auto_min_test_lines (+16 more)

### Community 59 - "partial.py"
Cohesion: 0.14
Nodes (11): build_bank(), frame_embedder(), job_lock_path(), approved_lines(), done_episodes(), new_edits(), partial_review(), PartialResult (+3 more)

### Community 60 - "Series-1 Cast Config"
Cohesion: 0.09
Nodes (23): cast, add_similarity, detector_model, embed_model, enabled, frame_width, learn, match_margin (+15 more)

### Community 61 - "test_parser_stages.py"
Cohesion: 0.12
Nodes (22): OcrReading, absorb_fragments(), build_events(), flag_non_dialogue(), frames_on_screen(), _Group, group_readings(), _median() (+14 more)

### Community 62 - "Paths"
Cohesion: 0.20
Nodes (8): card_media(), CharacterCard, _cut_clip(), _cut_picture(), _frame(), pin_card(), pin_dir(), _source()

### Community 63 - "Architecture Guard Test"
Cohesion: 0.17
Nodes (8): _breaches(), _imports(), _module_of(), _submodules(), test_every_package_is_a_known_module_with_a_public_api(), test_modules_import_each_other_only_through_their_api_and_downwards(), test_the_app_reaches_the_core_only_through_its_services(), test_the_core_never_imports_the_app_or_qt()

### Community 64 - "pytest"
Cohesion: 0.16
Nodes (13): ConfigError, active_series(), find_root(), list_series(), merge_sections(), parse_config(), _read_yaml(), save_config_text() (+5 more)

### Community 66 - "Pinned Requirements"
Cohesion: 0.10
Nodes (20): jieba 0.42.1, numpy 2.5.3, onnxruntime-gpu 1.30.0, openai 3.22.1, opencv-python-headless 5.0.0.93, pillow 12.3.0, pydantic 2.13.5, pypinyin 0.55.0 (+12 more)

### Community 67 - "Briefings & Style Rules"
Cohesion: 0.13
Nodes (19): load_prompt(), BriefingResponse, compress_story(), generate_briefing(), script_text(), StoryResponse, briefings_dir(), cap_style_rules() (+11 more)

### Community 68 - "NewCharacterDialog"
Cohesion: 0.29
Nodes (3): NewCharacterDialog, validate(), is_han()

### Community 69 - "Top-level Config Keys"
Cohesion: 0.10
Nodes (19): budget, max_cost_per_episode, cleanup, auto, device, episodes, number_patterns, video_extensions (+11 more)

### Community 70 - "kernel/__init__.py"
Cohesion: 0.09
Nodes (13): running_jobs(), BudgetExceeded, EpisodeLockedError, EpisodeNotFoundError, LLMOutputError, MemoryLockedError, append_jsonl(), _atomic_write() (+5 more)

### Community 71 - "Settings Schema Introspection"
Cohesion: 0.14
Nodes (9): _code_notes(), fields(), walk(), known_sets(), target(), _unwrap(), value_at(), with_known_sets() (+1 more)

### Community 73 - "rule_checks"
Cohesion: 0.15
Nodes (8): rule_checks(), RuleContext, _word_tokenizer(), _line(), test_glossary_rule_matches_whole_words_only(), test_pronoun_rule(), test_rules_catch_glossary_length_cps_and_speaker(), test_rules_pass_for_a_good_line()

### Community 74 - "Memory Banks Writing"
Cohesion: 0.14
Nodes (6): _add_exemplars(), BanksMixin, _drop_exemplar(), _keep_best(), _record_votes(), _undo_episode()

### Community 75 - "LLM Provider Config"
Cohesion: 0.11
Nodes (18): api_key_env, base_url, model, llm, max_retries, max_retry_wait_s, providers, temperature (+10 more)

### Community 76 - "test_pinyin_voice_windows.py"
Cohesion: 0.14
Nodes (10): Character, build_windows(), run(), write_silence(), _engine(), test_pinyin_uses_glossary_and_attaches_punctuation(), test_pinyin_words_are_joined_within_and_spaced_between(), test_polyphones_outside_known_phrases_are_reported() (+2 more)

### Community 77 - "pinyin_gen.py"
Cohesion: 0.20
Nodes (7): heteronyms(), PinyinEngine, PolyphoneChoice, PolyphoneResponse, resolve_polyphones(), run(), Token

### Community 78 - "Voice Learning Tests"
Cohesion: 0.18
Nodes (14): torch_device(), ModelUnavailableError, _auto_episode(), _episode(), _fake_embed(), test_auto_lines_pass_only_when_every_signal_agrees(), test_auto_lines_that_hurt_accuracy_are_not_learned(), test_auto_lines_that_keep_accuracy_are_learned() (+6 more)

### Community 79 - "Render Config"
Cohesion: 0.12
Nodes (17): render, avg_char_width, blur_radius, encoder, font_dir, font_name, line_spacing, mask (+9 more)

### Community 80 - "test_probation.py"
Cohesion: 0.26
Nodes (13): Candidate, _finish(), _lines(), _talks(), test_a_candidate_not_back_in_time_is_dropped(), test_a_new_voice_waits_on_probation_and_is_promoted_when_it_comes_back(), test_a_review_npc_goes_on_probation_at_finish(), test_auto_mode_needs_a_trusted_line_to_promote() (+5 more)

### Community 81 - "numpy"
Cohesion: 0.20
Nodes (5): candidate_looks(), candidate_voice(), check_return(), ReturnCheck, _unit()

### Community 82 - "Memory & Translation Prompts"
Cohesion: 0.19
Nodes (8): Style rules, Cổ trang / tiên hiệp register (Hán-Việt terms), identify / default_pair template toggle, Memory proposals (glossary / pronoun_pair / character), Pronoun matrix, Retries with earlier_attempts and evaluator_suggestion, Reviewer corrections, Speaker rules per voice status (fixed/confusable/disputed/new_voice/unknown/too_short)

### Community 83 - "SubtitleEvent"
Cohesion: 0.23
Nodes (10): SubtitleEvent, chunked(), apply_fixes(), batch_payload(), OcrFixChange, OcrFixResponse, run(), max_chars_for() (+2 more)

### Community 84 - "._field"
Cohesion: 0.18
Nodes (5): _decimals(), Field, set_float(), add(), FieldSpec

### Community 86 - "test_bootstrap_dream_cli.py"
Cohesion: 0.13
Nodes (11): build_parser(), main(), _setup_logging(), update_config_values(), _clip(), _fake_embed(), test_cli_errors_are_json_with_codes(), test_cli_status_and_add() (+3 more)

### Community 87 - "Series-1 Band Config"
Cohesion: 0.13
Nodes (15): bottom, left, right, top, video, band_frames, change_threshold, empty_text_ratio (+7 more)

### Community 88 - "test_character_lifecycle.py"
Cohesion: 0.40
Nodes (11): CharacterFate, _lines(), _setup(), _status(), test_consecutive_episodes_keep_a_character(), test_first_run_counts_earlier_episodes(), test_generic_characters_are_never_matched_or_learned(), test_old_memory_gets_the_new_columns() (+3 more)

### Community 89 - "Runner"
Cohesion: 0.35
Nodes (3): Runner, StageDef, ocr_hash()

### Community 91 - "LineHistory"
Cohesion: 0.18
Nodes (5): LineHistory, _Clock, test_steps_are_per_line_and_copies(), test_typing_in_one_field_is_one_undo_step(), test_undo_and_redo_restore_the_line_and_break_the_merge()

### Community 93 - "Prices Editor"
Cohesion: 0.16
Nodes (3): _num_text(), PricesEditor, ProvidersEditor

### Community 94 - "render.py"
Cohesion: 0.22
Nodes (10): _ass_text(), check_fonts(), choose_encoder(), encoder_args(), ffmpeg_args(), font_files(), preview_ass(), _run_ffmpeg() (+2 more)

### Community 98 - "Price Table Keys"
Cohesion: 0.15
Nodes (13): input, input_cached, output, input, input_cached, output, input, input_cached (+5 more)

### Community 99 - "Memory Config Keys"
Cohesion: 0.15
Nodes (13): memory, aliases_max, archive_after_absent, character_lifecycle, character_updates, correction_examples, description_max_chars, dream_max_lines (+5 more)

### Community 100 - "Series-1 series.yaml"
Cohesion: 0.15
Nodes (12): baseline, name, bench, baseline, non_dialogue, box_center_tolerance, box_height_tolerance, enabled (+4 more)

### Community 102 - "test_partial_review.py"
Cohesion: 0.24
Nodes (10): _episode(), _line(), _sug_model(), test_a_speaker_set_by_an_earlier_partial_review_may_change_again(), test_partial_review_learns_this_episodes_voices(), test_partial_review_names_the_talking_sprite_and_suggests_without_touching_memory(), test_suggestion_rules(), test_without_a_voice_update_the_pipeline_voice_still_counts() (+2 more)

### Community 103 - "Device Detection"
Cohesion: 0.21
Nodes (6): add_check(), cmd_check(), describe(), onnx_cuda_available(), onnx_use_cuda(), torch_cuda_available()

### Community 104 - "json"
Cohesion: 0.18
Nodes (5): atomic_write_json(), read_json(), dumps_aliases(), UpdatesMixin, parse_aliases()

### Community 105 - "Series-1 OCR Config"
Cohesion: 0.18
Nodes (11): ocr, fragment_max_samples, fragment_merge_similarity, mask_image, mask_scale, merge_max_edit_distance, min_confidence, preprocess (+3 more)

### Community 106 - "Series-1 Script Review Config"
Cohesion: 0.18
Nodes (11): script_review, enabled, example_limit, max_remove_share, memory_auto_remove_min, memory_max_han, remove_confidence, repeat_merge_gap_ms (+3 more)

### Community 109 - "test_new_voices.py"
Cohesion: 0.14
Nodes (18): NewVoice, draft_voice_ids(), episode_character_ids(), is_auto_id(), is_unnamed(), load_new_voices(), review_voice_ids(), save_new_voices() (+10 more)

### Community 110 - "sprite.py"
Cohesion: 0.26
Nodes (6): best_match(), candidates_for(), decide(), load_templates(), run(), save_template()

### Community 111 - "Translate Config"
Cohesion: 0.22
Nodes (9): translate, max_cps, max_line_chars, max_lines_per_event, max_retries, picture_evidence, picture_veto, pronoun_terms (+1 more)

### Community 112 - "measure.py"
Cohesion: 0.11
Nodes (29): _ask(), build_pipeline(), _interactive(), _output_exists(), _resolve_on_exists(), add_batch(), add_calibrate(), add_clean() (+21 more)

### Community 113 - "textutil.py"
Cohesion: 0.26
Nodes (6): balanced_wrap(), nfc(), split_explicit_lines(), visible_chars(), wrap_words(), wrap_lines()

### Community 114 - "rules"
Cohesion: 0.40
Nodes (3): check(), show(), rules()

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
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1020 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **29 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ReviewedLine` connect `partial.py` to `test_app.py`, `App Package & Jobs`, `test_ocr_preprocess.py`, `Memory Manager Rows`, `test_audit.py`, `test_feedback_loop.py`, `Memory Manager Tests`, `test_review_state.py`, `models.py`, `Benchmark Suite`, `workspace/__init__.py`, `test_cast.py`, `Memory Store`, `test_suite.py`, `test_character_card.py`, `Services`, `runner.py`, `Voice Learning & Evidence`, `Script Review & OCR Fix`, `ReviewView`, `build_ass`, `ocr_benchmark.py`, `Dreaming`, `character_updates.py`, `Voice Candidates`, `memory/__init__.py`, `._loaded`, `partial.py`, `Paths`, `Briefings & Style Rules`, `kernel/__init__.py`, `Voice Learning Tests`, `test_probation.py`, `numpy`, `test_bootstrap_dream_cli.py`, `test_character_lifecycle.py`, `.episode_update`, `LineHistory`, `render.py`, `AuditBar`, `test_partial_review.py`, `json`, `test_new_voices.py`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ReviewedLine` (e.g. with `_finish()` and `test_pipeline_records_what_the_reviewer_removed_and_kept()`) actually correct?**
  _`ReviewedLine` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `subagent`, `Font draws 了 like digit 7`, `Show wording that looks like stray text (史 for 屎, 鸡道, 姬叔)` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12854609929078015 - nodes in this community are weakly interconnected._
- **Why does `Config` connect `Voice Learning & Evidence` to `client.py`, `Memory Manager Rows`, `test_audit.py`, `test_feedback_loop.py`, `Memory Manager Tests`, `Benchmark Suite`, `Config Schema`, `workspace/__init__.py`, `Cast Engine`, `test_cast.py`, `Memory Store`, `Services`, `OCR Engine & Geometry`, `Pipeline Runner & Locks`, `conftest.py`, `runner.py`, `Frozen Baseline`, `Bootstrap Seed`, `build_ass`, `ocr_benchmark.py`, `Episode`, `make_llm`, `memory/__init__.py`, `Dreaming`, `character_updates.py`, `memory/__init__.py`, `Voice Match`, `Bench Run Sandbox`, `load_config`, `partial.py`, `test_parser_stages.py`, `Paths`, `pytest`, `Briefings & Style Rules`, `Settings Schema Introspection`, `pinyin_gen.py`, `Voice Learning Tests`, `SubtitleEvent`, `test_bootstrap_dream_cli.py`, `render.py`, `Device Detection`, `measure.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Config` (e.g. with `fields()` and `value_at()`) actually correct?**
  _`Config` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `client.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11904761904761904 - nodes in this community are weakly interconnected._