# Graph Report - Subtitle-translator  (2026-11-03)

## Corpus Check
- 214 files · ~169,140 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .qm 2, .example 1)

## Summary
- 3302 nodes · 11350 edges · 137 communities (113 shown, 24 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 687 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8e69410d`
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
- delivery.py
- Series Management
- Cast Engine
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
- Media (ffmpeg) Infra
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
- EpisodeContext
- Ingest & Change Detection
- Character Browser
- read_jsonl
- memory/__init__.py
- Dreaming
- character_updates.py
- Voice Candidates
- New Series Dialog
- Config
- Voice Match
- Bench Run Sandbox
- load_config
- Series-1 Voice Config
- ReviewView
- cast/learning.py
- Series-1 Cast Config
- test_parser_stages.py
- workspace/__init__.py
- Architecture Guard Test
- pytest
- Frame Selector Widget
- Pinned Requirements
- Briefings & Style Rules
- SubagentError
- Top-level Config Keys
- kernel/__init__.py
- Settings Schema Introspection
- ._show_card
- rule_checks
- Memory Banks Writing
- LLM Provider Config
- bench/audit.py
- pinyin_gen.py
- Voice Learning Tests
- Render Config
- test_probation.py
- numpy
- Memory & Translation Prompts
- json
- ._field
- Tag Editor Widget
- EditRecord
- Series-1 Band Config
- test_character_lifecycle.py
- runner.py
- .episode_update
- test_character_updates.py
- Flow Layout
- Prices Editor
- review_counts
- AuditBar
- Settings Form
- Price Table Keys
- Memory Config Keys
- Series-1 series.yaml
- DropTable
- test_partial_review.py
- Device Detection
- Band
- Series-1 OCR Config
- Series-1 Script Review Config
- HistoryMixin
- JobRunner
- test_new_voices.py
- sprite.py
- Translate Config
- measure.py
- voice/__init__.py
- save
- Background Workers
- _no_real_ffmpeg
- Vietnamese UI Fill
- group_map
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
1. `ReviewedLine` - 158 edges
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
- `save()` --indirect_call--> `episode_id()`  [INFERRED]
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

## Communities (137 total, 24 thin omitted)

### Community 0 - "test_app.py"
Cohesion: 0.15
Nodes (22): MainWindow, NewCharacterDialog, validate(), PinyinLine, write_jsonl(), gate(), write_events(), qapp() (+14 more)

### Community 1 - "client.py"
Cohesion: 0.07
Nodes (33): BudgetExceeded, LLMCallError, LLMOutputError, CostRecord, build_messages(), compute_cost(), _daily_quota(), _describe() (+25 more)

### Community 2 - "App Package & Jobs"
Cohesion: 0.06
Nodes (12): choose_platform(), install_fonts(), install_translator(), main(), agent_label(), error_message(), flag_label(), stage_label() (+4 more)

### Community 3 - "test_ocr_preprocess.py"
Cohesion: 0.16
Nodes (14): load_key(), _norm(), _band(), _box(), _event(), _gold(), test_answer_key_corrects_and_excludes_lines(), test_answer_key_moves_to_renumbered_events_by_time() (+6 more)

### Community 4 - "Memory Screen"
Cohesion: 0.06
Nodes (7): EntryTable, _item(), MemoryView, PairDialog, _same(), _update_text(), run_async()

### Community 5 - "Band & Cast Panel Views"
Cohesion: 0.06
Nodes (10): BandView, CastCanvas, CastPanel, ScaledImage, to_pixmap(), done(), failed(), test_cast_panel_shows_boxes_and_records_corrections() (+2 more)

### Community 6 - "partial.py"
Cohesion: 0.11
Nodes (16): ReviewIncompleteError, compute_edits(), draft_path(), finish_review(), flag_group(), load_draft(), needs_attention(), original_draft() (+8 more)

### Community 7 - "Memory Manager Rows"
Cohesion: 0.18
Nodes (20): merge_proposals(), replaced_term(), reviewed_glossary(), CommitInfo, Conflict, describe_update(), dumps_aliases(), held_updates() (+12 more)

### Community 8 - "test_audit.py"
Cohesion: 0.18
Nodes (16): disagreements(), draw_sample(), load_marks(), missing_answers(), save_marks(), AuditMark, _episode(), pathlib_name() (+8 more)

### Community 9 - "test_feedback_loop.py"
Cohesion: 0.15
Nodes (18): user_json(), evaluator(), vi_for(), translator(), test_off_skips_identification_and_learns_no_characters(), evaluator(), translator(), handler() (+10 more)

### Community 10 - "Memory Manager Tests"
Cohesion: 0.16
Nodes (21): MemoryManager, seed_memory(), test_learning_an_episode_again_replaces_what_it_learned(), P(), test_a_new_glossary_term_takes_the_form_the_reviewer_wrote(), test_conflicts_need_more_evidence(), test_deleted_lines_are_not_memory_evidence(), test_episode_update_applies_mines_briefs_and_commits() (+13 more)

### Community 12 - "test_review_state.py"
Cohesion: 0.10
Nodes (18): line_matches(), LineFilter, LineHistory, next_npc_number(), next_pending(), next_unmarked(), row_state(), _Clock (+10 more)

### Community 13 - "models.py"
Cohesion: 0.11
Nodes (18): freeze_finished(), episode_status(), register_episode(), test_pipeline_reports_script_reviewer_spending(), test_turning_it_on_again_runs_the_stages(), calls(), _pipeline(), stubs() (+10 more)

### Community 14 - "Benchmark Suite"
Cohesion: 0.16
Nodes (24): gold_lines(), align(), _approved(), _auto_pattern(), characters_at(), _decisions(), _events(), Gold (+16 more)

### Community 15 - "Config Schema"
Cohesion: 0.13
Nodes (24): AudioConfig, AuditConfig, BaselineConfig, BenchConfig, BudgetConfig, CleanupConfig, EpisodesConfig, EvaluateConfig (+16 more)

### Community 16 - "delivery.py"
Cohesion: 0.20
Nodes (10): OutputExistsError, deliver(), keep_both_path(), output_folder(), output_name(), resolve_conflict(), reveal_in_explorer(), _same_drive() (+2 more)

### Community 17 - "Series Management"
Cohesion: 0.11
Nodes (26): add_series(), cmd_series(), main(), _setup_logging(), load_config(), _load_env(), update_config_values(), add() (+18 more)

### Community 18 - "Cast Engine"
Cohesion: 0.09
Nodes (20): CastEngine, _ffmpeg(), frame_path(), get_engine(), group_unknowns(), keep_boxes(), line_motion(), load_frame() (+12 more)

### Community 19 - "Video Preview (mpv)"
Cohesion: 0.07
Nodes (7): fmt_time(), load_mpv(), PreviewWidget, TimelineSlider, text(), _FakePlayer, test_preview_transport_controls()

### Community 20 - "test_cast.py"
Cohesion: 0.11
Nodes (17): match(), _apply_labels(), _check_talkers(), _name_unknowns(), plan(), _Plan, FakeEngine, _frame() (+9 more)

### Community 21 - "Memory Store"
Cohesion: 0.07
Nodes (20): _pairs_block(), _present_block(), characters_block(), corrections_block(), evaluator_prefix(), glossary_block(), glossary_zh_block(), new_voices_block() (+12 more)

### Community 22 - "test_suite.py"
Cohesion: 0.13
Nodes (17): load_gold(), CastDetection, picture_veto(), test_picture_veto_disputes_the_voice(), line(), _line(), make_baseline(), test_a_stopped_chain_run_resumes_where_it_stopped() (+9 more)

### Community 23 - "card.py"
Cohesion: 0.11
Nodes (21): card_info(), card_media(), CharacterCard, confirmed_box(), _cut_clip(), _cut_picture(), _episode_ids(), _frame() (+13 more)

### Community 24 - "Services"
Cohesion: 0.08
Nodes (3): EpisodeRow, Services, load_sample()

### Community 25 - "OCR Engine & Geometry"
Cohesion: 0.07
Nodes (27): ModelUnavailableError, OcrBox, line_span(), symmetric_span(), center_in_band(), create_engine(), crop_path(), crop_view() (+19 more)

### Community 26 - "Subtitle Style"
Cohesion: 0.12
Nodes (18): calibrate(), grow_line(), labels_near(), load_style(), propose_regions(), _region_features(), save_style(), segment_mask() (+10 more)

### Community 27 - "Pipeline Runner & Locks"
Cohesion: 0.12
Nodes (5): _learn(), job_lock(), StageState, _episode_log, Pipeline

### Community 28 - "conftest.py"
Cohesion: 0.12
Nodes (16): FakeClient, FakeCompletions, make_llm(), project(), _response(), _setup(), test_auto_apply_does_not_count_as_rejection(), test_existing_rules_are_not_reproposed_and_terms_go_to_the_glossary() (+8 more)

### Community 29 - "Episodes Screen"
Cohesion: 0.13
Nodes (5): choose_batch_on_exists(), choose_on_exists(), job_busy(), EpisodesView, confirm()

### Community 30 - "Memory Proposals Apply"
Cohesion: 0.16
Nodes (7): MemoryProposal, atomic_write_text(), now_iso(), ApplyMixin, ApplyResult, test_a_different_suggestion_for_the_same_term_still_comes_through(), gloss()

### Community 31 - "benchmark.py"
Cohesion: 0.13
Nodes (16): auditable_lines(), gold_speakers(), _acc(), benchmark_episodes(), BenchmarkResult, _copy_reviewer_context(), _drop_heavy_files(), EpisodeScore (+8 more)

### Community 32 - "Voice Learning & Evidence"
Cohesion: 0.15
Nodes (17): is_auto_episode(), auto_clips(), auto_gate(), AutoGate, build_centroids(), Clip, embed_clips(), EvalReport (+9 more)

### Community 33 - "Media (ffmpeg) Infra"
Cohesion: 0.17
Nodes (16): available_encoders(), extract_clip(), extract_frame(), git(), has_video_stream(), imread(), iter_gray_frames(), missing_binaries() (+8 more)

### Community 34 - "Audit & Dreaming Screens"
Cohesion: 0.07
Nodes (12): AuditView, done(), character_proposals(), DreamingView, _summary(), done(), done(), save() (+4 more)

### Community 35 - "Settings & Run Panel"
Cohesion: 0.11
Nodes (5): label(), reset_all(), save(), sequence(), SettingsView

### Community 36 - "Script Review & OCR Fix"
Cohesion: 0.09
Nodes (22): ScriptDecision, is_han(), normalize_zh(), LineDecision, apply_script_review(), build_draft(), looks_like_noise(), ScriptReviewConfig (+14 more)

### Community 37 - "Frozen Baseline"
Cohesion: 0.21
Nodes (12): baseline_dir(), complete(), freeze(), freeze_episode(), _git_head(), _manifest(), memory_at_run(), _save_manifest() (+4 more)

### Community 38 - "Bootstrap Seed"
Cohesion: 0.11
Nodes (23): approve_seed(), _episode1_lines(), generate_seed(), load_seed(), name_pinyin(), save_clip(), save_seed(), seed_path() (+15 more)

### Community 39 - "YAML Comment-Preserving Edit"
Cohesion: 0.14
Nodes (17): file_comment(), _block_end(), delete_key(), _dump(), _find(), _get(), _is_child(), _path() (+9 more)

### Community 41 - "render.py"
Cohesion: 0.08
Nodes (29): balanced_wrap(), split_explicit_lines(), wrap_words(), _ass_text(), build_ass(), build_mask_filter(), check_fonts(), choose_encoder() (+21 more)

### Community 42 - "ocr_benchmark.py"
Cohesion: 0.13
Nodes (13): _sandbox_paths(), _covered(), EpisodeOcrScore, _existing_events(), ocr_episodes(), OcrBenchResult, _overlap(), remap_ids() (+5 more)

### Community 43 - "Episode"
Cohesion: 0.09
Nodes (18): add_status(), cmd_status(), SourceMissingError, Episode, AddCandidate, derived_status(), detect_number(), episode_id() (+10 more)

### Community 44 - "EpisodeContext"
Cohesion: 0.18
Nodes (24): atomic_write_json(), _review_run(), build_windows(), run(), EpisodeContext, make_episode(), sample_events(), test_translator_sees_the_cast() (+16 more)

### Community 45 - "Ingest & Change Detection"
Cohesion: 0.18
Nodes (18): binarize(), Change, change_fraction(), detect_changes(), draw_band(), fuse(), has_subtitle(), outlined_ratio() (+10 more)

### Community 46 - "Character Browser"
Cohesion: 0.12
Nodes (6): CharacterBrowser, CharacterStrip, describe(), _pixmap(), ClipPlayer, test_character_browser_lists_cards_and_assigns()

### Community 47 - "read_jsonl"
Cohesion: 0.20
Nodes (14): read_jsonl(), reviewer_corrections(), run(), _reading(), _rubric(), test_a_passing_line_keeps_the_evaluators_suggestion_for_the_reviewer(), test_fragments_merge_by_time_on_screen_and_noise_is_predeleted(), test_predeleted_lines_are_not_reviewer_edits() (+6 more)

### Community 48 - "memory/__init__.py"
Cohesion: 0.10
Nodes (21): Evaluation, LineTranslation, SpeakerCandidates, SubtitleEvent, judge(), llm_rubric(), max_chars_for(), rubric_payload() (+13 more)

### Community 49 - "Dreaming"
Cohesion: 0.10
Nodes (24): read_json(), apply_dream(), approved_lines(), describe(), done_episodes(), dream(), DreamGlossary, DreamItem (+16 more)

### Community 50 - "character_updates.py"
Cohesion: 0.11
Nodes (16): _alias_zh(), CharacterChange, CharacterUpdateResponse, check(), _clip(), _has_word(), _introduces(), _positions() (+8 more)

### Community 51 - "Voice Candidates"
Cohesion: 0.14
Nodes (3): load_line_voices(), CandidatesMixin, _Run

### Community 52 - "New Series Dialog"
Cohesion: 0.11
Nodes (5): NewSeriesDialog, StyleDialog, test_new_series_dialog_asks_for_the_default_pronoun_pair(), test_new_series_dialog_creates_a_translation_style(), test_new_series_work_folder_can_be_chosen()

### Community 53 - "Config"
Cohesion: 0.15
Nodes (7): auditable(), trusted_speakers(), torch_device(), job_lock_path(), trusted_auto_lines(), usable_line(), Config

### Community 54 - "Voice Match"
Cohesion: 0.13
Nodes (17): new_voice_id(), _voices(), VoiceConfig, episode_samples(), classify(), Embedder, find_new_voices(), get_embedder() (+9 more)

### Community 55 - "Bench Run Sandbox"
Cohesion: 0.16
Nodes (13): checkout_memory(), _drop_heavy(), _frozen_inputs(), _install_review(), _null(), _rerun_episode(), run(), _run_info() (+5 more)

### Community 56 - "load_config"
Cohesion: 0.20
Nodes (12): prompt_hash(), check_id(), list_registers(), load_register(), _parse(), Register, register_dir(), save_register() (+4 more)

### Community 57 - "Series-1 Voice Config"
Cohesion: 0.08
Nodes (24): voice, accept_score, confusable_similarity, learn_auto_allowed_flags, learn_auto_max_drop, learn_auto_min_margin, learn_auto_min_score, learn_auto_min_test_lines (+16 more)

### Community 58 - "ReviewView"
Cohesion: 0.08
Nodes (3): ReviewView, loaded(), opened()

### Community 59 - "cast/learning.py"
Cohesion: 0.14
Nodes (11): build_bank(), crop(), frame_time_ms(), apply_review_edits(), frame_embedder(), embed(), learn_sprites(), SpriteLearnResult (+3 more)

### Community 60 - "Series-1 Cast Config"
Cohesion: 0.09
Nodes (23): cast, add_similarity, detector_model, embed_model, enabled, frame_width, learn, match_margin (+15 more)

### Community 61 - "test_parser_stages.py"
Cohesion: 0.07
Nodes (31): AuditSample, CastBoxEdit, ChangeRecord, OcrReading, Window, edit_distance(), keep_cjk(), relatedness() (+23 more)

### Community 62 - "workspace/__init__.py"
Cohesion: 0.19
Nodes (9): EpisodeState, cleanup(), load_state(), save_state(), state_path(), test_auto_mode_learns_only_from_trusted_lines(), test_backfill_runs_cast_where_missing_then_learns(), fake_cast() (+1 more)

### Community 63 - "Architecture Guard Test"
Cohesion: 0.17
Nodes (8): _breaches(), _imports(), _module_of(), _submodules(), test_every_package_is_a_known_module_with_a_public_api(), test_modules_import_each_other_only_through_their_api_and_downwards(), test_the_app_reaches_the_core_only_through_its_services(), test_the_core_never_imports_the_app_or_qt()

### Community 64 - "pytest"
Cohesion: 0.19
Nodes (12): ConfigError, active_series(), find_root(), list_series(), merge_sections(), parse_config(), _read_yaml(), save_config_text() (+4 more)

### Community 66 - "Pinned Requirements"
Cohesion: 0.10
Nodes (20): jieba 0.42.1, numpy 2.5.3, onnxruntime-gpu 1.30.0, openai 3.22.1, opencv-python-headless 5.0.0.93, pillow 12.3.0, pydantic 2.13.5, pypinyin 0.55.0 (+12 more)

### Community 67 - "Briefings & Style Rules"
Cohesion: 0.21
Nodes (12): briefings_dir(), cap_style_rules(), IndexEntry, list_episode_briefings(), _read(), read_index(), read_story(), read_style_rules() (+4 more)

### Community 68 - "SubagentError"
Cohesion: 0.16
Nodes (13): EpisodeLockedError, EpisodeNotFoundError, JobRunningError, MemoryLockedError, OutputFolderError, StageError, SubagentError, mode_prompt() (+5 more)

### Community 69 - "Top-level Config Keys"
Cohesion: 0.10
Nodes (19): budget, max_cost_per_episode, cleanup, auto, device, episodes, number_patterns, video_extensions (+11 more)

### Community 70 - "kernel/__init__.py"
Cohesion: 0.11
Nodes (12): running_jobs(), append_jsonl(), _atomic_write(), FileLock, hash_path(), lock_holder(), pid_alive(), _replace_with_retry() (+4 more)

### Community 71 - "Settings Schema Introspection"
Cohesion: 0.12
Nodes (11): add(), _code_notes(), fields(), walk(), FieldSpec, known_sets(), target(), _unwrap() (+3 more)

### Community 73 - "rule_checks"
Cohesion: 0.13
Nodes (12): check(), rule_checks(), RuleContext, RuleFailure, _word_tokenizer(), _line(), rules(), test_gate_auto_and_human() (+4 more)

### Community 74 - "Memory Banks Writing"
Cohesion: 0.14
Nodes (6): _add_exemplars(), BanksMixin, _drop_exemplar(), _keep_best(), _record_votes(), _undo_episode()

### Community 75 - "LLM Provider Config"
Cohesion: 0.11
Nodes (18): api_key_env, base_url, model, llm, max_retries, max_retry_wait_s, providers, temperature (+10 more)

### Community 76 - "bench/audit.py"
Cohesion: 0.23
Nodes (11): AuditReport, build_report(), EpisodeAudit, is_flagged(), _pct(), Rate, render_report(), _rng() (+3 more)

### Community 77 - "pinyin_gen.py"
Cohesion: 0.15
Nodes (8): contains_term(), found_terms(), nfc(), visible_chars(), heteronyms(), PinyinEngine, run(), Token

### Community 78 - "Voice Learning Tests"
Cohesion: 0.31
Nodes (9): _auto_episode(), _episode(), _fake_embed(), test_auto_lines_pass_only_when_every_signal_agrees(), test_auto_lines_that_hurt_accuracy_are_not_learned(), test_auto_lines_that_keep_accuracy_are_learned(), test_auto_lines_wait_until_there_is_enough_to_measure(), test_learn_writes_bank_and_evaluate_reports_accuracy() (+1 more)

### Community 79 - "Render Config"
Cohesion: 0.12
Nodes (17): render, avg_char_width, blur_radius, encoder, font_dir, font_name, line_spacing, mask (+9 more)

### Community 80 - "test_probation.py"
Cohesion: 0.20
Nodes (17): NewVoice, review_voice_ids(), _approved(), test_a_name_you_give_is_locked(), test_new_voice_becomes_a_character_and_takes_the_first_name_everywhere(), _finish(), _lines(), _talks() (+9 more)

### Community 81 - "numpy"
Cohesion: 0.16
Nodes (7): ReviewedLine, candidate_looks(), candidate_voice(), check_return(), ReturnCheck, speaker_lines(), _unit()

### Community 82 - "Memory & Translation Prompts"
Cohesion: 0.19
Nodes (8): Style rules, Cổ trang / tiên hiệp register (Hán-Việt terms), identify / default_pair template toggle, Memory proposals (glossary / pronoun_pair / character), Pronoun matrix, Retries with earlier_attempts and evaluator_suggestion, Reviewer corrections, Speaker rules per voice status (fixed/confusable/disputed/new_voice/unknown/too_short)

### Community 83 - "json"
Cohesion: 0.12
Nodes (14): chunked(), load_prompt(), BriefingResponse, compress_story(), generate_briefing(), script_text(), StoryResponse, word_count() (+6 more)

### Community 84 - "._field"
Cohesion: 0.25
Nodes (3): _decimals(), Field, set_float()

### Community 86 - "EditRecord"
Cohesion: 0.33
Nodes (7): EditRecord, _clip(), _fake_embed(), test_bootstrap_seed_and_approve(), test_dreaming_proposals_and_apply(), test_mining_an_episode_again_replaces_its_speaker_corrections(), mine()

### Community 87 - "Series-1 Band Config"
Cohesion: 0.13
Nodes (15): bottom, left, right, top, video, band_frames, change_threshold, empty_text_ratio (+7 more)

### Community 88 - "test_character_lifecycle.py"
Cohesion: 0.40
Nodes (11): CharacterFate, _lines(), _setup(), _status(), test_consecutive_episodes_keep_a_character(), test_first_run_counts_earlier_episodes(), test_generic_characters_are_never_matched_or_learned(), test_old_memory_gets_the_new_columns() (+3 more)

### Community 89 - "runner.py"
Cohesion: 0.11
Nodes (12): counts_text(), _pct(), write_report(), BatchItem, Runner, _lazy(), review_outputs(), run_stage() (+4 more)

### Community 91 - "test_character_updates.py"
Cohesion: 0.29
Nodes (10): save_line_voices(), _line(), _llm(), _npc(), test_a_candidate_keeps_its_updates_when_promoted(), finish(), test_auto_mode_holds_updates_from_unchecked_lines(), test_check_keeps_only_what_the_lines_show() (+2 more)

### Community 93 - "Prices Editor"
Cohesion: 0.16
Nodes (3): _num_text(), PricesEditor, ProvidersEditor

### Community 94 - "review_counts"
Cohesion: 0.18
Nodes (5): all_correct_mark(), marked_count(), review_counts(), ReviewCounts, test_audit_marking()

### Community 98 - "Price Table Keys"
Cohesion: 0.15
Nodes (13): input, input_cached, output, input, input_cached, output, input, input_cached (+5 more)

### Community 99 - "Memory Config Keys"
Cohesion: 0.15
Nodes (13): memory, aliases_max, archive_after_absent, character_lifecycle, character_updates, correction_examples, description_max_chars, dream_max_lines (+5 more)

### Community 100 - "Series-1 series.yaml"
Cohesion: 0.15
Nodes (12): baseline, name, bench, baseline, non_dialogue, box_center_tolerance, box_height_tolerance, enabled (+4 more)

### Community 101 - "DropTable"
Cohesion: 0.13
Nodes (3): AddDialog, DropTable, done()

### Community 102 - "test_partial_review.py"
Cohesion: 0.18
Nodes (14): PartialSuggestion, partial_review(), PartialResult, suggest(), _episode(), _line(), _sug_model(), test_a_speaker_set_by_an_earlier_partial_review_may_change_again() (+6 more)

### Community 103 - "Device Detection"
Cohesion: 0.29
Nodes (4): describe(), onnx_cuda_available(), onnx_use_cuda(), torch_cuda_available()

### Community 104 - "Band"
Cohesion: 0.20
Nodes (3): Band, test_band_pixels_are_even_and_inside_frame(), test_band_centres_by_widening_the_short_side()

### Community 105 - "Series-1 OCR Config"
Cohesion: 0.18
Nodes (11): ocr, fragment_max_samples, fragment_merge_similarity, mask_image, mask_scale, merge_max_edit_distance, min_confidence, preprocess (+3 more)

### Community 106 - "Series-1 Script Review Config"
Cohesion: 0.18
Nodes (11): script_review, enabled, example_limit, max_remove_share, memory_auto_remove_min, memory_max_han, remove_confidence, repeat_merge_gap_ms (+3 more)

### Community 108 - "JobRunner"
Cohesion: 0.13
Nodes (3): JobRunner, test_run_panel_has_a_script_review_step(), __init__()

### Community 109 - "test_new_voices.py"
Cohesion: 0.14
Nodes (14): script_note(), draft_voice_ids(), episode_character_ids(), is_auto_id(), is_unnamed(), load_new_voices(), save_new_voices(), _e() (+6 more)

### Community 110 - "sprite.py"
Cohesion: 0.13
Nodes (9): best_match(), candidates_for(), decide(), load_templates(), run(), frame_reader(), save_template(), imwrite_png() (+1 more)

### Community 111 - "Translate Config"
Cohesion: 0.22
Nodes (9): translate, max_cps, max_line_chars, max_lines_per_event, max_retries, picture_evidence, picture_veto, pronoun_terms (+1 more)

### Community 112 - "measure.py"
Cohesion: 0.08
Nodes (33): _ask(), build_pipeline(), _interactive(), _output_exists(), _resolve_on_exists(), add_add(), add_batch(), add_calibrate() (+25 more)

### Community 113 - "voice/__init__.py"
Cohesion: 0.28
Nodes (3): load(), all_similarities(), pair_similarities()

### Community 114 - "save"
Cohesion: 0.36
Nodes (7): headline(), _r(), render(), save(), SuiteResult, add_bench(), cmd_bench()

### Community 119 - "group_map"
Cohesion: 0.50
Nodes (3): group_map(), mapping(), test_group_map_is_one_to_one_by_shared_lines()

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
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1022 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ReviewedLine` connect `numpy` to `test_app.py`, `App Package & Jobs`, `test_ocr_preprocess.py`, `Band & Cast Panel Views`, `partial.py`, `Memory Manager Rows`, `test_audit.py`, `Memory Manager Tests`, `test_review_state.py`, `Benchmark Suite`, `test_cast.py`, `Memory Store`, `test_suite.py`, `card.py`, `Services`, `Pipeline Runner & Locks`, `conftest.py`, `Memory Proposals Apply`, `benchmark.py`, `Voice Learning & Evidence`, `Script Review & OCR Fix`, `._load_editor`, `render.py`, `ocr_benchmark.py`, `EpisodeContext`, `read_jsonl`, `memory/__init__.py`, `Dreaming`, `character_updates.py`, `Voice Candidates`, `Config`, `Voice Match`, `ReviewView`, `cast/learning.py`, `test_parser_stages.py`, `workspace/__init__.py`, `Briefings & Style Rules`, `rule_checks`, `bench/audit.py`, `Voice Learning Tests`, `test_probation.py`, `json`, `EditRecord`, `test_character_lifecycle.py`, `runner.py`, `.episode_update`, `test_character_updates.py`, `review_counts`, `AuditBar`, `test_partial_review.py`, `test_new_voices.py`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ReviewedLine` (e.g. with `_finish()` and `test_pipeline_records_what_the_reviewer_removed_and_kept()`) actually correct?**
  _`ReviewedLine` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `subagent`, `Font draws 了 like digit 7`, `Show wording that looks like stray text (史 for 屎, 鸡道, 姬叔)` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `client.py` be split into smaller, more focused modules?**
  _Cohesion score 0.075 - nodes in this community are weakly interconnected._
- **Why does `ReviewView` connect `ReviewView` to `test_app.py`, `AuditBar`, `App Package & Jobs`, `Audit & Dreaming Screens`, `Memory Screen`, `Band & Cast Panel Views`, `._load_editor`, `._show_card`, `JobRunner`, `test_review_state.py`, `Character Browser`, `Video Preview (mpv)`, `Episodes Screen`, `review_counts`, `AuditBar`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Config` (e.g. with `fields()` and `value_at()`) actually correct?**
  _`Config` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `App Package & Jobs` be split into smaller, more focused modules?**
  _Cohesion score 0.058941058941058944 - nodes in this community are weakly interconnected._