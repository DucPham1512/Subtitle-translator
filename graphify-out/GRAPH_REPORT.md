# Graph Report - Subtitle-translator  (2026-11-03)

## Corpus Check
- 266 files · ~247,698 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 17 file(s) not represented in the graph (top: .drawio 6, .lock 2, (none) 2)

## Summary
- 3667 nodes · 11892 edges · 171 communities (139 shown, 32 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 776 edges (avg confidence: 0.87)
- Token cost: 390,590 input · 0 output

## Community Hubs (Navigation)
- LLM Client & Budget
- Sprite Check & Cast Matching
- Dreaming & Rejections
- Review Gate & Drafts
- Memory Entry Tables UI
- App Shell & Jobs
- Evaluator Rule Checks
- Kernel Errors & Translation
- CLI Series & Prompt Hash
- App Services & Output
- Memory Manager Apply & Banks
- Bootstrap Wizard View
- Memory Store Queries
- Video Preview (mpv)
- Audit Screen
- Benchmark Gold Lines
- OCR Engine & Boxes
- Pipeline Status & Finish
- CLI Common Helpers
- Infra Stdlib Utilities
- Voice Embeddings & Candidates
- Script Review Decisions
- OCR Models & Edit Distance
- Pipeline Tests & Fakes
- Subtitle Events & Windows
- Episodes Screen
- Episode Registry
- Subtitle Style Calibration
- Character Voices Store
- Audit Data Sampling
- ASS Builder & Mask
- Band & Cast Canvas Views
- Review Screen
- Bootstrap Service & ffmpeg
- Voice Learning
- Memory Proposals Apply
- YAML Comment-Preserving Edit
- Character Cards
- Cast Engine Helpers
- Main Window Navigation
- Settings Service & Root
- Config Schema Models
- Shortcuts Settings
- Voice Ids & Config
- Cast Stage Frames
- OCR Benchmark
- Ingest & Change Detection
- App Service Rows
- Character Browser
- Prompts Loading & Story
- New Series Dialog
- Bench Run Sandbox
- Speaker Benchmark Stats
- Series-1 Voice Config
- Episode State & Cast Tests
- Desktop App Spec
- Memory & Dreaming Screens Spec
- Series-1 Cast Config
- Bootstrap Seed
- Frozen Baseline
- Benchmarks & Events Spec
- Frame Selector Widget
- Briefings & Style Rules
- On-Screen Cast Review
- Top-level Config Keys
- OCR Preprocess Crop
- New Voices & Probation
- Memory Banks Writing
- Architecture Spec Stages
- Atomic Writes & Locks
- Settings Schema Introspection
- Character Updates
- Cast Experiments & Skill
- LLM Provider Config
- Pipeline Map Notes
- Cast Box Edits
- Episode Memory Update
- Translation Spec
- Job Lock & Status
- Cast Detection Models
- Review Character Panel
- Architecture Guard Test
- Render Config
- Benchmark Suite Notes
- OCR Spec & Calibration
- Job Runner
- Audit Marks
- Cast Panel UI
- CLAUDE.md Rules
- Pinned Requirements
- Add Episodes Dialog
- Tag Editor Widget
- Series-1 Band Config
- Glossary Learning Fix
- Memory Prompts
- Stage Runner & Hashing
- SQLite Schema Spec
- Render & Registry Spec
- Review Flags & Filters
- Audit Bar
- New Character Dialog
- Flow Layout
- Prices Editor
- Design Rationale & History
- Character Lifecycle Tests
- Voice Learning Tests
- Settings & Config Spec
- Data Models Spec
- Review & Bootstrap Services
- Settings Form
- Sprite Bank Matching
- Price Table Keys
- Memory Config Keys
- Series-1 series.yaml
- Code Refactor Decisions
- Settings Field Controls
- Linux Move & Requirements
- Memory Prompt Prefix
- Video Render & Encoder
- Script Review Spec
- Pipeline CLI Spec
- Glossary & ID-off Changes
- Series-1 OCR Config
- Series-1 Script Review Config
- Multi-Series Decision
- App Entry Point
- Review Editor State
- Example Cast
- Register & Pronoun Mode
- Known Weaknesses
- Cast Engine (OWLv2/DINOv2)
- Memory Service & Voice API
- Async Fetch Helpers
- Translate Config
- LDA Sprite Experiment
- Pipeline Map Stages
- Briefing Generation
- Changelog 2026-10-11
- Suite Result Report
- Memory Git History
- Pinyin Engine
- Voice-Cast Spec
- Series-1 Cast
- Vault Housekeeping
- OCR Map & Prompts
- Module Boundaries Spec
- Vietnamese UI Fill
- Raw YAML Dialog
- Audit Config
- Series Picker
- Sprite Config
- Voice Matching Diagram
- OCR Test Fixtures
- Audio Config
- Output Config
- Review Config
- Windows Config
- Story & Fates Prompts
- Id Group Mapping
- Band Centering
- Memory Migration
- Qt Test Fixture
- Subagent Package

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
- `Command list` --semantically_similar_to--> `Pipeline and CLI commands (pipeline/, __main__.py)`  [INFERRED] [semantically similar]
  README.md → .claude/rules/pipeline-cli.md
- `Auto mode: speaker only when bootstrap seed and voice fixed, default ta/ngươi` --semantically_similar_to--> `Character identification off (show.character_identification)`  [INFERRED] [semantically similar]
  knowledge_vault/decisions/07-10-2026/2026-10-07 chia hai chế độ auto và human.md → .claude/rules/translation.md
- `main()` --calls--> `find_root()`  [INFERRED]
  app/__main__.py → subagent/settings/config.py
- `_same()` --calls--> `parse_aliases()`  [INFERRED]
  app/views/memory.py → subagent/memory/store.py
- `test_advanced_settings_form_edits_in_place_and_keeps_comments()` --uses--> `TagEditor`  [INFERRED]
  tests/test_app.py → app/views/settings_form.py

## Import Cycles
- 2-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/__init__.py`
- 3-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/manager/__init__.py -> subagent/memory/__init__.py`
- 3-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/briefing_gen.py -> subagent/memory/__init__.py`
- 3-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/prefix.py -> subagent/memory/__init__.py`
- 4-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/manager/__init__.py -> subagent/memory/manager/apply.py -> subagent/memory/__init__.py`
- 4-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/manager/__init__.py -> subagent/memory/manager/episode.py -> subagent/memory/__init__.py`
- 4-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/briefing_gen.py -> subagent/memory/prefix.py -> subagent/memory/__init__.py`
- 5-file cycle: `subagent/memory/__init__.py -> subagent/memory/dreaming.py -> subagent/memory/manager/__init__.py -> subagent/memory/manager/updates.py -> subagent/memory/character_updates.py -> subagent/memory/__init__.py`

## Hyperedges (group relationships)
- **Memory learning after finish review** — _claude_rules_memory_memory_manager, _claude_rules_memory_character_updates, _claude_rules_memory_probation, _claude_rules_memory_character_lifecycle, _claude_rules_memory_human_edit_mining [EXTRACTED 1.00]
- **OCR front-end stages 1-4** — _claude_rules_ocr_frame_sampling, _claude_rules_ocr_ocr_stage, _claude_rules_ocr_event_building, _claude_rules_ocr_ocr_correction [EXTRACTED 1.00]
- **Reviewer rejection / hold-for-review stores** — _claude_rules_data_models_conflicts_json, _claude_rules_data_models_dream_rejections_json, _claude_rules_data_models_character_updates_json [INFERRED 0.75]
- **Translate-evaluate-retry flow** — _claude_rules_translation_translator, _claude_rules_translation_evaluator, _claude_rules_translation_rule_checks, _claude_rules_translation_llm_rubric, _claude_rules_translation_retry_loop, _claude_rules_translation_retry_input [EXTRACTED 1.00]
- **Speaker attribution evidence signals** — _claude_rules_voice_cast_voice_match, _claude_rules_voice_cast_voice_statuses, _claude_rules_voice_cast_talking_sprite, _claude_rules_translation_picture_veto, _claude_rules_translation_picture_evidence, _claude_rules_voice_cast_sprite_check [INFERRED 0.85]
- **Accuracy experiment methodology** — _claude_skills_pipeline_improvement_experiments_skill_locate_failing_stage, _claude_skills_pipeline_improvement_experiments_skill_free_ceiling_check, _claude_skills_pipeline_improvement_experiments_skill_fair_run_comparison, _claude_skills_pipeline_improvement_experiments_skill_decide_and_record [EXTRACTED 1.00]
- **Glossary learning and matching fixes (2026-10-10)** — knowledge_vault_decisions_10_10_2026_2026_10_10_sửa_lỗi_glossary_học_từ_bản_dịch_máy_reviewed_glossary, knowledge_vault_decisions_10_10_2026_2026_10_10_sửa_lỗi_glossary_học_từ_bản_dịch_máy_replaced_term, knowledge_vault_decisions_10_10_2026_2026_10_10_vòng_phản_hồi_translator___evaluator_glossary_word_match, knowledge_vault_decisions_10_10_2026_2026_10_10_vòng_phản_hồi_translator___evaluator_jieba_hmm [INFERRED 0.85]
- **Multi-series configuration (series folder, overrides, registers, identification switch)** — knowledge_vault_decisions_11_10_2026_2026_10_11_nhiều_bộ_phim_trong_một_dự_án_series_folder, knowledge_vault_decisions_11_10_2026_2026_10_11_nhiều_bộ_phim_trong_một_dự_án_series_yaml_override, knowledge_vault_decisions_11_10_2026_2026_10_11_tạo_văn_phong_dịch_mới_register_files, knowledge_vault_decisions_12_10_2026_2026_10_12_chế_độ_nhận_diện_nhân_vật_character_identification, knowledge_vault_decisions_11_10_2026_2026_10_11_thiết_lập_nâng_cao_dạng_biểu_mẫu_advanced_settings_form [INFERRED 0.85]
- **Module boundary enforcement (public API, app/services, architecture test)** — knowledge_vault_decisions_21_10_2026_2026_10_21_tách_code_thành_module_feature_modules, knowledge_vault_decisions_21_10_2026_2026_10_21_tách_code_thành_module_package_public_api, knowledge_vault_decisions_21_10_2026_2026_10_21_tách_code_thành_module_app_services, knowledge_vault_decisions_21_10_2026_2026_10_21_tách_code_thành_module_test_architecture [EXTRACTED 1.00]
- **LLM prompts that feed the Memory Manager** — prompts_briefing_system, prompts_character_update_system, prompts_dreaming_system, prompts_bootstrap_system, prompts_story_compress_system [INFERRED 0.85]
- **Translate / evaluate / retry loop** — prompts_translator_system, prompts_evaluator_system, prompts_translator_system_retries_earlier_attempts, knowledge_vault_map_tổng_quan_pipeline_translate_evaluate_loop, prompts_registers_co_trang_tien_hiep [INFERRED 0.85]
- **Benchmark tooling against frozen gold** — knowledge_vault_decisions_đo_lường___benchmark_suite_audit, knowledge_vault_decisions_đo_lường___benchmark_suite_speaker_benchmark, knowledge_vault_decisions_đo_lường___benchmark_suite_baseline_replay_2026_10, knowledge_vault_decisions_đo_lường___benchmark_suite_benchmark_suite, knowledge_vault_decisions_đo_lường___benchmark_suite_reference_snapshot, knowledge_vault_decisions_đo_lường___benchmark_suite_reference_chain [EXTRACTED 1.00]

## Communities (171 total, 32 thin omitted)

### Community 0 - "LLM Client & Budget"
Cohesion: 0.06
Nodes (36): BudgetExceeded, LLMCallError, LLMOutputError, CostRecord, build_messages(), compute_cost(), _daily_quota(), _describe() (+28 more)

### Community 1 - "Sprite Check & Cast Matching"
Cohesion: 0.07
Nodes (50): run(), best_match(), candidates_for(), decide(), load_templates(), run(), frame_reader(), save_template() (+42 more)

### Community 2 - "Dreaming & Rejections"
Cohesion: 0.07
Nodes (46): present_ids(), apply_dream(), forget_rejections(), load_rejections(), MemoryManager, FakeClient, FakeCompletions, make_llm() (+38 more)

### Community 3 - "Review Gate & Drafts"
Cohesion: 0.07
Nodes (42): script_note(), EditRecord, PartialSuggestion, ReviewedLine, write_jsonl(), partial_review(), suggest(), apply_script_review() (+34 more)

### Community 4 - "Memory Entry Tables UI"
Cohesion: 0.06
Nodes (8): EntryTable, _item(), MemoryView, done(), PairDialog, text(), _same(), _update_text()

### Community 5 - "App Shell & Jobs"
Cohesion: 0.07
Nodes (9): agent_label(), error_message(), stage_label(), status_label(), ReviewData, choose_on_exists(), RunPanel, confirm() (+1 more)

### Community 6 - "Evaluator Rule Checks"
Cohesion: 0.07
Nodes (35): check(), _kept_evaluation(), Evaluation, LineTranslation, SpeakerCandidates, llm_rubric(), rubric_payload(), rule_checks() (+27 more)

### Community 7 - "Kernel Errors & Translation"
Cohesion: 0.06
Nodes (28): EpisodeLockedError, EpisodeNotFoundError, JobRunningError, MemoryLockedError, OutputFolderError, ReviewIncompleteError, SourceMissingError, StageError (+20 more)

### Community 8 - "CLI Series & Prompt Hash"
Cohesion: 0.08
Nodes (36): cmd_series(), ConfigError, main(), prompt_hash(), active_series(), list_series(), load_config(), _load_env() (+28 more)

### Community 9 - "App Services & Output"
Cohesion: 0.07
Nodes (17): OutputExistsError, cleanup(), deliver(), keep_both_path(), output_folder(), output_name(), resolve_conflict(), reveal_in_explorer() (+9 more)

### Community 10 - "Memory Manager Apply & Banks"
Cohesion: 0.18
Nodes (22): merge_proposals(), replaced_term(), reviewed_glossary(), CommitInfo, Conflict, describe_update(), dumps_aliases(), held_updates() (+14 more)

### Community 12 - "Memory Store Queries"
Cohesion: 0.08
Nodes (12): glossary_zh_block(), ocr_fix_prefix(), LogEntry, MemoryStore, PronounPair, SpriteExemplar, VoiceEntry, _voices() (+4 more)

### Community 13 - "Video Preview (mpv)"
Cohesion: 0.07
Nodes (6): fmt_time(), load_mpv(), PreviewWidget, TimelineSlider, _FakePlayer, test_preview_transport_controls()

### Community 14 - "Audit Screen"
Cohesion: 0.07
Nodes (8): AuditView, done(), DreamingView, _summary(), show_error(), run_async(), _Signals, _Task

### Community 15 - "Benchmark Gold Lines"
Cohesion: 0.12
Nodes (32): gold_lines(), _norm(), _overlap(), score_episode(), align(), _approved(), _auto_pattern(), characters_at() (+24 more)

### Community 16 - "OCR Engine & Boxes"
Cohesion: 0.08
Nodes (18): OcrBox, keep_cjk(), line_span(), symmetric_span(), create_engine(), _engine_key(), filter_boxes(), get_engine() (+10 more)

### Community 17 - "Pipeline Status & Finish"
Cohesion: 0.12
Nodes (6): _learn(), job_lock(), StageState, counts_text(), _episode_log, Pipeline

### Community 18 - "CLI Common Helpers"
Cohesion: 0.09
Nodes (32): _ask(), build_pipeline(), _interactive(), _output_exists(), _resolve_on_exists(), add_add(), add_batch(), add_calibrate() (+24 more)

### Community 19 - "Infra Stdlib Utilities"
Cohesion: 0.07
Nodes (14): describe(), onnx_cuda_available(), onnx_use_cuda(), torch_cuda_available(), torch_device(), ModelUnavailableError, Progress, build_parser() (+6 more)

### Community 20 - "Voice Embeddings & Candidates"
Cohesion: 0.08
Nodes (10): load_line_voices(), CandidatesMixin, _Run, candidate_looks(), candidate_voice(), check_return(), ReturnCheck, speaker_lines() (+2 more)

### Community 21 - "Script Review Decisions"
Cohesion: 0.10
Nodes (25): ScriptDecision, normalize_zh(), LineDecision, ScriptReviewConfig, examples_block(), find_repeats(), han_count(), memory_removals() (+17 more)

### Community 22 - "OCR Models & Edit Distance"
Cohesion: 0.10
Nodes (22): OcrReading, edit_distance(), relatedness(), absorb_fragments(), build_events(), flag_non_dialogue(), frames_on_screen(), _Group (+14 more)

### Community 23 - "Pipeline Tests & Fakes"
Cohesion: 0.09
Nodes (30): freeze_finished(), user_json(), evaluator(), test_off_skips_identification_and_learns_no_characters(), evaluator(), translator(), handler(), handler() (+22 more)

### Community 24 - "Subtitle Events & Windows"
Cohesion: 0.09
Nodes (22): SubtitleEvent, Window, chunked(), Character, GlossaryEntry, crop_path(), apply_fixes(), batch_payload() (+14 more)

### Community 25 - "Episodes Screen"
Cohesion: 0.12
Nodes (4): choose_batch_on_exists(), job_busy(), EpisodesView, done()

### Community 26 - "Episode Registry"
Cohesion: 0.12
Nodes (14): cmd_add(), Episode, AddCandidate, derived_status(), fingerprint(), Registry, add(), scan_paths() (+6 more)

### Community 27 - "Subtitle Style Calibration"
Cohesion: 0.13
Nodes (17): calibrate(), grow_line(), labels_near(), load_style(), propose_regions(), _region_features(), save_style(), segment_mask() (+9 more)

### Community 28 - "Character Voices Store"
Cohesion: 0.10
Nodes (13): atomic_write_json(), read_json(), draft_voice_ids(), episode_character_ids(), is_auto_id(), is_unnamed(), load_new_voices(), review_voice_ids() (+5 more)

### Community 29 - "Audit Data Sampling"
Cohesion: 0.12
Nodes (18): auditable(), auditable_lines(), AuditReport, build_report(), disagreements(), draw_sample(), EpisodeAudit, is_flagged() (+10 more)

### Community 30 - "ASS Builder & Mask"
Cohesion: 0.10
Nodes (18): _ass_text(), build_ass(), build_mask_filter(), _color(), Layout, _style(), Band, test_band_pixels_are_even_and_inside_frame() (+10 more)

### Community 31 - "Band & Cast Canvas Views"
Cohesion: 0.11
Nodes (5): BandView, CastCanvas, ScaledImage, to_pixmap(), test_greyscale_images_can_be_shown()

### Community 32 - "Review Screen"
Cohesion: 0.10
Nodes (3): ReviewView, loaded(), opened()

### Community 33 - "Bootstrap Service & ffmpeg"
Cohesion: 0.15
Nodes (17): available_encoders(), extract_clip(), extract_frame(), git(), has_video_stream(), imread(), iter_gray_frames(), missing_binaries() (+9 more)

### Community 34 - "Voice Learning"
Cohesion: 0.13
Nodes (20): cmd_voices(), is_auto_episode(), usable_line(), auto_clips(), auto_gate(), AutoGate, build_centroids(), Clip (+12 more)

### Community 35 - "Memory Proposals Apply"
Cohesion: 0.19
Nodes (6): MemoryProposal, atomic_write_text(), ApplyMixin, ApplyResult, test_a_different_suggestion_for_the_same_term_still_comes_through(), gloss()

### Community 36 - "YAML Comment-Preserving Edit"
Cohesion: 0.14
Nodes (17): file_comment(), _block_end(), delete_key(), _dump(), _find(), _get(), _is_child(), _path() (+9 more)

### Community 37 - "Character Cards"
Cohesion: 0.14
Nodes (13): card_info(), card_media(), CharacterCard, confirmed_box(), _cut_clip(), _cut_picture(), _episode_ids(), _frame() (+5 more)

### Community 38 - "Cast Engine Helpers"
Cohesion: 0.12
Nodes (14): crop(), frame_time_ms(), get_engine(), _apply_labels(), apply_review_edits(), _check_talkers(), frame_embedder(), embed() (+6 more)

### Community 39 - "Main Window Navigation"
Cohesion: 0.22
Nodes (17): MainWindow, PinyinLine, gate(), register_episode(), settle(), test_audit_screen_and_audit_mode(), test_bootstrap_learns_the_subtitle_style_as_a_job(), test_character_cards_and_browser_in_review() (+9 more)

### Community 40 - "Settings Service & Root"
Cohesion: 0.14
Nodes (14): find_root(), check_id(), list_registers(), load_register(), _parse(), Register, register_dir(), save_register() (+6 more)

### Community 41 - "Config Schema Models"
Cohesion: 0.12
Nodes (25): AudioConfig, AuditConfig, BaselineConfig, BenchConfig, BudgetConfig, CleanupConfig, EpisodesConfig, EvaluateConfig (+17 more)

### Community 42 - "Shortcuts Settings"
Cohesion: 0.11
Nodes (5): label(), reset_all(), save(), sequence(), SettingsView

### Community 43 - "Voice Ids & Config"
Cohesion: 0.14
Nodes (15): new_voice_id(), VoiceConfig, classify(), compute_centroids(), Embedder, find_new_voices(), get_embedder(), group_voices() (+7 more)

### Community 44 - "Cast Stage Frames"
Cohesion: 0.12
Nodes (15): _ffmpeg(), frame_path(), group_unknowns(), keep_boxes(), line_motion(), load_frame(), _mark_talking(), middle_frames() (+7 more)

### Community 45 - "OCR Benchmark"
Cohesion: 0.12
Nodes (16): _sandbox_paths(), _covered(), EpisodeOcrScore, _existing_events(), load_key(), ocr_episodes(), OcrBenchResult, remap_ids() (+8 more)

### Community 46 - "Ingest & Change Detection"
Cohesion: 0.16
Nodes (19): binarize(), Change, change_fraction(), detect_changes(), draw_band(), fuse(), has_subtitle(), outlined_ratio() (+11 more)

### Community 48 - "Character Browser"
Cohesion: 0.12
Nodes (6): CharacterBrowser, CharacterStrip, describe(), _pixmap(), ClipPlayer, test_character_browser_lists_cards_and_assigns()

### Community 49 - "Prompts Loading & Story"
Cohesion: 0.15
Nodes (19): load_prompt(), compress_story(), approved_lines(), describe(), done_episodes(), dream(), DreamGlossary, DreamItem (+11 more)

### Community 50 - "New Series Dialog"
Cohesion: 0.13
Nodes (5): NewSeriesDialog, StyleDialog, test_new_series_dialog_asks_for_the_default_pronoun_pair(), test_new_series_dialog_creates_a_translation_style(), test_new_series_work_folder_can_be_chosen()

### Community 51 - "Bench Run Sandbox"
Cohesion: 0.16
Nodes (13): checkout_memory(), _drop_heavy(), _frozen_inputs(), _install_review(), _null(), _rerun_episode(), run(), _run_info() (+5 more)

### Community 52 - "Speaker Benchmark Stats"
Cohesion: 0.14
Nodes (12): gold_speakers(), stratified(), wilson(), _acc(), benchmark_episodes(), BenchmarkResult, _copy_reviewer_context(), _drop_heavy_files() (+4 more)

### Community 53 - "Series-1 Voice Config"
Cohesion: 0.08
Nodes (24): voice, accept_score, confusable_similarity, learn_auto_allowed_flags, learn_auto_max_drop, learn_auto_min_margin, learn_auto_min_score, learn_auto_min_test_lines (+16 more)

### Community 54 - "Episode State & Cast Tests"
Cohesion: 0.18
Nodes (16): EpisodeState, save_state(), FakeEngine, _frame(), _lines(), test_auto_mode_learns_only_from_trusted_lines(), test_backfill_runs_cast_where_missing_then_learns(), fake_cast() (+8 more)

### Community 55 - "Desktop App Spec"
Cohesion: 0.15
Nodes (22): Batch run (batch --rerun), Character card (Who is this character?), Desktop app spec (6), Review draft autosave (review_draft.jsonl), Episodes and run screens (6.3), Interface language i18n (6.10), Live preview (6.5, mpv), Navigation sidebar (6.2) (+14 more)

### Community 56 - "Memory & Dreaming Screens Spec"
Cohesion: 0.16
Nodes (21): Dreaming screen (6.8), Memory screen (6.7), character_updates.json, conflicts.json, dream_rejections.json, speaker_corrections.jsonl, candidate_sprites table, candidates table (+13 more)

### Community 57 - "Series-1 Cast Config"
Cohesion: 0.09
Nodes (23): cast, add_similarity, detector_model, embed_model, enabled, frame_width, learn, match_margin (+15 more)

### Community 58 - "Bootstrap Seed"
Cohesion: 0.18
Nodes (18): approve_seed(), _episode1_lines(), generate_seed(), load_seed(), save_seed(), seed_path(), seed_proposals(), SeedCharacter (+10 more)

### Community 60 - "Frozen Baseline"
Cohesion: 0.19
Nodes (12): baseline_dir(), complete(), freeze(), freeze_episode(), _git_head(), _manifest(), memory_at_run(), _save_manifest() (+4 more)

### Community 61 - "Benchmarks & Events Spec"
Cohesion: 0.17
Nodes (21): Stage 3: event building (ocr/events.py), OCR answer key (answer_key.json), Audit (6.11, bench/audit.py), Audit marks (audit_marks.jsonl), Audit sample (stratified, seeded by episode id), Frozen baseline (6.11d), Baseline aliases.json (NPC ids naming one character), Benchmark suite (6.11e, bench score|run) (+13 more)

### Community 63 - "Briefings & Style Rules"
Cohesion: 0.21
Nodes (13): briefings_dir(), cap_style_rules(), IndexEntry, list_episode_briefings(), _read(), read_episode_briefing(), read_index(), read_story() (+5 more)

### Community 65 - "Top-level Config Keys"
Cohesion: 0.10
Nodes (19): budget, max_cost_per_episode, cleanup, auto, device, episodes, number_patterns, video_extensions (+11 more)

### Community 66 - "OCR Preprocess Crop"
Cohesion: 0.16
Nodes (13): crop_view(), to_band_coords(), _band(), _box(), _event(), _gold(), test_benchmark_scores_by_time_overlap(), test_box_filter_drops_short_and_distant_boxes() (+5 more)

### Community 67 - "New Voices & Probation"
Cohesion: 0.23
Nodes (14): NewVoice, Candidate, save_line_voices(), _finish(), _lines(), _talks(), test_a_candidate_not_back_in_time_is_dropped(), test_a_new_voice_waits_on_probation_and_is_promoted_when_it_comes_back() (+6 more)

### Community 68 - "Memory Banks Writing"
Cohesion: 0.14
Nodes (7): now_iso(), _add_exemplars(), BanksMixin, _drop_exemplar(), _keep_best(), _record_votes(), _undo_episode()

### Community 69 - "Architecture Spec Stages"
Cohesion: 0.11
Nodes (19): QFileSystemWatcher on state.json, Pipeline and modules spec (3.2-3.4), Repository layout (3.3), Stage 5: audio extraction, Stage 6b: cast, Stage 18: cleanup, Stage 15: voice + sprite learning, Stage 14: memory update (+11 more)

### Community 70 - "Atomic Writes & Locks"
Cohesion: 0.18
Nodes (7): _atomic_write(), atomic_write_bytes(), FileLock, hash_path(), _replace_with_retry(), sha256_bytes(), sha256_json()

### Community 71 - "Settings Schema Introspection"
Cohesion: 0.15
Nodes (9): _code_notes(), fields(), walk(), known_sets(), target(), _unwrap(), value_at(), with_known_sets() (+1 more)

### Community 72 - "Character Updates"
Cohesion: 0.18
Nodes (13): _alias_zh(), CharacterChange, CharacterUpdateResponse, check(), _clip(), _has_word(), _introduces(), _pairs_block() (+5 more)

### Community 73 - "Cast Experiments & Skill"
Cohesion: 0.13
Nodes (14): Cast recognition OWLv2 + DINOv2 (cast/cast.py), Sprite learning (cast/learning.py, write_sprites), Talking sprite detection via head motion, Pipeline improvement experiments skill, Changelog 2026-10-08, Changelog 2026-10-09, Changelog 2026-10-10, Sprite DINOv2 LDA projection experiment (removed) (+6 more)

### Community 74 - "LLM Provider Config"
Cohesion: 0.11
Nodes (18): api_key_env, base_url, model, llm, max_retries, max_retry_wait_s, providers, temperature (+10 more)

### Community 75 - "Pipeline Map Notes"
Cohesion: 0.16
Nodes (16): pipeline.drawio diagram, Cleanup, Human review + finish, Memory bootstrap, Memory update, Render + deliver, Report, Review gate (+8 more)

### Community 76 - "Cast Box Edits"
Cohesion: 0.20
Nodes (11): CastBoxEdit, VideoInfo, _cast(), _line(), _no_real_ffmpeg(), _setup(), test_bootstrap_material_and_a_pinned_sample_come_first(), clip() (+3 more)

### Community 78 - "Translation Spec"
Cohesion: 0.15
Nodes (15): translation rules (5.9-5.14), Evaluator (translation/evaluate.py), LLM rubric (meaning, pronouns, register, naturalness, speaker), Memory prefix (memory_prefix.md), Picture veto / disputed status (translate.picture_veto), Pinyin generation (translation/pinyin_gen.py), Polyphone fallback utility call, Translator prompt layout (static + memory prefix + variable) (+7 more)

### Community 79 - "Job Lock & Status"
Cohesion: 0.16
Nodes (5): job_lock_path(), running_jobs(), lock_holder(), pid_alive(), write_silence()

### Community 80 - "Cast Detection Models"
Cohesion: 0.19
Nodes (9): gold_boxes(), CastDetection, CastLine, picture_veto(), test_cast_panel_shows_boxes_and_records_corrections(), test_on_screen_checked_mark(), test_picture_veto_disputes_the_voice(), line() (+1 more)

### Community 81 - "Review Character Panel"
Cohesion: 0.13
Nodes (6): character_proposals(), save(), load(), done(), done(), episode_id()

### Community 82 - "Architecture Guard Test"
Cohesion: 0.21
Nodes (8): _breaches(), _imports(), _module_of(), _submodules(), test_every_package_is_a_known_module_with_a_public_api(), test_modules_import_each_other_only_through_their_api_and_downwards(), test_the_app_reaches_the_core_only_through_its_services(), test_the_core_never_imports_the_app_or_qt()

### Community 83 - "Render Config"
Cohesion: 0.12
Nodes (17): render, avg_char_width, blur_radius, encoder, font_dir, font_name, line_spacing, mask (+9 more)

### Community 84 - "Benchmark Suite Notes"
Cohesion: 0.18
Nodes (14): Audit (6.11), Baseline replay-2026-10 (6.11d), Benchmark suite (6.11e), Probation fix (5.15b), reference-chain run, reference-snapshot run, Speaker benchmark (6.11b), Cast recognition (5.8b) (+6 more)

### Community 85 - "OCR Spec & Calibration"
Cohesion: 0.23
Nodes (13): Bootstrap wizard (6.6), Stage 1: ingest (ocr/ingest.py), Stage 2: OCR (ocr/ocr.py), Subtitle band calibration (calibrate), Box filter (detect mode), Frame sampling + change detection (5.3), Generic subtitle segmentation (5.4a, preprocess: segment), Line recognition (recognize: line) (+5 more)

### Community 86 - "Job Runner"
Cohesion: 0.20
Nodes (3): JobRunner, test_run_panel_has_a_script_review_step(), __init__()

### Community 87 - "Audit Marks"
Cohesion: 0.25
Nodes (11): save_marks(), AuditMark, _episode(), pathlib_name(), test_gold_answers_and_benchmark(), fake_stage(), test_marks_keep_not_applicable_apart_from_unmarked(), test_new_character_without_id_means_blank_is_right() (+3 more)

### Community 89 - "CLAUDE.md Rules"
Cohesion: 0.15
Nodes (14): Knowledge vault rules (section 12), Human mode and auto mode, Subtitle Agent project overview, Rules for Claude Code (section 9), Tech stack (Python, Pydantic, openai SDK, RapidOCR, ECAPA, PySide6), Changelog 2026-10-21, Dated decision folders decisions/dd-mm-yyyy/, Migration to Linux (video_data, work/series-1) (+6 more)

### Community 90 - "Pinned Requirements"
Cohesion: 0.12
Nodes (15): jieba 0.42.1, numpy 2.5.3, onnxruntime-gpu 1.30.0, openai 3.22.1, opencv-python-headless 5.0.0.93, pillow 12.3.0, pydantic 2.13.5, PySide6 6.11.2 (+7 more)

### Community 93 - "Series-1 Band Config"
Cohesion: 0.13
Nodes (15): bottom, left, right, top, video, band_frames, change_threshold, empty_text_ratio (+7 more)

### Community 94 - "Glossary Learning Fix"
Cohesion: 0.21
Nodes (9): 2026-10-10 sửa lỗi glossary học từ bản dịch máy, Human-edit mining (5.16), Memory Manager (memory/manager.py), Reviewer edit breakdown (87 lines over 16 episodes: 22 speaker, 12 OCR, 53 translation), 5 wrong glossary entries (降鱼十八钓, 姬佬, 竿门开, 龙抬头, 趴地虎), 2026-10-10 vòng phản hồi translator - evaluator, evaluate.min_score config key, judge() evaluator verdict function (+1 more)

### Community 95 - "Memory Prompts"
Cohesion: 0.22
Nodes (9): Dreaming (offline), Translate + evaluate loop, Style rules, Cổ trang / tiên hiệp register (Hán-Việt terms), identify / default_pair template toggle, Memory proposals (glossary / pronoun_pair / character), Pronoun matrix, Retries with earlier_attempts and evaluator_suggestion (+1 more)

### Community 96 - "Stage Runner & Hashing"
Cohesion: 0.35
Nodes (3): Runner, StageDef, ocr_hash()

### Community 97 - "SQLite Schema Spec"
Cohesion: 0.19
Nodes (14): Stage 4: OCR correction (ocr/ocr_fix.py), SQLite memory schema (4.1), appearances table, characters table, confusable_pairs table, glossary table, line_decision_episodes table, line_decisions table (+6 more)

### Community 98 - "Render & Registry Spec"
Cohesion: 0.18
Nodes (13): pipeline-cli rules (5.19-5.23), Cleanup of temporary files, NVENC encoder with libx264 fallback, Episode number detection (episodes.number_patterns), Episode registry (workspace/episodes.py), on_exists name-conflict policy (overwrite|keep-both|fail), Output delivery (output/delivery.py), Output renderer (output/render.py) (+5 more)

### Community 99 - "Review Flags & Filters"
Cohesion: 0.15
Nodes (4): flag_label(), show(), flag_group(), needs_attention()

### Community 101 - "New Character Dialog"
Cohesion: 0.20
Nodes (3): NewCharacterDialog, validate(), is_han()

### Community 103 - "Prices Editor"
Cohesion: 0.16
Nodes (3): _num_text(), PricesEditor, ProvidersEditor

### Community 104 - "Design Rationale & History"
Cohesion: 0.14
Nodes (4): Lịch sử - thứ tự triển khai và dữ kiện dự án, Implementation order (18 steps), Confirmed project facts table, Thiết kế - lý do các lựa chọn

### Community 105 - "Character Lifecycle Tests"
Cohesion: 0.35
Nodes (11): new_voices_block(), _lines(), _setup(), _status(), test_consecutive_episodes_keep_a_character(), test_first_run_counts_earlier_episodes(), test_generic_characters_are_never_matched_or_learned(), test_old_memory_gets_the_new_columns() (+3 more)

### Community 106 - "Voice Learning Tests"
Cohesion: 0.30
Nodes (9): _auto_episode(), _episode(), _fake_embed(), test_auto_lines_pass_only_when_every_signal_agrees(), test_auto_lines_that_hurt_accuracy_are_not_learned(), test_auto_lines_that_keep_accuracy_are_learned(), test_auto_lines_wait_until_there_is_enough_to_measure(), test_learn_writes_bank_and_evaluate_reports_accuracy() (+1 more)

### Community 107 - "Settings & Config Spec"
Cohesion: 0.29
Nodes (12): Advanced settings form (settings_form.py), Settings screen (6.9), budget.max_cost_per_episode, Config and series spec (5.2, 5.2a), config.yaml (Pydantic-validated config), llm.providers (translator, utility, evaluator), Series (5.2a), series list/add/default/rename/migrate commands (+4 more)

### Community 108 - "Data Models Spec"
Cohesion: 0.18
Nodes (13): CastDetection, CastLine, CostRecord, Data models spec (4), EditRecord, Episode, Evaluation, LineTranslation (+5 more)

### Community 109 - "Review & Bootstrap Services"
Cohesion: 0.18
Nodes (3): name_pinyin(), save_clip(), slugify()

### Community 111 - "Sprite Bank Matching"
Cohesion: 0.22
Nodes (5): build_bank(), match(), PartialResult, _session_bank(), _sprites()

### Community 112 - "Price Table Keys"
Cohesion: 0.15
Nodes (13): input, input_cached, output, input, input_cached, output, input, input_cached (+5 more)

### Community 113 - "Memory Config Keys"
Cohesion: 0.15
Nodes (13): memory, aliases_max, archive_after_absent, character_lifecycle, character_updates, correction_examples, description_max_chars, dream_max_lines (+5 more)

### Community 114 - "Series-1 series.yaml"
Cohesion: 0.15
Nodes (12): baseline, name, bench, baseline, non_dialogue, box_center_tolerance, box_height_tolerance, enabled (+4 more)

### Community 115 - "Code Refactor Decisions"
Cohesion: 0.27
Nodes (10): 2026-10-11 tái cấu trúc code, subagent/cli/ command groups (episodes, memory, measure, series), probation function split into four steps, _transaction() helper, 2026-10-21 tách code thành module, Pipeline after_finish hook (baseline copy attached by CLI), app/services/ layer, diagrams/modules.drawio (+2 more)

### Community 116 - "Settings Field Controls"
Cohesion: 0.18
Nodes (5): _decimals(), Field, set_float(), add(), FieldSpec

### Community 117 - "Linux Move & Requirements"
Cohesion: 0.21
Nodes (8): Baseline replay-2026-10, 2026-10-12 requirements.txt và hướng dẫn cài đặt, README Install / Run sections, 2026-10-21 chuyển sang Linux, TMPDIR workaround for /tmp RAM disk during pip install, video_data/input and video_data/output in project, 2026-10-21 xem trước video trên Linux, libmpv / python-mpv

### Community 118 - "Memory Prompt Prefix"
Cohesion: 0.35
Nodes (8): characters_block(), corrections_block(), evaluator_prefix(), glossary_block(), pronoun_block(), story_block(), style_block(), translator_prefix()

### Community 119 - "Video Render & Encoder"
Cohesion: 0.29
Nodes (8): check_fonts(), choose_encoder(), encoder_args(), ffmpeg_args(), font_files(), preview_ass(), sync_fonts(), write_ass()

### Community 120 - "Script Review Spec"
Cohesion: 0.20
Nodes (11): build_ass / build_mask_filter shared builders, finish_review(episode_id), line_decisions memory (record_line_decisions), Review gate and review draft (review/review.py), Script review (translation/script_review.py), Script review OCR fixes never applied (script_ocr flag), series-1 script review prompt notes, Font draws 了 like digit 7 (+3 more)

### Community 121 - "Pipeline CLI Spec"
Cohesion: 0.18
Nodes (11): work/<episode>/.lock, Pipeline and CLI commands (pipeline/, __main__.py), --progress json protocol, report.md per-episode report, Pipeline.run_batch / batch command, run --rerun (RERUN_FROM ocr_fix), BudgetExceeded (budget.max_cost_per_episode), CostRecord in cost.jsonl and llm.prices (+3 more)

### Community 122 - "Glossary & ID-off Changes"
Cohesion: 0.18
Nodes (11): Character identification off (show.character_identification), Glossary whole-word match via jieba with HMM, Evaluator rule checks (length, cps, glossary whole-word, pronouns, speaker ids), Glossary rule jieba HMM fix (鱼 false hits 16→1), Changelog 2026-10-12, Per-series character identification switch, requirements.txt and README install rewrite, Decision: split auto and human modes (+3 more)

### Community 123 - "Series-1 OCR Config"
Cohesion: 0.18
Nodes (11): ocr, fragment_max_samples, fragment_merge_similarity, mask_image, mask_scale, merge_max_edit_distance, min_confidence, preprocess (+3 more)

### Community 124 - "Series-1 Script Review Config"
Cohesion: 0.18
Nodes (11): script_review, enabled, example_limit, max_remove_share, memory_auto_remove_min, memory_max_han, remove_confidence, repeat_merge_gap_ms (+3 more)

### Community 125 - "Multi-Series Decision"
Cohesion: 0.25
Nodes (7): 2026-10-11 nhiều bộ phim trong một dự án, Paths object, series-1 (current series), series list|add|default|rename|migrate CLI, 2026-10-11 thiết lập nâng cao dạng biểu mẫu, subagent/yaml_edit.py comment-preserving in-place YAML edit, Prop text leaking into subtitles (姬, 楚, 史, 表)

### Community 126 - "App Entry Point"
Cohesion: 0.27
Nodes (4): choose_platform(), install_fonts(), install_translator(), main()

### Community 128 - "Example Cast"
Cohesion: 0.24
Nodes (8): 白小雪 (bai_xiaoxue), 林渊 (lin_yuan), 青云门 Thanh Vân Môn, 苏清寒 (su_qinghan), CPU-only setup, Desktop app (python -m app), First episode of a series workflow, Implementation notes (pronoun_pairs.context, evidence_count, conflicts.json)

### Community 129 - "Register & Pronoun Mode"
Cohesion: 0.36
Nodes (5): 2026-10-11 tạo văn phong dịch mới, co_trang_tien_hiep register (31 pronoun terms), translate.pronoun_terms, 2026-10-12 chế độ nhận diện nhân vật, Default pronoun pair show.self_term / show.address_term

### Community 130 - "Known Weaknesses"
Cohesion: 0.27
Nodes (8): Điểm yếu đã biết, Gemini free tier daily quota exhausted, 了 read as 7 (OCR weakness), Low sprite naming rate (LDA tried, failed), Short line between two near-identical lines swallowed in event merge, Đo lường - OCR, OCR benchmark (6.11c), seg_outline_share 0.4 / outline level 72

### Community 132 - "Memory Service & Voice API"
Cohesion: 0.31
Nodes (3): load(), all_similarities(), voice_clips()

### Community 133 - "Async Fetch Helpers"
Cohesion: 0.31
Nodes (4): done(), failed(), done(), failed()

### Community 134 - "Translate Config"
Cohesion: 0.22
Nodes (9): translate, max_cps, max_line_chars, max_lines_per_event, max_retries, picture_evidence, picture_veto, pronoun_terms (+1 more)

### Community 135 - "LDA Sprite Experiment"
Cohesion: 0.39
Nodes (7): 2026-10-10 chiếu đặc trưng sprite theo nhãn reviewer, Cast recognition (5.8b), DINOv2 raw feature vectors (768-d), Hybrid raw-reject + projected-identify matching (future idea), Liu & Keller AAAI 2023 'Detecting and Grounding Important Characters in Visual Stories' (arXiv 2303.17647), sprite_bank.source exemplar provenance column (removed), sprites evaluate command (removed)

### Community 136 - "Pipeline Map Stages"
Cohesion: 0.22
Nodes (8): Audio extraction, Cast stage, Pinyin stage, Scene windowing, Voice match, pypinyin 0.55.0, speechbrain 1.1.1, transformers 5.18.0

### Community 137 - "Briefing Generation"
Cohesion: 0.33
Nodes (6): BriefingResponse, CharacterFate, generate_briefing(), script_text(), StoryResponse, word_count()

### Community 138 - "Changelog 2026-10-11"
Cohesion: 0.29
Nodes (8): Cổ trang / tiên hiệp register (Hán-Việt, classical pronouns), Translation styles / registers (prompts/registers/<id>.md), Changelog 2026-10-11, Advanced settings as forms preserving YAML comments, Multiple series in one project (data/series/<slug>/), Refactor: memory/manager package, subagent/cli, Translation styles as shared prompts/registers files, Series folders data/series/<slug>/ and series.yaml

### Community 139 - "Suite Result Report"
Cohesion: 0.36
Nodes (7): headline(), _r(), render(), save(), SuiteResult, add_bench(), cmd_bench()

### Community 142 - "Voice-Cast Spec"
Cohesion: 0.38
Nodes (7): voice-cast rules (5.1, 5.7-5.8b, 5.13), Audio extraction (voice/audio.py), New voices npc_<ep>_<n> (group_voices), Returning probation candidates, Voice learning (voice/learning.py), Voice match (voice/voice.py) ECAPA statuses, Voice statuses fixed / confusable / unknown / too_short / new_voice

### Community 144 - "Series-1 Cast"
Cohesion: 0.52
Nodes (7): series-1 cast.md, Bắc Tỵ, Cơ Bá Thường, Cơ Tử, Sở Lưu Cần, Sử Thượng Phi, Tiểu Lượng

### Community 145 - "Vault Housekeeping"
Cohesion: 0.38
Nodes (4): 2026-10-21 rút gọn skill refactor, 2026-10-21 thư mục quyết định theo ngày, 2026-10-21 trang chủ vault, Home.md vault start page

### Community 146 - "OCR Map & Prompts"
Cohesion: 0.29
Nodes (5): Event building, Frame sampling + change detection, OCR stage, OCR correction, rapidocr 3.9.2

### Community 147 - "Module Boundaries Spec"
Cohesion: 0.40
Nodes (4): app/services/ (the app's only door into the core), Module layer table (kernel..cli), Module boundaries (3.4), tests/test_architecture.py boundary guard

### Community 150 - "Audit Config"
Cohesion: 0.33
Nodes (6): audit, ignore_flags, include_human, max_disagreements, min_per_stratum, sample_size

### Community 152 - "Sprite Config"
Cohesion: 0.40
Nodes (5): sprite, enabled, match_threshold, scales, trigger_conf_below

### Community 153 - "Voice Matching Diagram"
Cohesion: 0.70
Nodes (5): 2026-10-21 sơ đồ khớp giọng, Automatic npc_<ep>_<n> voice ids, Voice learning with auto-mode filter and gate, diagrams/voice matching.drawio, Voice match statuses fixed / confusable / unknown / too_short

### Community 155 - "Audio Config"
Cohesion: 0.50
Nodes (4): audio, min_event_ms, pad_ms, sample_rate

### Community 156 - "Output Config"
Cohesion: 0.50
Nodes (4): output, folder, name_suffix, on_exists

### Community 157 - "Review Config"
Cohesion: 0.50
Nodes (4): review, mode, noise_max_han, predelete_fragments

### Community 158 - "Windows Config"
Cohesion: 0.50
Nodes (4): windows, context_overlap, gap_ms, max_lines

### Community 160 - "Id Group Mapping"
Cohesion: 0.50
Nodes (3): group_map(), mapping(), test_group_map_is_one_to_one_by_shared_lines()

## Ambiguous Edges - Review These
- `Translator and evaluator from different model families` → `Gemini free tier daily quota exhausted`  [AMBIGUOUS]
  knowledge_vault/decisions/điểm yếu đã biết.md · relation: conceptually_related_to

## Knowledge Gaps
- **88 isolated node(s):** `subagent`, `Interface language i18n (6.10)`, `Stage 5: audio extraction`, `Stage 6: voice match`, `Stage 6b: cast` (+83 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1078 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ReviewedLine` connect `Review Gate & Drafts` to `LLM Client & Budget`, `Sprite Check & Cast Matching`, `Dreaming & Rejections`, `App Shell & Jobs`, `Evaluator Rule Checks`, `Kernel Errors & Translation`, `Briefing Generation`, `App Services & Output`, `Memory Manager Apply & Banks`, `Memory Store Queries`, `Benchmark Gold Lines`, `Voice Embeddings & Candidates`, `Script Review Decisions`, `OCR Models & Edit Distance`, `Character Voices Store`, `Audit Data Sampling`, `ASS Builder & Mask`, `Review Screen`, `Voice Learning`, `Character Cards`, `Cast Engine Helpers`, `Main Window Navigation`, `OCR Benchmark`, `App Service Rows`, `Prompts Loading & Story`, `Episode State & Cast Tests`, `Briefings & Style Rules`, `On-Screen Cast Review`, `OCR Preprocess Crop`, `New Voices & Probation`, `Character Updates`, `Cast Box Edits`, `Episode Memory Update`, `Cast Detection Models`, `Audit Marks`, `Review Flags & Filters`, `Audit Bar`, `Character Lifecycle Tests`, `Voice Learning Tests`, `Sprite Bank Matching`, `Memory Prompt Prefix`, `Video Render & Encoder`, `Review Editor State`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ReviewedLine` (e.g. with `_finish()` and `test_pipeline_records_what_the_reviewer_removed_and_kept()`) actually correct?**
  _`ReviewedLine` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `subagent`, `Interface language i18n (6.10)`, `Stage 5: audio extraction` to the rest of the system?**
  _88 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `LLM Client & Budget` be split into smaller, more focused modules?**
  _Cohesion score 0.062317429406037 - nodes in this community are weakly interconnected._
- **Why does `Config` connect `Infra Stdlib Utilities` to `LLM Client & Budget`, `Dreaming & Rejections`, `Review Gate & Drafts`, `Kernel Errors & Translation`, `CLI Series & Prompt Hash`, `Briefing Generation`, `App Services & Output`, `Memory Manager Apply & Banks`, `Memory Store Queries`, `Benchmark Gold Lines`, `OCR Engine & Boxes`, `Pipeline Status & Finish`, `CLI Common Helpers`, `OCR Models & Edit Distance`, `Subtitle Events & Windows`, `Episode Registry`, `Character Voices Store`, `Audit Data Sampling`, `ASS Builder & Mask`, `Voice Learning`, `Character Cards`, `Cast Engine Helpers`, `Settings Service & Root`, `Config Schema Models`, `Voice Ids & Config`, `Cast Stage Frames`, `OCR Benchmark`, `Prompts Loading & Story`, `Bench Run Sandbox`, `Speaker Benchmark Stats`, `Bootstrap Seed`, `Frozen Baseline`, `Atomic Writes & Locks`, `Settings Schema Introspection`, `Character Updates`, `Review & Bootstrap Services`, `Sprite Bank Matching`, `Video Render & Encoder`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Config` (e.g. with `fields()` and `value_at()`) actually correct?**
  _`Config` has 5 INFERRED edges - model-reasoned connections that need verification._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `Translator and evaluator from different model families` and `Gemini free tier daily quota exhausted`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._