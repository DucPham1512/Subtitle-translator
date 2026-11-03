# Graph Report - Subtitle-translator  (2026-11-03)

## Corpus Check
- 214 files · ~167,725 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .qm 2, .example 1)

## Summary
- 3251 nodes · 11197 edges · 142 communities (107 shown, 35 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 670 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Main Window & Services
- LLM Client & Costs
- App Package & Jobs
- Cast Models & Tests
- Memory Screen
- Band & Cast Panel Views
- Review Data & Cards
- Memory Manager Rows
- Audit Sampling
- Feedback Loop Tests
- Memory Manager Tests
- Bootstrap Wizard View
- New Voices & Characters
- Progress & Pipeline Tests
- Benchmark Suite
- Config Schema
- Output Delivery & ASS
- Series Management
- Cast Engine
- Video Preview (mpv)
- Sprite Learning
- Memory Store
- Evaluator Checks
- Character Cards
- Partial Review Service
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
- Episode Context & Finish
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
- Review Flags & Filters
- Series-1 Cast Config
- Event Building
- Video Render
- Architecture Guard Test
- CLI Entry & Logging
- Frame Selector Widget
- Pinned Requirements
- Briefings & Style Rules
- Review Character Editor
- Top-level Config Keys
- Job Locks
- Settings Schema Introspection
- Bootstrap & Memory Services
- Memory Prompt Prefix
- Memory Banks Writing
- LLM Provider Config
- OCR Preprocess Crop
- Pinyin Engine
- Voice Learning Tests
- Render Config
- Text Utilities
- Episode State & Cleanup
- Memory & Translation Prompts
- OCR Boxes
- Episode Memory Update
- Tag Editor Widget
- CLI Commands
- Series-1 Band Config
- Character Lifecycle
- Probation
- Job Runner
- Memory Entry Table
- Flow Layout
- Prices Editor
- Episode Fingerprints
- Memory Store Models
- Audit Bar
- Settings Form
- Price Table Keys
- Memory Config Keys
- Series-1 series.yaml
- Sprite Check
- Settings Field Controls
- Device Detection
- Memory Aux Writes
- Series-1 OCR Config
- Series-1 Script Review Config
- App Entry Point
- New Character Dialog
- Memory Git History
- Drop Table
- Translate Config
- Briefing Generation
- Memory DB Connection
- Add Episodes Dialog
- Background Workers
- File Lock
- Evaluator Rubric
- Vietnamese UI Fill
- Character Proposals
- Series-1 Cast
- Raw YAML Dialog
- Audit Config
- Text Similarity
- Sprite Config
- Series-1 Review Prompt
- Fake mpv Player
- Style Test Fixtures
- Audio Config
- Output Config
- Review Config
- Windows Config
- Briefing & Story Prompts
- Glossary Tokenizer
- Project Metadata

## God Nodes (most connected - your core abstractions)
1. `ReviewedLine` - 145 edges
2. `Config` - 140 edges
3. `Paths` - 137 edges
4. `read_jsonl()` - 127 edges
5. `MemoryStore` - 112 edges
6. `seed_memory()` - 107 edges
7. `write_jsonl()` - 102 edges
8. `ReviewView` - 94 edges
9. `Registry` - 91 edges
10. `EpisodeContext` - 88 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `find_root()`  [INFERRED]
  app/__main__.py → subagent/settings/config.py
- `_same()` --calls--> `parse_aliases()`  [INFERRED]
  app/views/memory.py → subagent/memory/store.py
- `test_advanced_settings_form_edits_in_place_and_keeps_comments()` --uses--> `TagEditor`  [INFERRED]
  tests/test_app.py → app/views/settings_form.py
- `test_advanced_settings_form_edits_in_place_and_keeps_comments()` --uses--> `PricesEditor`  [INFERRED]
  tests/test_app.py → app/views/settings_form.py
- `_pipeline()` --indirect_call--> `freeze_finished()`  [INFERRED]
  tests/test_pipeline.py → subagent/bench/baseline.py

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

## Communities (142 total, 35 thin omitted)

### Community 0 - "Main Window & Services"
Cohesion: 0.08
Nodes (34): MainWindow, EpisodeRow, Services, validate(), LineTranslation, PinyinLine, write_jsonl(), gate() (+26 more)

### Community 1 - "LLM Client & Costs"
Cohesion: 0.07
Nodes (31): CostRecord, build_messages(), compute_cost(), _daily_quota(), _describe(), LLMClient, missing_prices(), record_cost() (+23 more)

### Community 2 - "App Package & Jobs"
Cohesion: 0.08
Nodes (7): agent_label(), error_message(), stage_label(), status_label(), choose_on_exists(), RunPanel, fmt_ms()

### Community 3 - "Cast Models & Tests"
Cohesion: 0.07
Nodes (34): gold_boxes(), CastBoxEdit, CastDetection, CastLine, EpisodeState, SpeakerCandidates, VideoInfo, picture_veto() (+26 more)

### Community 4 - "Memory Screen"
Cohesion: 0.07
Nodes (7): _item(), MemoryView, done(), PairDialog, text(), _update_text(), run_async()

### Community 5 - "Band & Cast Panel Views"
Cohesion: 0.06
Nodes (9): BandView, CastCanvas, CastPanel, ScaledImage, to_pixmap(), done(), failed(), test_cast_panel_shows_boxes_and_records_corrections() (+1 more)

### Community 6 - "Review Data & Cards"
Cohesion: 0.07
Nodes (31): ReviewIncompleteError, EditRecord, ReviewedLine, ScriptDecision, apply_script_review(), build_draft(), compute_edits(), draft_path() (+23 more)

### Community 7 - "Memory Manager Rows"
Cohesion: 0.18
Nodes (22): merge_proposals(), replaced_term(), reviewed_glossary(), CommitInfo, Conflict, describe_update(), dumps_aliases(), held_updates() (+14 more)

### Community 8 - "Audit Sampling"
Cohesion: 0.10
Nodes (30): auditable(), auditable_lines(), AuditReport, build_report(), disagreements(), draw_sample(), EpisodeAudit, gold_speakers() (+22 more)

### Community 9 - "Feedback Loop Tests"
Cohesion: 0.09
Nodes (36): ChangeRecord, run(), FakeClient, FakeCompletions, make_episode(), make_llm(), user_json(), _rubric() (+28 more)

### Community 10 - "Memory Manager Tests"
Cohesion: 0.11
Nodes (36): MemoryManager, save_line_voices(), seed_memory(), _line(), _llm(), _npc(), test_a_candidate_keeps_its_updates_when_promoted(), finish() (+28 more)

### Community 12 - "New Voices & Characters"
Cohesion: 0.10
Nodes (30): NewVoice, draft_voice_ids(), episode_character_ids(), is_auto_id(), is_unnamed(), load_new_voices(), review_voice_ids(), save_new_voices() (+22 more)

### Community 13 - "Progress & Pipeline Tests"
Cohesion: 0.10
Nodes (23): OcrReading, Progress, episode_status(), register_episode(), test_pipeline_reports_script_reviewer_spending(), _reading(), test_off_skips_identification_and_learns_no_characters(), test_turning_it_on_again_runs_the_stages() (+15 more)

### Community 14 - "Benchmark Suite"
Cohesion: 0.12
Nodes (34): align(), _approved(), _auto_pattern(), characters_at(), _decisions(), _events(), Gold, group_map() (+26 more)

### Community 15 - "Config Schema"
Cohesion: 0.08
Nodes (31): AudioConfig, AuditConfig, Band, BaselineConfig, BenchConfig, BudgetConfig, CleanupConfig, EpisodesConfig (+23 more)

### Community 16 - "Output Delivery & ASS"
Cohesion: 0.10
Nodes (22): OutputFolderError, deliver(), keep_both_path(), output_folder(), output_name(), resolve_conflict(), reveal_in_explorer(), _same_drive() (+14 more)

### Community 17 - "Series Management"
Cohesion: 0.11
Nodes (24): add_series(), cmd_series(), ConfigError, active_series(), list_series(), merge_sections(), parse_config(), _read_yaml() (+16 more)

### Community 18 - "Cast Engine"
Cohesion: 0.09
Nodes (17): CastEngine, _ffmpeg(), frame_path(), keep_boxes(), line_motion(), load_frame(), _mark_talking(), match() (+9 more)

### Community 19 - "Video Preview (mpv)"
Cohesion: 0.08
Nodes (5): fmt_time(), load_mpv(), PreviewWidget, TimelineSlider, test_preview_transport_controls()

### Community 20 - "Sprite Learning"
Cohesion: 0.10
Nodes (18): build_bank(), crop(), frame_time_ms(), get_engine(), group_unknowns(), _apply_labels(), apply_review_edits(), _check_talkers() (+10 more)

### Community 21 - "Memory Store"
Cohesion: 0.10
Nodes (9): glossary_usage(), glossary_zh_block(), MemoryStore, SpriteExemplar, _voices(), _clip(), _fake_embed(), test_bootstrap_seed_and_approve() (+1 more)

### Community 22 - "Evaluator Checks"
Cohesion: 0.10
Nodes (24): check(), SubtitleEvent, max_chars_for(), rubric_payload(), rule_checks(), RuleContext, script_payload(), line_input() (+16 more)

### Community 23 - "Character Cards"
Cohesion: 0.11
Nodes (21): card_info(), card_media(), CharacterCard, confirmed_box(), _cut_clip(), _cut_picture(), _episode_ids(), _frame() (+13 more)

### Community 24 - "Partial Review Service"
Cohesion: 0.12
Nodes (19): ReviewData, script_note(), PartialSuggestion, read_jsonl(), partial_review(), PartialResult, suggest(), load_draft() (+11 more)

### Community 25 - "OCR Engine & Geometry"
Cohesion: 0.10
Nodes (15): onnx_use_cuda(), line_span(), symmetric_span(), center_in_band(), create_engine(), _engine_key(), get_engine(), _line_mode() (+7 more)

### Community 26 - "Subtitle Style"
Cohesion: 0.14
Nodes (17): crop_path(), calibrate(), grow_line(), labels_near(), load_style(), propose_regions(), _region_features(), save_style() (+9 more)

### Community 27 - "Pipeline Runner & Locks"
Cohesion: 0.14
Nodes (3): job_lock(), _episode_log, Pipeline

### Community 28 - "CLI Episodes"
Cohesion: 0.12
Nodes (27): _ask(), build_pipeline(), _interactive(), _output_exists(), _resolve_on_exists(), add_add(), add_batch(), add_calibrate() (+19 more)

### Community 29 - "Episodes Screen"
Cohesion: 0.13
Nodes (4): choose_batch_on_exists(), job_busy(), EpisodesView, done()

### Community 30 - "Memory Proposals Apply"
Cohesion: 0.17
Nodes (6): MemoryProposal, now_iso(), ApplyMixin, ApplyResult, test_a_different_suggestion_for_the_same_term_still_comes_through(), gloss()

### Community 31 - "Stage Table & State"
Cohesion: 0.12
Nodes (12): StageState, counts_text(), write_report(), BatchItem, Runner, _lazy(), review_outputs(), run_stage() (+4 more)

### Community 32 - "Voice Learning & Evidence"
Cohesion: 0.13
Nodes (18): is_auto_episode(), trusted_auto_lines(), usable_line(), Config, auto_clips(), auto_gate(), AutoGate, build_centroids() (+10 more)

### Community 33 - "Media (ffmpeg) Infra"
Cohesion: 0.15
Nodes (20): available_encoders(), extract_clip(), extract_frame(), git(), has_video_stream(), imread(), imwrite_png(), iter_gray_frames() (+12 more)

### Community 34 - "Audit & Dreaming Screens"
Cohesion: 0.09
Nodes (6): AuditView, done(), DreamingView, _summary(), confirm(), show_error()

### Community 35 - "Settings & Run Panel"
Cohesion: 0.10
Nodes (5): label(), reset_all(), save(), sequence(), SettingsView

### Community 36 - "Script Review & OCR Fix"
Cohesion: 0.10
Nodes (19): chunked(), load_prompt(), LineDecision, apply_fixes(), batch_payload(), OcrFixChange, OcrFixResponse, run() (+11 more)

### Community 37 - "Frozen Baseline"
Cohesion: 0.13
Nodes (18): baseline_dir(), complete(), freeze(), freeze_episode(), freeze_finished(), _git_head(), _manifest(), memory_at_run() (+10 more)

### Community 38 - "Bootstrap Seed"
Cohesion: 0.12
Nodes (21): approve_seed(), _episode1_lines(), generate_seed(), load_seed(), name_pinyin(), save_clip(), save_seed(), seed_path() (+13 more)

### Community 39 - "YAML Comment-Preserving Edit"
Cohesion: 0.14
Nodes (17): file_comment(), _block_end(), delete_key(), _dump(), _find(), _get(), _is_child(), _path() (+9 more)

### Community 41 - "Speaker Benchmark"
Cohesion: 0.12
Nodes (17): is_flagged(), stratified(), _acc(), benchmark_episodes(), BenchmarkResult, _copy_reviewer_context(), _drop_heavy_files(), EpisodeScore (+9 more)

### Community 42 - "OCR Benchmark"
Cohesion: 0.12
Nodes (15): _covered(), EpisodeOcrScore, _existing_events(), gold_lines(), load_key(), _norm(), ocr_episodes(), OcrBenchResult (+7 more)

### Community 43 - "Episode Registry"
Cohesion: 0.16
Nodes (9): cmd_status(), Episode, derived_status(), Registry, test_add_register_duplicates_and_numbers(), test_missing_source_and_relink(), test_no_video_stream_is_skipped(), test_register_rejects_missing_and_clashing_numbers() (+1 more)

### Community 44 - "Episode Context & Finish"
Cohesion: 0.15
Nodes (10): _learn(), run(), calibrate(), _review_run(), run(), run(), EpisodeContext, test_archived_voices_are_not_matched() (+2 more)

### Community 45 - "Ingest & Change Detection"
Cohesion: 0.16
Nodes (19): binarize(), Change, change_fraction(), detect_changes(), draw_band(), fuse(), has_subtitle(), outlined_ratio() (+11 more)

### Community 46 - "Character Browser"
Cohesion: 0.12
Nodes (5): CharacterBrowser, CharacterStrip, describe(), _pixmap(), ClipPlayer

### Community 47 - "Kernel Errors"
Cohesion: 0.15
Nodes (18): BudgetExceeded, EpisodeLockedError, EpisodeNotFoundError, JobRunningError, LLMCallError, LLMOutputError, MemoryLockedError, ModelUnavailableError (+10 more)

### Community 48 - "Translate Stage"
Cohesion: 0.14
Nodes (13): _kept_evaluation(), Evaluation, Window, _best(), context_row(), ProposalDraft, rank_attempt(), _same() (+5 more)

### Community 49 - "Dreaming"
Cohesion: 0.16
Nodes (20): read_json(), sha256_json(), apply_dream(), describe(), dream(), DreamGlossary, DreamItem, DreamOutput (+12 more)

### Community 50 - "Character Updates"
Cohesion: 0.12
Nodes (15): _alias_zh(), CharacterChange, CharacterUpdateResponse, check(), _clip(), _has_word(), _introduces(), _pairs_block() (+7 more)

### Community 51 - "Voice Candidates"
Cohesion: 0.12
Nodes (5): load_line_voices(), CandidatesMixin, _Run, speaker_lines(), episode_number()

### Community 52 - "New Series Dialog"
Cohesion: 0.13
Nodes (5): NewSeriesDialog, StyleDialog, test_new_series_dialog_asks_for_the_default_pronoun_pair(), test_new_series_dialog_creates_a_translation_style(), test_new_series_work_folder_can_be_chosen()

### Community 54 - "Voice Match"
Cohesion: 0.16
Nodes (14): new_voice_id(), classify(), compute_centroids(), Embedder, find_new_voices(), get_embedder(), group_voices(), l2_normalize() (+6 more)

### Community 55 - "Bench Run Sandbox"
Cohesion: 0.16
Nodes (13): checkout_memory(), _drop_heavy(), _frozen_inputs(), _install_review(), _null(), _rerun_episode(), run(), _run_info() (+5 more)

### Community 56 - "Translation Registers"
Cohesion: 0.18
Nodes (13): check_id(), list_registers(), load_register(), _parse(), Register, register_dir(), save_register(), split_terms() (+5 more)

### Community 57 - "Series-1 Voice Config"
Cohesion: 0.08
Nodes (24): voice, accept_score, confusable_similarity, learn_auto_allowed_flags, learn_auto_max_drop, learn_auto_min_margin, learn_auto_min_score, learn_auto_min_test_lines (+16 more)

### Community 58 - "Review Flags & Filters"
Cohesion: 0.11
Nodes (5): flag_label(), loaded(), opened(), flag_group(), needs_attention()

### Community 60 - "Series-1 Cast Config"
Cohesion: 0.09
Nodes (23): cast, add_similarity, detector_model, embed_model, enabled, frame_width, learn, match_margin (+15 more)

### Community 61 - "Event Building"
Cohesion: 0.17
Nodes (13): absorb_fragments(), build_events(), flag_non_dialogue(), frames_on_screen(), _Group, group_readings(), _median(), _merge_flicker() (+5 more)

### Community 62 - "Video Render"
Cohesion: 0.18
Nodes (12): _ass_text(), build_mask_filter(), check_fonts(), choose_encoder(), encoder_args(), ffmpeg_args(), font_files(), preview_ass() (+4 more)

### Community 63 - "Architecture Guard Test"
Cohesion: 0.17
Nodes (8): _breaches(), _imports(), _module_of(), _submodules(), test_every_package_is_a_known_module_with_a_public_api(), test_modules_import_each_other_only_through_their_api_and_downwards(), test_the_app_reaches_the_core_only_through_its_services(), test_the_core_never_imports_the_app_or_qt()

### Community 64 - "CLI Entry & Logging"
Cohesion: 0.14
Nodes (15): main(), _setup_logging(), prompt_hash(), load_config(), _load_env(), update_config_values(), project(), test_cli_errors_are_json_with_codes() (+7 more)

### Community 66 - "Pinned Requirements"
Cohesion: 0.10
Nodes (20): jieba 0.42.1, numpy 2.5.3, onnxruntime-gpu 1.30.0, openai 3.22.1, opencv-python-headless 5.0.0.93, pillow 12.3.0, pydantic 2.13.5, pypinyin 0.55.0 (+12 more)

### Community 67 - "Briefings & Style Rules"
Cohesion: 0.21
Nodes (13): briefings_dir(), cap_style_rules(), IndexEntry, list_episode_briefings(), _read(), read_episode_briefing(), read_index(), read_story() (+5 more)

### Community 68 - "Review Character Editor"
Cohesion: 0.12
Nodes (8): done(), save(), load(), done(), done(), failed(), done(), episode_id()

### Community 69 - "Top-level Config Keys"
Cohesion: 0.10
Nodes (19): budget, max_cost_per_episode, cleanup, auto, device, episodes, number_patterns, video_extensions (+11 more)

### Community 70 - "Job Locks"
Cohesion: 0.16
Nodes (8): running_jobs(), _atomic_write(), atomic_write_bytes(), lock_holder(), pid_alive(), _replace_with_retry(), run(), write_silence()

### Community 71 - "Settings Schema Introspection"
Cohesion: 0.14
Nodes (9): _code_notes(), fields(), walk(), known_sets(), target(), _unwrap(), value_at(), with_known_sets() (+1 more)

### Community 72 - "Bootstrap & Memory Services"
Cohesion: 0.15
Nodes (3): load(), all_similarities(), voice_clips()

### Community 73 - "Memory Prompt Prefix"
Cohesion: 0.22
Nodes (10): characters_block(), corrections_block(), evaluator_prefix(), glossary_block(), ocr_fix_prefix(), pronoun_block(), reviewer_corrections(), story_block() (+2 more)

### Community 74 - "Memory Banks Writing"
Cohesion: 0.14
Nodes (6): _add_exemplars(), BanksMixin, _drop_exemplar(), _keep_best(), _record_votes(), _undo_episode()

### Community 75 - "LLM Provider Config"
Cohesion: 0.11
Nodes (18): api_key_env, base_url, model, llm, max_retries, max_retry_wait_s, providers, temperature (+10 more)

### Community 76 - "OCR Preprocess Crop"
Cohesion: 0.18
Nodes (11): crop_view(), to_band_coords(), _band(), _event(), _gold(), test_benchmark_scores_by_time_overlap(), test_crop_view_places_what_ocr_read_in_the_band(), test_mask_keeps_outlined_subtitle_and_drops_props() (+3 more)

### Community 77 - "Pinyin Engine"
Cohesion: 0.20
Nodes (8): is_han(), heteronyms(), PinyinEngine, PolyphoneChoice, PolyphoneResponse, resolve_polyphones(), run(), Token

### Community 78 - "Voice Learning Tests"
Cohesion: 0.23
Nodes (12): learn_voices(), LearnResult, _auto_episode(), _episode(), _fake_embed(), test_auto_lines_pass_only_when_every_signal_agrees(), test_auto_lines_that_hurt_accuracy_are_not_learned(), test_auto_lines_that_keep_accuracy_are_learned() (+4 more)

### Community 79 - "Render Config"
Cohesion: 0.12
Nodes (17): render, avg_char_width, blur_radius, encoder, font_dir, font_name, line_spacing, mask (+9 more)

### Community 80 - "Text Utilities"
Cohesion: 0.20
Nodes (7): balanced_wrap(), found_terms(), nfc(), split_explicit_lines(), visible_chars(), wrap_words(), wrap_lines()

### Community 81 - "Episode State & Cleanup"
Cohesion: 0.23
Nodes (5): cleanup(), load_state(), save_state(), state_path(), test_cleanup_keeps_script_and_marks_purged()

### Community 82 - "Memory & Translation Prompts"
Cohesion: 0.19
Nodes (8): Style rules, Cổ trang / tiên hiệp register (Hán-Việt terms), identify / default_pair template toggle, Memory proposals (glossary / pronoun_pair / character), Pronoun matrix, Retries with earlier_attempts and evaluator_suggestion, Reviewer corrections, Speaker rules per voice status (fixed/confusable/disputed/new_voice/unknown/too_short)

### Community 83 - "OCR Boxes"
Cohesion: 0.16
Nodes (8): OcrBox, keep_cjk(), filter_boxes(), group_rows(), reading_from_boxes(), _to_box(), _box(), test_box_filter_drops_short_and_distant_boxes()

### Community 86 - "CLI Commands"
Cohesion: 0.17
Nodes (7): add_dream(), add_sprites(), add_voices(), cmd_dream(), cmd_sprites(), cmd_voices(), build_parser()

### Community 87 - "Series-1 Band Config"
Cohesion: 0.13
Nodes (15): bottom, left, right, top, video, band_frames, change_threshold, empty_text_ratio (+7 more)

### Community 88 - "Character Lifecycle"
Cohesion: 0.32
Nodes (12): CharacterFate, new_voices_block(), _lines(), _setup(), _status(), test_consecutive_episodes_keep_a_character(), test_first_run_counts_earlier_episodes(), test_generic_characters_are_never_matched_or_learned() (+4 more)

### Community 89 - "Probation"
Cohesion: 0.20
Nodes (5): candidate_looks(), candidate_voice(), check_return(), ReturnCheck, _unit()

### Community 93 - "Prices Editor"
Cohesion: 0.16
Nodes (3): _num_text(), PricesEditor, ProvidersEditor

### Community 94 - "Episode Fingerprints"
Cohesion: 0.16
Nodes (6): sha256_bytes(), detect_number(), fingerprint(), scan_paths(), test_detect_number(), test_fingerprint_reads_head_and_tail()

### Community 95 - "Memory Store Models"
Cohesion: 0.15
Nodes (5): Character, GlossaryEntry, LogEntry, PronounPair, VoiceEntry

### Community 98 - "Price Table Keys"
Cohesion: 0.15
Nodes (13): input, input_cached, output, input, input_cached, output, input, input_cached (+5 more)

### Community 99 - "Memory Config Keys"
Cohesion: 0.15
Nodes (13): memory, aliases_max, archive_after_absent, character_lifecycle, character_updates, correction_examples, description_max_chars, dream_max_lines (+5 more)

### Community 100 - "Series-1 series.yaml"
Cohesion: 0.15
Nodes (12): baseline, name, bench, baseline, non_dialogue, box_center_tolerance, box_height_tolerance, enabled (+4 more)

### Community 101 - "Sprite Check"
Cohesion: 0.23
Nodes (7): best_match(), candidates_for(), decide(), load_templates(), run(), frame_reader(), save_template()

### Community 102 - "Settings Field Controls"
Cohesion: 0.18
Nodes (5): _decimals(), Field, set_float(), add(), FieldSpec

### Community 103 - "Device Detection"
Cohesion: 0.23
Nodes (4): describe(), onnx_cuda_available(), torch_cuda_available(), torch_device()

### Community 105 - "Series-1 OCR Config"
Cohesion: 0.18
Nodes (11): ocr, fragment_max_samples, fragment_merge_similarity, mask_image, mask_scale, merge_max_edit_distance, min_confidence, preprocess (+3 more)

### Community 106 - "Series-1 Script Review Config"
Cohesion: 0.18
Nodes (11): script_review, enabled, example_limit, max_remove_share, memory_auto_remove_min, memory_max_han, remove_confidence, repeat_merge_gap_ms (+3 more)

### Community 107 - "App Entry Point"
Cohesion: 0.27
Nodes (4): choose_platform(), install_fonts(), install_translator(), main()

### Community 111 - "Translate Config"
Cohesion: 0.22
Nodes (9): translate, max_cps, max_line_chars, max_lines_per_event, max_retries, picture_evidence, picture_veto, pronoun_terms (+1 more)

### Community 112 - "Briefing Generation"
Cohesion: 0.33
Nodes (6): BriefingResponse, compress_story(), generate_briefing(), script_text(), StoryResponse, word_count()

### Community 117 - "Evaluator Rubric"
Cohesion: 0.25
Nodes (4): judge(), RubricLine, RubricResponse, RuleFailure

### Community 120 - "Series-1 Cast"
Cohesion: 0.52
Nodes (7): series-1 cast.md, Bắc Tỵ, Cơ Bá Thường, Cơ Tử, Sở Lưu Cần, Sử Thượng Phi, Tiểu Lượng

### Community 122 - "Audit Config"
Cohesion: 0.33
Nodes (6): audit, ignore_flags, include_human, max_disagreements, min_per_stratum, sample_size

### Community 123 - "Text Similarity"
Cohesion: 0.40
Nodes (3): edit_distance(), normalize_zh(), relatedness()

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
- **28 isolated node(s):** `subagent`, `Font draws 了 like digit 7`, `Stray screen text (楚, 姬, 史, 林, 绝密, 000)`, `Show wording that looks like stray text (史 for 屎, 鸡道, 姬叔)`, `Similar-looking misreadings (干, 参/善, 美)` (+23 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1006 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ReviewedLine` connect `Review Data & Cards` to `Main Window & Services`, `LLM Client & Costs`, `App Package & Jobs`, `Cast Models & Tests`, `Memory Manager Rows`, `Audit Sampling`, `Feedback Loop Tests`, `Memory Manager Tests`, `New Voices & Characters`, `Progress & Pipeline Tests`, `Benchmark Suite`, `Output Delivery & ASS`, `Sprite Learning`, `Memory Store`, `Evaluator Checks`, `Character Cards`, `Partial Review Service`, `Memory Proposals Apply`, `Stage Table & State`, `Voice Learning & Evidence`, `Speaker Benchmark`, `OCR Benchmark`, `Episode Context & Finish`, `Kernel Errors`, `Dreaming`, `Character Updates`, `Voice Candidates`, `Review On-Screen Cast`, `Review Flags & Filters`, `Video Render`, `Briefings & Style Rules`, `Memory Prompt Prefix`, `OCR Preprocess Crop`, `Voice Learning Tests`, `Episode Memory Update`, `Character Lifecycle`, `Probation`, `Audit Bar`, `Memory Aux Writes`, `Briefing Generation`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ReviewedLine` (e.g. with `_finish()` and `test_pipeline_records_what_the_reviewer_removed_and_kept()`) actually correct?**
  _`ReviewedLine` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `subagent`, `Font draws 了 like digit 7`, `Stray screen text (楚, 姬, 史, 林, 绝密, 000)` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Main Window & Services` be split into smaller, more focused modules?**
  _Cohesion score 0.07525807525807526 - nodes in this community are weakly interconnected._
- **Why does `Config` connect `Voice Learning & Evidence` to `LLM Client & Costs`, `Cast Models & Tests`, `Memory Manager Rows`, `Audit Sampling`, `Feedback Loop Tests`, `Memory Manager Tests`, `Progress & Pipeline Tests`, `Benchmark Suite`, `Config Schema`, `Output Delivery & ASS`, `Series Management`, `Cast Engine`, `Sprite Learning`, `Memory Store`, `Evaluator Checks`, `Character Cards`, `Partial Review Service`, `OCR Engine & Geometry`, `CLI Episodes`, `Stage Table & State`, `Frozen Baseline`, `Bootstrap Seed`, `Speaker Benchmark`, `OCR Benchmark`, `Episode Context & Finish`, `Kernel Errors`, `Translate Stage`, `Dreaming`, `Character Updates`, `Voice Match`, `Bench Run Sandbox`, `Translation Registers`, `Event Building`, `Video Render`, `CLI Entry & Logging`, `Settings Schema Introspection`, `Pinyin Engine`, `Voice Learning Tests`, `Text Utilities`, `Episode Fingerprints`, `Device Detection`, `Briefing Generation`, `File Lock`, `Evaluator Rubric`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Config` (e.g. with `fields()` and `value_at()`) actually correct?**
  _`Config` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `LLM Client & Costs` be split into smaller, more focused modules?**
  _Cohesion score 0.06734867860187553 - nodes in this community are weakly interconnected._