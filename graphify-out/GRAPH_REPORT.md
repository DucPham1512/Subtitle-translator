# Graph Report - Subtitle-translator  (2026-11-03)

## Corpus Check
- 214 files · ~168,650 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .qm 2, .example 1)

## Summary
- 3289 nodes · 11309 edges · 139 communities (106 shown, 33 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 684 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4ebb393c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_app.py
- LLM Client & Costs
- App Package & Jobs
- SpeakerCandidates
- Memory Screen
- Band & Cast Panel Views
- partial.py
- Memory Manager Rows
- test_audit.py
- test_feedback_loop.py
- Memory Manager Tests
- Bootstrap Wizard View
- New Voices & Characters
- register_episode
- Benchmark Suite
- Config Schema
- render.py
- Series Management
- Cast Engine
- Video Preview (mpv)
- test_cast.py
- Memory Store
- rule_checks
- core.py
- Services
- OCR Engine & Geometry
- Subtitle Style
- Pipeline Runner & Locks
- CLI Episodes
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
- Speaker Benchmark
- ocr_benchmark.py
- Episode Registry
- read_jsonl
- Ingest & Change Detection
- Character Browser
- conftest.py
- memory/__init__.py
- Dreaming
- Character Updates
- Voice Candidates
- New Series Dialog
- Config
- Voice Match
- Bench Run Sandbox
- Translation Registers
- Series-1 Voice Config
- ._open_preview
- bench/audit.py
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
- delivery.py
- SubtitleEvent
- Memory Banks Writing
- LLM Provider Config
- test_pinyin_voice_windows.py
- pinyin_gen.py
- Voice Learning Tests
- Render Config
- kernel/__init__.py
- test_episodes.py
- Memory & Translation Prompts
- json
- Episode Memory Update
- Tag Editor Widget
- subagent/__main__.py
- Series-1 Band Config
- test_character_lifecycle.py
- Runner
- Job Runner
- LineHistory
- Flow Layout
- Prices Editor
- Band
- AuditBar
- Settings Form
- Price Table Keys
- Memory Config Keys
- Series-1 series.yaml
- typing
- ._load_sprites
- Device Detection
- Memory Aux Writes
- Series-1 OCR Config
- Series-1 Script Review Config
- HistoryMixin
- FileLock
- test_new_voices.py
- AddCandidate
- Translate Config
- cli/memory.py
- TimelineSlider
- ._center_band
- Background Workers
- .line_ocr_crop
- test_missing_source_marks_episode
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
- `load()` --indirect_call--> `episode_id()`  [INFERRED]
  app/views/review.py → subagent/workspace/episodes.py
- `save()` --indirect_call--> `episode_id()`  [INFERRED]
  app/views/review.py → subagent/workspace/episodes.py
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

## Communities (139 total, 33 thin omitted)

### Community 0 - "test_app.py"
Cohesion: 0.12
Nodes (31): MainWindow, validate(), LineTranslation, PinyinLine, write_jsonl(), gate(), register_episode(), sample_events() (+23 more)

### Community 1 - "LLM Client & Costs"
Cohesion: 0.08
Nodes (28): BudgetExceeded, LLMCallError, LLMOutputError, CostRecord, compute_cost(), _daily_quota(), _describe(), LLMClient (+20 more)

### Community 2 - "App Package & Jobs"
Cohesion: 0.05
Nodes (16): choose_platform(), install_fonts(), install_translator(), main(), agent_label(), error_message(), stage_label(), status_label() (+8 more)

### Community 3 - "SpeakerCandidates"
Cohesion: 0.15
Nodes (17): PartialSuggestion, SpeakerCandidates, partial_review(), PartialResult, _session_bank(), _sprites(), suggest(), _episode() (+9 more)

### Community 4 - "Memory Screen"
Cohesion: 0.05
Nodes (9): EntryTable, _item(), MemoryView, done(), PairDialog, text(), _same(), _update_text() (+1 more)

### Community 5 - "Band & Cast Panel Views"
Cohesion: 0.07
Nodes (6): BandView, CastCanvas, CastPanel, ScaledImage, to_pixmap(), test_greyscale_images_can_be_shown()

### Community 6 - "partial.py"
Cohesion: 0.11
Nodes (26): ReviewIncompleteError, ReviewedLine, apply_script_review(), build_draft(), compute_edits(), draft_path(), finish_review(), flag_group() (+18 more)

### Community 7 - "Memory Manager Rows"
Cohesion: 0.16
Nodes (23): contains_term(), merge_proposals(), replaced_term(), reviewed_glossary(), CommitInfo, Conflict, describe_update(), dumps_aliases() (+15 more)

### Community 8 - "test_audit.py"
Cohesion: 0.18
Nodes (15): disagreements(), draw_sample(), load_marks(), missing_answers(), save_marks(), AuditMark, _episode(), pathlib_name() (+7 more)

### Community 9 - "test_feedback_loop.py"
Cohesion: 0.11
Nodes (28): run(), WindowTranslator, user_json(), _rubric(), evaluator(), test_a_passing_line_keeps_the_evaluators_suggestion_for_the_reviewer(), test_reading_speed_is_flagged_not_retried(), test_retry_sends_history_and_suggestion() (+20 more)

### Community 10 - "Memory Manager Tests"
Cohesion: 0.11
Nodes (33): EditRecord, present_ids(), MemoryManager, seed_memory(), _line(), _llm(), _npc(), test_a_candidate_keeps_its_updates_when_promoted() (+25 more)

### Community 12 - "New Voices & Characters"
Cohesion: 0.23
Nodes (14): Candidate, save_line_voices(), _finish(), _lines(), _talks(), test_a_candidate_not_back_in_time_is_dropped(), test_a_new_voice_waits_on_probation_and_is_promoted_when_it_comes_back(), test_a_review_npc_goes_on_probation_at_finish() (+6 more)

### Community 13 - "register_episode"
Cohesion: 0.11
Nodes (14): freeze_finished(), write_silence(), test_turning_it_on_again_runs_the_stages(), calls(), _pipeline(), stubs(), ocr(), test_auto_mode_end_to_end_and_output_conflict() (+6 more)

### Community 14 - "Benchmark Suite"
Cohesion: 0.11
Nodes (35): align(), _approved(), _auto_pattern(), characters_at(), _decisions(), _events(), Gold, group_map() (+27 more)

### Community 15 - "Config Schema"
Cohesion: 0.12
Nodes (24): AudioConfig, AuditConfig, BaselineConfig, BenchConfig, BudgetConfig, CleanupConfig, EpisodesConfig, EvaluateConfig (+16 more)

### Community 16 - "render.py"
Cohesion: 0.09
Nodes (23): _ass_text(), build_ass(), build_mask_filter(), check_fonts(), choose_encoder(), _color(), encoder_args(), ffmpeg_args() (+15 more)

### Community 17 - "Series Management"
Cohesion: 0.15
Nodes (13): cmd_series(), running_jobs(), JobRunningError, add(), _blocks(), check_slug(), migrate(), _refuse_while_jobs_run() (+5 more)

### Community 18 - "Cast Engine"
Cohesion: 0.07
Nodes (26): build_bank(), CastEngine, crop(), _ffmpeg(), frame_path(), frame_time_ms(), get_engine(), group_unknowns() (+18 more)

### Community 19 - "Video Preview (mpv)"
Cohesion: 0.12
Nodes (4): fmt_time(), load_mpv(), PreviewWidget, test_preview_transport_controls()

### Community 20 - "test_cast.py"
Cohesion: 0.10
Nodes (24): _apply_labels(), _check_talkers(), learn_sprites(), _name_unknowns(), plan(), _Plan, SpriteLearnResult, EpisodeState (+16 more)

### Community 21 - "Memory Store"
Cohesion: 0.07
Nodes (18): _alias_zh(), check(), _clip(), _pairs_block(), _present_block(), propose(), _script(), glossary_zh_block() (+10 more)

### Community 22 - "rule_checks"
Cohesion: 0.15
Nodes (11): check(), rule_checks(), RuleContext, picture_veto(), test_picture_veto_disputes_the_voice(), _line(), rules(), test_glossary_rule_matches_whole_words_only() (+3 more)

### Community 23 - "core.py"
Cohesion: 0.08
Nodes (24): gold_boxes(), card_info(), confirmed_box(), shown_talking_box(), CastBoxEdit, CastDetection, CastLine, VideoInfo (+16 more)

### Community 24 - "Services"
Cohesion: 0.07
Nodes (3): EpisodeRow, script_note(), Services

### Community 25 - "OCR Engine & Geometry"
Cohesion: 0.07
Nodes (23): onnx_use_cuda(), OcrBox, line_span(), symmetric_span(), create_engine(), crop_view(), _engine_key(), filter_boxes() (+15 more)

### Community 26 - "Subtitle Style"
Cohesion: 0.12
Nodes (18): calibrate(), grow_line(), labels_near(), load_style(), propose_regions(), _region_features(), save_style(), segment_mask() (+10 more)

### Community 27 - "Pipeline Runner & Locks"
Cohesion: 0.13
Nodes (4): _learn(), job_lock(), _episode_log, Pipeline

### Community 28 - "CLI Episodes"
Cohesion: 0.11
Nodes (27): _ask(), build_pipeline(), _interactive(), _output_exists(), _resolve_on_exists(), add_add(), add_batch(), add_calibrate() (+19 more)

### Community 29 - "Episodes Screen"
Cohesion: 0.10
Nodes (5): job_busy(), DropTable, EpisodesView, done(), confirm()

### Community 30 - "Memory Proposals Apply"
Cohesion: 0.19
Nodes (6): MemoryProposal, atomic_write_text(), ApplyMixin, ApplyResult, test_a_different_suggestion_for_the_same_term_still_comes_through(), gloss()

### Community 31 - "runner.py"
Cohesion: 0.08
Nodes (18): collect_metrics(), counts_text(), episode_status(), _pct(), write_report(), BatchItem, _lazy(), review_outputs() (+10 more)

### Community 32 - "Voice Learning & Evidence"
Cohesion: 0.13
Nodes (20): add_voices(), cmd_voices(), _voices(), auto_gate(), AutoGate, build_centroids(), Clip, embed_clips() (+12 more)

### Community 33 - "Media (ffmpeg) Infra"
Cohesion: 0.09
Nodes (25): best_match(), candidates_for(), decide(), load_templates(), run(), frame_reader(), save_template(), job_lock_path() (+17 more)

### Community 34 - "Audit & Dreaming Screens"
Cohesion: 0.08
Nodes (6): label(), AuditView, done(), DreamingView, _summary(), show_error()

### Community 36 - "Script Review & OCR Fix"
Cohesion: 0.11
Nodes (19): ScriptDecision, edit_distance(), is_han(), nfc(), normalize_zh(), relatedness(), LineDecision, ScriptReviewConfig (+11 more)

### Community 37 - "Frozen Baseline"
Cohesion: 0.17
Nodes (15): baseline_dir(), complete(), freeze(), freeze_episode(), _git_head(), _manifest(), memory_at_run(), _save_manifest() (+7 more)

### Community 38 - "Bootstrap Seed"
Cohesion: 0.15
Nodes (18): approve_seed(), _episode1_lines(), generate_seed(), load_seed(), name_pinyin(), save_clip(), save_seed(), seed_path() (+10 more)

### Community 39 - "YAML Comment-Preserving Edit"
Cohesion: 0.14
Nodes (17): file_comment(), _block_end(), delete_key(), _dump(), _find(), _get(), _is_child(), _path() (+9 more)

### Community 40 - "ReviewView"
Cohesion: 0.05
Nodes (7): flag_label(), ReviewView, show(), done(), load(), loaded(), done()

### Community 41 - "Speaker Benchmark"
Cohesion: 0.15
Nodes (11): auditable_lines(), gold_speakers(), is_flagged(), _acc(), benchmark_episodes(), BenchmarkResult, _copy_reviewer_context(), _drop_heavy_files() (+3 more)

### Community 42 - "ocr_benchmark.py"
Cohesion: 0.08
Nodes (27): _sandbox_paths(), _covered(), EpisodeOcrScore, _existing_events(), gold_lines(), load_key(), _norm(), ocr_episodes() (+19 more)

### Community 43 - "Episode Registry"
Cohesion: 0.15
Nodes (11): add_status(), cmd_status(), EpisodeNotFoundError, SourceMissingError, Episode, derived_status(), episode_id(), Registry (+3 more)

### Community 44 - "read_jsonl"
Cohesion: 0.14
Nodes (25): read_jsonl(), run(), run(), _review_run(), run(), run(), run(), run() (+17 more)

### Community 45 - "Ingest & Change Detection"
Cohesion: 0.15
Nodes (21): ChangeRecord, binarize(), calibrate(), Change, change_fraction(), detect_changes(), draw_band(), fuse() (+13 more)

### Community 46 - "Character Browser"
Cohesion: 0.12
Nodes (5): CharacterBrowser, CharacterStrip, describe(), _pixmap(), ClipPlayer

### Community 47 - "conftest.py"
Cohesion: 0.19
Nodes (11): main(), prompt_hash(), load_config(), project(), test_new_series_asks_how_pronouns_are_decided(), test_a_new_series_has_its_own_folders_settings_and_font(), test_cli_series_commands(), test_migrate_names_the_single_series_layout() (+3 more)

### Community 48 - "memory/__init__.py"
Cohesion: 0.13
Nodes (12): _kept_evaluation(), Evaluation, corrections_block(), reviewer_corrections(), _best(), ProposalDraft, rank_attempt(), _same() (+4 more)

### Community 49 - "Dreaming"
Cohesion: 0.09
Nodes (34): apply_dream(), approved_lines(), describe(), done_episodes(), dream(), DreamGlossary, DreamItem, DreamOutput (+26 more)

### Community 50 - "Character Updates"
Cohesion: 0.23
Nodes (7): CharacterChange, CharacterUpdateResponse, _has_word(), _introduces(), _positions(), PronounUse, parse_aliases()

### Community 51 - "Voice Candidates"
Cohesion: 0.08
Nodes (10): load_line_voices(), CandidatesMixin, _Run, candidate_looks(), candidate_voice(), check_return(), ReturnCheck, speaker_lines() (+2 more)

### Community 52 - "New Series Dialog"
Cohesion: 0.13
Nodes (5): NewSeriesDialog, StyleDialog, test_new_series_dialog_asks_for_the_default_pronoun_pair(), test_new_series_dialog_creates_a_translation_style(), test_new_series_work_folder_can_be_chosen()

### Community 53 - "Config"
Cohesion: 0.13
Nodes (9): trusted_speakers(), torch_device(), is_auto_episode(), trusted_auto_lines(), usable_line(), Config, auto_clips(), reviewed_clips() (+1 more)

### Community 54 - "Voice Match"
Cohesion: 0.15
Nodes (15): load(), update_voices(), new_voice_id(), VoiceConfig, all_similarities(), classify(), compute_centroids(), find_new_voices() (+7 more)

### Community 55 - "Bench Run Sandbox"
Cohesion: 0.16
Nodes (13): checkout_memory(), _drop_heavy(), _frozen_inputs(), _install_review(), _null(), _rerun_episode(), run(), _run_info() (+5 more)

### Community 56 - "Translation Registers"
Cohesion: 0.13
Nodes (20): EpisodeLockedError, MemoryLockedError, StageError, SubagentError, check_id(), list_registers(), load_register(), _parse() (+12 more)

### Community 57 - "Series-1 Voice Config"
Cohesion: 0.08
Nodes (24): voice, accept_score, confusable_similarity, learn_auto_allowed_flags, learn_auto_max_drop, learn_auto_min_margin, learn_auto_min_score, learn_auto_min_test_lines (+16 more)

### Community 59 - "bench/audit.py"
Cohesion: 0.19
Nodes (14): auditable(), AuditReport, build_report(), EpisodeAudit, load_sample(), _pct(), Rate, render_report() (+6 more)

### Community 60 - "Series-1 Cast Config"
Cohesion: 0.09
Nodes (23): cast, add_similarity, detector_model, embed_model, enabled, frame_width, learn, match_margin (+15 more)

### Community 61 - "test_parser_stages.py"
Cohesion: 0.12
Nodes (22): OcrReading, absorb_fragments(), build_events(), flag_non_dialogue(), frames_on_screen(), _Group, group_readings(), _median() (+14 more)

### Community 62 - "Paths"
Cohesion: 0.23
Nodes (10): card_media(), CharacterCard, _cut_clip(), _cut_picture(), _episode_ids(), _frame(), pin_card(), pin_dir() (+2 more)

### Community 63 - "Architecture Guard Test"
Cohesion: 0.21
Nodes (8): _breaches(), _imports(), _module_of(), _submodules(), test_every_package_is_a_known_module_with_a_public_api(), test_modules_import_each_other_only_through_their_api_and_downwards(), test_the_app_reaches_the_core_only_through_its_services(), test_the_core_never_imports_the_app_or_qt()

### Community 64 - "pytest"
Cohesion: 0.14
Nodes (13): ConfigError, active_series(), find_root(), list_series(), merge_sections(), parse_config(), _read_yaml(), save_config_text() (+5 more)

### Community 66 - "Pinned Requirements"
Cohesion: 0.10
Nodes (20): jieba 0.42.1, numpy 2.5.3, onnxruntime-gpu 1.30.0, openai 3.22.1, opencv-python-headless 5.0.0.93, pillow 12.3.0, pydantic 2.13.5, pypinyin 0.55.0 (+12 more)

### Community 67 - "Briefings & Style Rules"
Cohesion: 0.19
Nodes (14): briefings_dir(), cap_style_rules(), IndexEntry, list_episode_briefings(), _read(), read_episode_briefing(), read_index(), read_story() (+6 more)

### Community 68 - "Review Character Editor"
Cohesion: 0.10
Nodes (9): character_proposals(), NewCharacterDialog, save(), done(), failed(), done(), done(), failed() (+1 more)

### Community 69 - "Top-level Config Keys"
Cohesion: 0.10
Nodes (19): budget, max_cost_per_episode, cleanup, auto, device, episodes, number_patterns, video_extensions (+11 more)

### Community 70 - "util.py"
Cohesion: 0.16
Nodes (9): append_jsonl(), _atomic_write(), atomic_write_bytes(), hash_path(), lock_holder(), pid_alive(), _replace_with_retry(), sha256_bytes() (+1 more)

### Community 71 - "Settings Schema Introspection"
Cohesion: 0.13
Nodes (10): add(), _code_notes(), fields(), walk(), FieldSpec, known_sets(), target(), _unwrap() (+2 more)

### Community 72 - "delivery.py"
Cohesion: 0.16
Nodes (16): OutputExistsError, OutputFolderError, cleanup(), deliver(), keep_both_path(), output_folder(), output_name(), resolve_conflict() (+8 more)

### Community 73 - "SubtitleEvent"
Cohesion: 0.18
Nodes (10): SubtitleEvent, judge(), llm_rubric(), max_chars_for(), rubric_payload(), RubricLine, RubricResponse, RuleFailure (+2 more)

### Community 74 - "Memory Banks Writing"
Cohesion: 0.14
Nodes (6): _add_exemplars(), BanksMixin, _drop_exemplar(), _keep_best(), _record_votes(), _undo_episode()

### Community 75 - "LLM Provider Config"
Cohesion: 0.11
Nodes (18): api_key_env, base_url, model, llm, max_retries, max_retry_wait_s, providers, temperature (+10 more)

### Community 76 - "test_pinyin_voice_windows.py"
Cohesion: 0.15
Nodes (11): Character, GlossaryEntry, LogEntry, VoiceEntry, _word_tokenizer(), _engine(), test_classify_status_rules(), test_pinyin_uses_glossary_and_attaches_punctuation() (+3 more)

### Community 77 - "pinyin_gen.py"
Cohesion: 0.22
Nodes (6): heteronyms(), PinyinEngine, PolyphoneChoice, PolyphoneResponse, run(), Token

### Community 78 - "Voice Learning Tests"
Cohesion: 0.22
Nodes (13): ModelUnavailableError, _auto_episode(), _episode(), _fake_embed(), test_auto_lines_pass_only_when_every_signal_agrees(), test_auto_lines_that_hurt_accuracy_are_not_learned(), test_auto_lines_that_keep_accuracy_are_learned(), test_auto_lines_wait_until_there_is_enough_to_measure() (+5 more)

### Community 79 - "Render Config"
Cohesion: 0.12
Nodes (17): render, avg_char_width, blur_radius, encoder, font_dir, font_name, line_spacing, mask (+9 more)

### Community 80 - "kernel/__init__.py"
Cohesion: 0.17
Nodes (9): Window, balanced_wrap(), split_explicit_lines(), visible_chars(), wrap_words(), WindowsConfig, wrap_lines(), build_windows() (+1 more)

### Community 81 - "test_episodes.py"
Cohesion: 0.18
Nodes (9): detect_number(), fingerprint(), scan_paths(), test_add_register_duplicates_and_numbers(), test_detect_number(), test_fingerprint_reads_head_and_tail(), test_no_video_stream_is_skipped(), test_register_rejects_missing_and_clashing_numbers() (+1 more)

### Community 82 - "Memory & Translation Prompts"
Cohesion: 0.19
Nodes (8): Style rules, Cổ trang / tiên hiệp register (Hán-Việt terms), identify / default_pair template toggle, Memory proposals (glossary / pronoun_pair / character), Pronoun matrix, Retries with earlier_attempts and evaluator_suggestion, Reviewer corrections, Speaker rules per voice status (fixed/confusable/disputed/new_voice/unknown/too_short)

### Community 83 - "json"
Cohesion: 0.11
Nodes (16): chunked(), build_messages(), load_prompt(), BriefingResponse, compress_story(), generate_briefing(), script_text(), StoryResponse (+8 more)

### Community 86 - "subagent/__main__.py"
Cohesion: 0.22
Nodes (3): Progress, build_parser(), _setup_logging()

### Community 87 - "Series-1 Band Config"
Cohesion: 0.13
Nodes (15): bottom, left, right, top, video, band_frames, change_threshold, empty_text_ratio (+7 more)

### Community 88 - "test_character_lifecycle.py"
Cohesion: 0.40
Nodes (11): CharacterFate, _lines(), _setup(), _status(), test_consecutive_episodes_keep_a_character(), test_first_run_counts_earlier_episodes(), test_generic_characters_are_never_matched_or_learned(), test_old_memory_gets_the_new_columns() (+3 more)

### Community 89 - "Runner"
Cohesion: 0.33
Nodes (4): StageState, Runner, StageDef, ocr_hash()

### Community 90 - "Job Runner"
Cohesion: 0.20
Nodes (3): JobRunner, test_run_panel_has_a_script_review_step(), __init__()

### Community 91 - "LineHistory"
Cohesion: 0.10
Nodes (16): all_correct_mark(), line_matches(), LineFilter, LineHistory, marked_count(), next_npc_number(), next_unmarked(), _Clock (+8 more)

### Community 93 - "Prices Editor"
Cohesion: 0.11
Nodes (6): _decimals(), Field, _num_text(), PricesEditor, ProvidersEditor, set_float()

### Community 94 - "Band"
Cohesion: 0.18
Nodes (4): center_in_band(), Band, test_band_pixels_are_even_and_inside_frame(), test_band_centres_by_widening_the_short_side()

### Community 98 - "Price Table Keys"
Cohesion: 0.15
Nodes (13): input, input_cached, output, input, input_cached, output, input, input_cached (+5 more)

### Community 99 - "Memory Config Keys"
Cohesion: 0.15
Nodes (13): memory, aliases_max, archive_after_absent, character_lifecycle, character_updates, correction_examples, description_max_chars, dream_max_lines (+5 more)

### Community 100 - "Series-1 series.yaml"
Cohesion: 0.15
Nodes (12): baseline, name, bench, baseline, non_dialogue, box_center_tolerance, box_height_tolerance, enabled (+4 more)

### Community 103 - "Device Detection"
Cohesion: 0.31
Nodes (3): describe(), onnx_cuda_available(), torch_cuda_available()

### Community 104 - "Memory Aux Writes"
Cohesion: 0.21
Nodes (4): atomic_write_json(), now_iso(), read_json(), UpdatesMixin

### Community 105 - "Series-1 OCR Config"
Cohesion: 0.18
Nodes (11): ocr, fragment_max_samples, fragment_merge_similarity, mask_image, mask_scale, merge_max_edit_distance, min_confidence, preprocess (+3 more)

### Community 106 - "Series-1 Script Review Config"
Cohesion: 0.18
Nodes (11): script_review, enabled, example_limit, max_remove_share, memory_auto_remove_min, memory_max_han, remove_confidence, repeat_merge_gap_ms (+3 more)

### Community 109 - "test_new_voices.py"
Cohesion: 0.15
Nodes (18): NewVoice, draft_voice_ids(), episode_character_ids(), is_auto_id(), is_unnamed(), load_new_voices(), review_voice_ids(), save_new_voices() (+10 more)

### Community 111 - "Translate Config"
Cohesion: 0.22
Nodes (9): translate, max_cps, max_line_chars, max_lines_per_event, max_retries, picture_evidence, picture_veto, pronoun_terms (+1 more)

### Community 112 - "cli/memory.py"
Cohesion: 0.47
Nodes (4): add_dream(), add_sprites(), cmd_dream(), cmd_sprites()

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
- **33 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ReviewedLine` connect `partial.py` to `test_app.py`, `App Package & Jobs`, `SpeakerCandidates`, `Memory Manager Rows`, `test_audit.py`, `test_feedback_loop.py`, `Memory Manager Tests`, `New Voices & Characters`, `Benchmark Suite`, `render.py`, `Cast Engine`, `test_cast.py`, `Memory Store`, `core.py`, `Services`, `runner.py`, `Voice Learning & Evidence`, `ReviewView`, `Speaker Benchmark`, `ocr_benchmark.py`, `read_jsonl`, `Dreaming`, `Character Updates`, `Voice Candidates`, `Config`, `bench/audit.py`, `Paths`, `Briefings & Style Rules`, `delivery.py`, `Voice Learning Tests`, `kernel/__init__.py`, `json`, `Episode Memory Update`, `test_character_lifecycle.py`, `LineHistory`, `Memory Aux Writes`, `test_new_voices.py`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ReviewedLine` (e.g. with `_finish()` and `test_pipeline_records_what_the_reviewer_removed_and_kept()`) actually correct?**
  _`ReviewedLine` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `subagent`, `Font draws 了 like digit 7`, `Show wording that looks like stray text (史 for 屎, 鸡道, 姬叔)` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12368972746331237 - nodes in this community are weakly interconnected._
- **Why does `PreviewWidget` connect `Video Preview (mpv)` to `test_app.py`, `App Package & Jobs`, `ReviewView`, `Bootstrap Wizard View`, `.open`, `._open_preview`, `.shutdown`, `.__init__`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Config` (e.g. with `fields()` and `value_at()`) actually correct?**
  _`Config` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `LLM Client & Costs` be split into smaller, more focused modules?**
  _Cohesion score 0.08208020050125313 - nodes in this community are weakly interconnected._