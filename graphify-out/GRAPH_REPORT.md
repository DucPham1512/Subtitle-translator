# Graph Report - Subtitle-translator  (2026-11-03)

## Corpus Check
- 214 files · ~169,481 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .qm 2, .example 1)

## Summary
- 3320 nodes · 11407 edges · 143 communities (113 shown, 30 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 690 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `94e91df4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Services
- make_llm
- App Package & Jobs
- test_ocr_preprocess.py
- Memory Screen
- CastCanvas
- ReviewedLine
- Memory Manager Rows
- bench/audit.py
- test_feedback_loop.py
- seed_memory
- Bootstrap Wizard View
- test_review_state.py
- models.py
- Benchmark Suite
- Config Schema
- SubtitleEvent
- workspace/series.py
- cast.py
- Video Preview (mpv)
- test_cast.py
- Memory Store
- models.py
- card.py
- ._loaded
- OCR Engine & Geometry
- Subtitle Style
- Pipeline Runner & Locks
- kernel/__init__.py
- Episodes Screen
- Memory Proposals Apply
- render.py
- voice/learning.py
- core.py
- DreamingView
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
- test_audit.py
- Architecture Guard Test
- cast/learning.py
- Frame Selector Widget
- Pinned Requirements
- Briefings & Style Rules
- delivery.py
- Top-level Config Keys
- normalize_zh
- Settings Schema Introspection
- NewCharacterDialog
- test_translate_review.py
- Memory Banks Writing
- LLM Provider Config
- test_partial_review.py
- briefing_gen.py
- Voice Learning Tests
- Render Config
- Config
- memory/__init__.py
- Memory & Translation Prompts
- views/episodes.py
- ._field
- Tag Editor Widget
- read_jsonl
- Series-1 Band Config
- test_character_lifecycle.py
- workspace/__init__.py
- .episode_update
- test_probation.py
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
- AuditView
- Series-1 OCR Config
- Series-1 Script Review Config
- pinyin_gen.py
- JobRunner
- app/__main__.py
- sprite.py
- Translate Config
- measure.py
- test_character_card.py
- CastPanel
- Background Workers
- cast/__init__.py
- BandView
- Vietnamese UI Fill
- EntryTable
- Series-1 Cast
- Raw YAML Dialog
- Audit Config
- test_new_voices.py
- Sprite Config
- Series-1 Review Prompt
- Paths
- Audio Config
- Output Config
- Review Config
- Windows Config
- Briefing & Story Prompts
- _no_real_ffmpeg
- Project Metadata

## God Nodes (most connected - your core abstractions)
1. `ReviewedLine` - 164 edges
2. `Config` - 141 edges
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
- `load()` --indirect_call--> `episode_id()`  [INFERRED]
  app/views/review.py → subagent/workspace/episodes.py
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

## Communities (143 total, 30 thin omitted)

### Community 1 - "make_llm"
Cohesion: 0.12
Nodes (12): LLMCallError, compute_cost(), _daily_quota(), _describe(), LLMClient, _retryable(), schema_instruction(), _server_delay() (+4 more)

### Community 2 - "App Package & Jobs"
Cohesion: 0.10
Nodes (5): error_message(), ReviewData, ClipPlayer, fmt_ms(), show_error()

### Community 3 - "test_ocr_preprocess.py"
Cohesion: 0.16
Nodes (13): crop_view(), to_band_coords(), _band(), _box(), _event(), _gold(), test_benchmark_scores_by_time_overlap(), test_box_filter_drops_short_and_distant_boxes() (+5 more)

### Community 4 - "Memory Screen"
Cohesion: 0.07
Nodes (6): _item(), MemoryView, done(), PairDialog, _update_text(), run_async()

### Community 6 - "ReviewedLine"
Cohesion: 0.11
Nodes (24): ReviewIncompleteError, ReviewedLine, apply_script_review(), build_draft(), draft_path(), finish_review(), flag_group(), load_draft() (+16 more)

### Community 7 - "Memory Manager Rows"
Cohesion: 0.15
Nodes (24): contains_term(), merge_proposals(), replaced_term(), reviewed_glossary(), CommitInfo, Conflict, describe_update(), dumps_aliases() (+16 more)

### Community 8 - "bench/audit.py"
Cohesion: 0.08
Nodes (30): auditable(), auditable_lines(), AuditReport, build_report(), disagreements(), EpisodeAudit, gold_speakers(), is_flagged() (+22 more)

### Community 9 - "test_feedback_loop.py"
Cohesion: 0.14
Nodes (28): read_jsonl(), run(), user_json(), _rubric(), evaluator(), test_a_passing_line_keeps_the_evaluators_suggestion_for_the_reviewer(), test_reading_speed_is_flagged_not_retried(), test_retry_sends_history_and_suggestion() (+20 more)

### Community 10 - "seed_memory"
Cohesion: 0.11
Nodes (35): EditRecord, MemoryManager, seed_memory(), _line(), _llm(), _npc(), test_a_candidate_keeps_its_updates_when_promoted(), finish() (+27 more)

### Community 12 - "test_review_state.py"
Cohesion: 0.08
Nodes (24): all_correct_mark(), line_matches(), LineFilter, LineHistory, marked_count(), next_npc_number(), next_pending(), next_unmarked() (+16 more)

### Community 13 - "models.py"
Cohesion: 0.17
Nodes (15): register_episode(), test_turning_it_on_again_runs_the_stages(), calls(), _pipeline(), stubs(), ingest(), ocr(), test_auto_mode_end_to_end_and_output_conflict() (+7 more)

### Community 14 - "Benchmark Suite"
Cohesion: 0.09
Nodes (40): gold_lines(), align(), _approved(), _auto_pattern(), characters_at(), _decisions(), _events(), Gold (+32 more)

### Community 15 - "Config Schema"
Cohesion: 0.13
Nodes (23): AudioConfig, AuditConfig, BaselineConfig, BenchConfig, BudgetConfig, CleanupConfig, EpisodesConfig, EvaluateConfig (+15 more)

### Community 16 - "SubtitleEvent"
Cohesion: 0.19
Nodes (11): SubtitleEvent, Window, crop_path(), WindowsConfig, max_chars_for(), line_input(), build_windows(), run() (+3 more)

### Community 17 - "workspace/series.py"
Cohesion: 0.09
Nodes (24): add_series(), cmd_series(), running_jobs(), EpisodeLockedError, JobRunningError, StageError, SubagentError, mode_prompt() (+16 more)

### Community 18 - "cast.py"
Cohesion: 0.10
Nodes (17): CastEngine, _ffmpeg(), frame_path(), get_engine(), keep_boxes(), line_motion(), _mark_talking(), middle_frames() (+9 more)

### Community 19 - "Video Preview (mpv)"
Cohesion: 0.07
Nodes (6): fmt_time(), load_mpv(), PreviewWidget, TimelineSlider, _FakePlayer, test_preview_transport_controls()

### Community 20 - "test_cast.py"
Cohesion: 0.15
Nodes (16): compute_edits(), _text(), FakeEngine, _frame(), _lines(), test_auto_mode_learns_only_from_trusted_lines(), test_backfill_runs_cast_where_missing_then_learns(), fake_cast() (+8 more)

### Community 21 - "Memory Store"
Cohesion: 0.08
Nodes (15): main(), _setup_logging(), glossary_usage(), glossary_zh_block(), new_voices_block(), MemoryStore, SpriteExemplar, _voices() (+7 more)

### Community 22 - "models.py"
Cohesion: 0.13
Nodes (15): CastBoxEdit, CastDetection, CastLine, ChangeRecord, test_on_screen_checked_mark(), line(), test_translator_sees_the_cast(), _line() (+7 more)

### Community 23 - "card.py"
Cohesion: 0.17
Nodes (8): card_media(), CharacterCard, _cut_clip(), _cut_picture(), _frame(), pin_card(), pin_dir(), _source()

### Community 24 - "._loaded"
Cohesion: 0.15
Nodes (3): flag_label(), loaded(), opened()

### Community 25 - "OCR Engine & Geometry"
Cohesion: 0.08
Nodes (17): OcrBox, line_span(), symmetric_span(), create_engine(), _engine_key(), filter_boxes(), get_engine(), group_rows() (+9 more)

### Community 26 - "Subtitle Style"
Cohesion: 0.12
Nodes (20): calibrate(), grow_line(), labels_near(), load_style(), propose_regions(), _region_features(), save_style(), segment_mask() (+12 more)

### Community 27 - "Pipeline Runner & Locks"
Cohesion: 0.13
Nodes (4): job_lock(), _episode_log, Pipeline, test_pipeline_reports_script_reviewer_spending()

### Community 28 - "kernel/__init__.py"
Cohesion: 0.09
Nodes (12): MemoryLockedError, append_jsonl(), _atomic_write(), atomic_write_json(), atomic_write_text(), FileLock, lock_holder(), now_iso() (+4 more)

### Community 29 - "Episodes Screen"
Cohesion: 0.11
Nodes (5): choose_batch_on_exists(), choose_on_exists(), job_busy(), EpisodesView, confirm()

### Community 30 - "Memory Proposals Apply"
Cohesion: 0.17
Nodes (4): character_proposals(), MemoryProposal, ApplyMixin, ApplyResult

### Community 31 - "render.py"
Cohesion: 0.18
Nodes (12): build_mask_filter(), check_fonts(), choose_encoder(), encoder_args(), ffmpeg_args(), font_files(), preview_ass(), render() (+4 more)

### Community 32 - "voice/learning.py"
Cohesion: 0.18
Nodes (14): auto_gate(), AutoGate, build_centroids(), Clip, embed_clips(), episode_samples(), EvalReport, evaluate() (+6 more)

### Community 33 - "core.py"
Cohesion: 0.17
Nodes (17): available_encoders(), extract_clip(), extract_frame(), git(), has_video_stream(), imread(), iter_gray_frames(), missing_binaries() (+9 more)

### Community 35 - "Settings & Run Panel"
Cohesion: 0.12
Nodes (4): reset_all(), save(), sequence(), SettingsView

### Community 36 - "Script Review & OCR Fix"
Cohesion: 0.10
Nodes (25): script_note(), ScriptDecision, is_han(), LineDecision, ScriptReviewConfig, examples_block(), find_repeats(), han_count() (+17 more)

### Community 37 - "Frozen Baseline"
Cohesion: 0.16
Nodes (14): baseline_dir(), complete(), freeze(), freeze_episode(), freeze_finished(), _git_head(), _manifest(), memory_at_run() (+6 more)

### Community 38 - "Bootstrap Seed"
Cohesion: 0.10
Nodes (20): approve_seed(), _episode1_lines(), generate_seed(), load_seed(), name_pinyin(), save_clip(), save_seed(), seed_path() (+12 more)

### Community 39 - "YAML Comment-Preserving Edit"
Cohesion: 0.14
Nodes (17): file_comment(), _block_end(), delete_key(), _dump(), _find(), _get(), _is_child(), _path() (+9 more)

### Community 40 - "._load_editor"
Cohesion: 0.16
Nodes (3): _bullets(), show(), _section()

### Community 41 - "test_render_delivery.py"
Cohesion: 0.11
Nodes (15): balanced_wrap(), split_explicit_lines(), wrap_words(), _ass_text(), build_ass(), _color(), Layout, _style() (+7 more)

### Community 42 - "ocr_benchmark.py"
Cohesion: 0.11
Nodes (16): _covered(), EpisodeOcrScore, _existing_events(), load_key(), _norm(), ocr_episodes(), OcrBenchResult, _overlap() (+8 more)

### Community 43 - "Episode"
Cohesion: 0.10
Nodes (20): save(), EpisodeNotFoundError, SourceMissingError, Episode, sha256_bytes(), AddCandidate, derived_status(), detect_number() (+12 more)

### Community 44 - "read_jsonl"
Cohesion: 0.17
Nodes (13): _learn(), run(), counts_text(), write_report(), _review_run(), EpisodeContext, make_episode(), test_stage_records_cast_and_talker() (+5 more)

### Community 45 - "Ingest & Change Detection"
Cohesion: 0.20
Nodes (16): binarize(), Change, change_fraction(), detect_changes(), draw_band(), fuse(), has_subtitle(), outlined_ratio() (+8 more)

### Community 46 - "Character Browser"
Cohesion: 0.13
Nodes (4): CharacterBrowser, CharacterStrip, describe(), _pixmap()

### Community 47 - "Runner"
Cohesion: 0.20
Nodes (8): StageState, hash_path(), sha256_json(), prompt_hash(), Runner, review_outputs(), StageDef, ocr_hash()

### Community 48 - "memory/__init__.py"
Cohesion: 0.09
Nodes (20): Evaluation, LineTranslation, visible_chars(), judge(), llm_rubric(), rubric_payload(), RubricLine, RubricResponse (+12 more)

### Community 49 - "Dreaming"
Cohesion: 0.10
Nodes (27): apply_dream(), describe(), dream(), _dream_variable(), DreamGlossary, DreamItem, DreamOutput, DreamPronoun (+19 more)

### Community 50 - "character_updates.py"
Cohesion: 0.11
Nodes (18): _alias_zh(), _character_change(), CharacterChange, CharacterUpdateResponse, check(), _clip(), _has_word(), _introduces() (+10 more)

### Community 51 - ".probation"
Cohesion: 0.08
Nodes (10): load_line_voices(), CandidatesMixin, _Run, candidate_looks(), candidate_voice(), check_return(), ReturnCheck, speaker_lines() (+2 more)

### Community 52 - "New Series Dialog"
Cohesion: 0.11
Nodes (5): NewSeriesDialog, StyleDialog, test_new_series_dialog_asks_for_the_default_pronoun_pair(), test_new_series_dialog_creates_a_translation_style(), test_new_series_work_folder_can_be_chosen()

### Community 53 - "._show_card"
Cohesion: 0.10
Nodes (8): done(), done(), failed(), load(), done(), done(), failed(), done()

### Community 54 - "voice.py"
Cohesion: 0.17
Nodes (15): load(), VoiceConfig, all_similarities(), classify(), compute_centroids(), Embedder, get_embedder(), l2_normalize() (+7 more)

### Community 55 - "Bench Run Sandbox"
Cohesion: 0.16
Nodes (13): checkout_memory(), _drop_heavy(), _frozen_inputs(), _install_review(), _null(), _rerun_episode(), run(), _run_info() (+5 more)

### Community 56 - "load_config"
Cohesion: 0.17
Nodes (13): check_id(), list_registers(), load_register(), _parse(), Register, register_dir(), save_register(), split_terms() (+5 more)

### Community 57 - "Series-1 Voice Config"
Cohesion: 0.08
Nodes (24): voice, accept_score, confusable_similarity, learn_auto_allowed_flags, learn_auto_max_drop, learn_auto_min_margin, learn_auto_min_score, learn_auto_min_test_lines (+16 more)

### Community 59 - "Band"
Cohesion: 0.18
Nodes (4): center_in_band(), Band, test_band_pixels_are_even_and_inside_frame(), test_band_centres_by_widening_the_short_side()

### Community 60 - "Series-1 Cast Config"
Cohesion: 0.09
Nodes (23): cast, add_similarity, detector_model, embed_model, enabled, frame_width, learn, match_margin (+15 more)

### Community 61 - "test_parser_stages.py"
Cohesion: 0.11
Nodes (22): OcrReading, absorb_fragments(), build_events(), flag_non_dialogue(), frames_on_screen(), _Group, group_readings(), _median() (+14 more)

### Community 62 - "test_audit.py"
Cohesion: 0.19
Nodes (15): draw_sample(), save_marks(), AuditSample, _episode(), pathlib_name(), test_gold_answers_and_benchmark(), fake_stage(), test_human_reviewed_episodes_are_not_audited_by_default() (+7 more)

### Community 63 - "Architecture Guard Test"
Cohesion: 0.17
Nodes (8): _breaches(), _imports(), _module_of(), _submodules(), test_every_package_is_a_known_module_with_a_public_api(), test_modules_import_each_other_only_through_their_api_and_downwards(), test_the_app_reaches_the_core_only_through_its_services(), test_the_core_never_imports_the_app_or_qt()

### Community 64 - "cast/learning.py"
Cohesion: 0.16
Nodes (9): group_unknowns(), _apply_labels(), _check_talkers(), _name_unknowns(), plan(), _Plan, SpriteLearnResult, trusted_speakers() (+1 more)

### Community 66 - "Pinned Requirements"
Cohesion: 0.10
Nodes (20): jieba 0.42.1, numpy 2.5.3, onnxruntime-gpu 1.30.0, openai 3.22.1, opencv-python-headless 5.0.0.93, pillow 12.3.0, pydantic 2.13.5, pypinyin 0.55.0 (+12 more)

### Community 67 - "Briefings & Style Rules"
Cohesion: 0.16
Nodes (13): briefings_dir(), cap_style_rules(), IndexEntry, list_episode_briefings(), _read(), read_index(), read_story(), read_style_rules() (+5 more)

### Community 68 - "delivery.py"
Cohesion: 0.17
Nodes (14): OutputExistsError, OutputFolderError, deliver(), keep_both_path(), output_folder(), output_name(), resolve_conflict(), reveal_in_explorer() (+6 more)

### Community 69 - "Top-level Config Keys"
Cohesion: 0.10
Nodes (19): budget, max_cost_per_episode, cleanup, auto, device, episodes, number_patterns, video_extensions (+11 more)

### Community 70 - "normalize_zh"
Cohesion: 0.31
Nodes (4): edit_distance(), nfc(), normalize_zh(), relatedness()

### Community 71 - "Settings Schema Introspection"
Cohesion: 0.18
Nodes (6): _code_notes(), known_sets(), target(), _unwrap(), value_at(), with_known_sets()

### Community 73 - "test_translate_review.py"
Cohesion: 0.17
Nodes (13): check(), SpeakerCandidates, rule_checks(), RuleContext, picture_veto(), test_picture_veto_disputes_the_voice(), _line(), rules() (+5 more)

### Community 74 - "Memory Banks Writing"
Cohesion: 0.14
Nodes (6): _add_exemplars(), BanksMixin, _drop_exemplar(), _keep_best(), _record_votes(), _undo_episode()

### Community 75 - "LLM Provider Config"
Cohesion: 0.11
Nodes (18): api_key_env, base_url, model, llm, max_retries, max_retry_wait_s, providers, temperature (+10 more)

### Community 76 - "test_partial_review.py"
Cohesion: 0.21
Nodes (13): EpisodeState, PartialSuggestion, partial_review(), _episode(), _line(), _sug_model(), test_a_speaker_set_by_an_earlier_partial_review_may_change_again(), test_partial_review_learns_this_episodes_voices() (+5 more)

### Community 77 - "briefing_gen.py"
Cohesion: 0.12
Nodes (15): chunked(), load_prompt(), BriefingResponse, compress_story(), generate_briefing(), script_text(), StoryResponse, ocr_fix_prefix() (+7 more)

### Community 78 - "Voice Learning Tests"
Cohesion: 0.17
Nodes (15): ModelUnavailableError, auto_clips(), reviewed_clips(), _auto_episode(), _episode(), _fake_embed(), test_auto_lines_pass_only_when_every_signal_agrees(), test_auto_lines_that_hurt_accuracy_are_not_learned() (+7 more)

### Community 79 - "Render Config"
Cohesion: 0.12
Nodes (17): render, avg_char_width, blur_radius, encoder, font_dir, font_name, line_spacing, mask (+9 more)

### Community 80 - "Config"
Cohesion: 0.15
Nodes (8): describe(), onnx_cuda_available(), onnx_use_cuda(), torch_cuda_available(), torch_device(), trusted_auto_lines(), usable_line(), Config

### Community 81 - "memory/__init__.py"
Cohesion: 0.13
Nodes (12): draft_voice_ids(), episode_character_ids(), is_auto_id(), is_unnamed(), load_new_voices(), new_voice_id(), review_voice_ids(), save_new_voices() (+4 more)

### Community 82 - "Memory & Translation Prompts"
Cohesion: 0.19
Nodes (8): Style rules, Cổ trang / tiên hiệp register (Hán-Việt terms), identify / default_pair template toggle, Memory proposals (glossary / pronoun_pair / character), Pronoun matrix, Retries with earlier_attempts and evaluator_suggestion, Reviewer corrections, Speaker rules per voice status (fixed/confusable/disputed/new_voice/unknown/too_short)

### Community 83 - "views/episodes.py"
Cohesion: 0.09
Nodes (7): agent_label(), stage_label(), status_label(), AddDialog, DropTable, done(), RunPanel

### Community 84 - "._field"
Cohesion: 0.15
Nodes (7): _decimals(), Field, set_float(), add(), fields(), walk(), FieldSpec

### Community 85 - "Tag Editor Widget"
Cohesion: 0.23
Nodes (3): text(), TagEditor, test_tag_editor_adds_removes_and_validates_numbers()

### Community 86 - "read_jsonl"
Cohesion: 0.12
Nodes (23): BudgetExceeded, LLMOutputError, CostRecord, build_messages(), missing_prices(), record_cost(), FakeClient, FakeCompletions (+15 more)

### Community 87 - "Series-1 Band Config"
Cohesion: 0.13
Nodes (15): bottom, left, right, top, video, band_frames, change_threshold, empty_text_ratio (+7 more)

### Community 88 - "test_character_lifecycle.py"
Cohesion: 0.20
Nodes (20): CharacterFate, characters_block(), evaluator_prefix(), glossary_block(), pronoun_block(), story_block(), style_block(), translator_prefix() (+12 more)

### Community 89 - "workspace/__init__.py"
Cohesion: 0.09
Nodes (13): cleanup(), collect_metrics(), episode_status(), _pct(), BatchItem, _lazy(), run_stage(), _source_key() (+5 more)

### Community 91 - "test_probation.py"
Cohesion: 0.25
Nodes (14): NewVoice, save_line_voices(), _finish(), _lines(), _talks(), test_a_candidate_not_back_in_time_is_dropped(), test_a_new_voice_waits_on_probation_and_is_promoted_when_it_comes_back(), test_a_review_npc_goes_on_probation_at_finish() (+6 more)

### Community 93 - "Prices Editor"
Cohesion: 0.18
Nodes (3): _num_text(), PricesEditor, ProvidersEditor

### Community 94 - "partial.py"
Cohesion: 0.20
Nodes (6): build_bank(), match(), PartialResult, _session_bank(), _sprites(), suggest()

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
Cohesion: 0.18
Nodes (23): MainWindow, validate(), PinyinLine, write_jsonl(), gate(), sample_events(), write_events(), qapp() (+15 more)

### Community 102 - "settings/__init__.py"
Cohesion: 0.12
Nodes (19): ConfigError, active_series(), find_root(), list_series(), load_config(), _load_env(), merge_sections(), parse_config() (+11 more)

### Community 104 - "AuditView"
Cohesion: 0.14
Nodes (3): label(), AuditView, done()

### Community 105 - "Series-1 OCR Config"
Cohesion: 0.18
Nodes (11): ocr, fragment_max_samples, fragment_merge_similarity, mask_image, mask_scale, merge_max_edit_distance, min_confidence, preprocess (+3 more)

### Community 106 - "Series-1 Script Review Config"
Cohesion: 0.18
Nodes (11): script_review, enabled, example_limit, max_remove_share, memory_auto_remove_min, memory_max_han, remove_confidence, repeat_merge_gap_ms (+3 more)

### Community 107 - "pinyin_gen.py"
Cohesion: 0.10
Nodes (17): Character, GlossaryEntry, LogEntry, VoiceEntry, heteronyms(), PinyinEngine, PolyphoneChoice, PolyphoneResponse (+9 more)

### Community 108 - "JobRunner"
Cohesion: 0.20
Nodes (3): JobRunner, test_run_panel_has_a_script_review_step(), __init__()

### Community 109 - "app/__main__.py"
Cohesion: 0.27
Nodes (4): choose_platform(), install_fonts(), install_translator(), main()

### Community 110 - "sprite.py"
Cohesion: 0.16
Nodes (11): best_match(), candidates_for(), decide(), load_templates(), run(), frame_reader(), save_template(), imwrite_png() (+3 more)

### Community 111 - "Translate Config"
Cohesion: 0.22
Nodes (9): translate, max_cps, max_line_chars, max_lines_per_event, max_retries, picture_evidence, picture_veto, pronoun_terms (+1 more)

### Community 112 - "measure.py"
Cohesion: 0.08
Nodes (36): _ask(), build_pipeline(), _interactive(), _output_exists(), _resolve_on_exists(), add_add(), add_batch(), add_calibrate() (+28 more)

### Community 113 - "test_character_card.py"
Cohesion: 0.22
Nodes (12): card_info(), confirmed_box(), _episode_ids(), shown_talking_box(), _cast(), _line(), _setup(), test_bootstrap_material_and_a_pinned_sample_come_first() (+4 more)

### Community 116 - "cast/__init__.py"
Cohesion: 0.21
Nodes (7): crop(), frame_time_ms(), load_frame(), apply_review_edits(), frame_embedder(), embed(), learn_sprites()

### Community 117 - "BandView"
Cohesion: 0.24
Nodes (4): BandView, to_pixmap(), test_cast_panel_shows_boxes_and_records_corrections(), test_greyscale_images_can_be_shown()

### Community 120 - "Series-1 Cast"
Cohesion: 0.52
Nodes (7): series-1 cast.md, Bắc Tỵ, Cơ Bá Thường, Cơ Tử, Sở Lưu Cần, Sử Thượng Phi, Tiểu Lượng

### Community 122 - "Audit Config"
Cohesion: 0.33
Nodes (6): audit, ignore_flags, include_human, max_disagreements, min_per_stratum, sample_size

### Community 123 - "test_new_voices.py"
Cohesion: 0.27
Nodes (7): find_new_voices(), group_voices(), _e(), _results(), test_group_voices_keeps_alike_voices_together(), test_new_voice_needs_enough_lines_and_an_unfamiliar_voice(), _unit()

### Community 124 - "Sprite Config"
Cohesion: 0.40
Nodes (5): sprite, enabled, match_threshold, scales, trigger_conf_below

### Community 125 - "Series-1 Review Prompt"
Cohesion: 0.40
Nodes (5): series-1 script review prompt notes, Font draws 了 like digit 7, Show wording that looks like stray text (史 for 屎, 鸡道, 姬叔), Similar-looking misreadings (干, 参/善, 美), Stray screen text (楚, 姬, 史, 林, 绝密, 000)

### Community 126 - "Paths"
Cohesion: 0.29
Nodes (5): job_lock_path(), approved_lines(), done_episodes(), new_edits(), Paths

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
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1029 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **30 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ReviewedLine` connect `ReviewedLine` to `Services`, `App Package & Jobs`, `test_ocr_preprocess.py`, `.character_updates`, `Memory Manager Rows`, `bench/audit.py`, `test_feedback_loop.py`, `seed_memory`, `test_review_state.py`, `Benchmark Suite`, `test_cast.py`, `Memory Store`, `models.py`, `card.py`, `._loaded`, `kernel/__init__.py`, `render.py`, `voice/learning.py`, `Script Review & OCR Fix`, `._load_editor`, `test_render_delivery.py`, `ocr_benchmark.py`, `read_jsonl`, `Runner`, `memory/__init__.py`, `Dreaming`, `character_updates.py`, `.probation`, `ReviewView`, `test_audit.py`, `cast/learning.py`, `Briefings & Style Rules`, `delivery.py`, `test_translate_review.py`, `test_partial_review.py`, `briefing_gen.py`, `Voice Learning Tests`, `Config`, `memory/__init__.py`, `test_character_lifecycle.py`, `workspace/__init__.py`, `.episode_update`, `test_probation.py`, `partial.py`, `AuditBar`, `Registry`, `test_character_card.py`, `cast/__init__.py`, `test_new_voices.py`, `Paths`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ReviewedLine` (e.g. with `_finish()` and `test_pipeline_records_what_the_reviewer_removed_and_kept()`) actually correct?**
  _`ReviewedLine` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `subagent`, `Font draws 了 like digit 7`, `Show wording that looks like stray text (史 for 屎, 鸡道, 姬叔)` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Services` be split into smaller, more focused modules?**
  _Cohesion score 0.08888888888888889 - nodes in this community are weakly interconnected._
- **Why does `Config` connect `Config` to `make_llm`, `ReviewedLine`, `Memory Manager Rows`, `bench/audit.py`, `seed_memory`, `Benchmark Suite`, `Config Schema`, `SubtitleEvent`, `workspace/series.py`, `cast.py`, `Memory Store`, `card.py`, `OCR Engine & Geometry`, `kernel/__init__.py`, `render.py`, `voice/learning.py`, `Frozen Baseline`, `Bootstrap Seed`, `test_render_delivery.py`, `ocr_benchmark.py`, `Episode`, `read_jsonl`, `Runner`, `memory/__init__.py`, `Dreaming`, `character_updates.py`, `voice.py`, `Bench Run Sandbox`, `load_config`, `test_parser_stages.py`, `test_audit.py`, `cast/learning.py`, `delivery.py`, `Settings Schema Introspection`, `test_partial_review.py`, `briefing_gen.py`, `Voice Learning Tests`, `._field`, `read_jsonl`, `partial.py`, `settings/__init__.py`, `pinyin_gen.py`, `measure.py`, `test_character_card.py`, `cast/__init__.py`, `Paths`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Config` (e.g. with `fields()` and `value_at()`) actually correct?**
  _`Config` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `make_llm` be split into smaller, more focused modules?**
  _Cohesion score 0.11904761904761904 - nodes in this community are weakly interconnected._