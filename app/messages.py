"""Translated labels for statuses, stages, flags and pipeline error codes (6.10)."""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication


def status_label(status: str) -> str:
    return {
        "new": QCoreApplication.translate("Status", "New"),
        "running": QCoreApplication.translate("Status", "Running"),
        "awaiting_review": QCoreApplication.translate("Status", "Awaiting review"),
        "done": QCoreApplication.translate("Status", "Done"),
        "failed": QCoreApplication.translate("Status", "Failed"),
        "missing": QCoreApplication.translate("Status", "Video missing"),
        "interrupted": QCoreApplication.translate("Status", "Interrupted"),
    }.get(status, status)


def stage_label(stage: str) -> str:
    return {
        "ingest": QCoreApplication.translate("Stage", "Frame sampling"),
        "ocr": QCoreApplication.translate("Stage", "OCR"),
        "events": QCoreApplication.translate("Stage", "Events"),
        "ocr_fix": QCoreApplication.translate("Stage", "OCR correction"),
        "audio": QCoreApplication.translate("Stage", "Audio"),
        "voice": QCoreApplication.translate("Stage", "Voice match"),
        "pinyin": QCoreApplication.translate("Stage", "Pinyin"),
        "windows": QCoreApplication.translate("Stage", "Scenes"),
        "translate": QCoreApplication.translate("Stage", "Translate + evaluate"),
        "sprite": QCoreApplication.translate("Stage", "Sprite check"),
        "script_review": QCoreApplication.translate("Stage", "Script review"),
        "cast": QCoreApplication.translate("Stage", "Characters on screen"),
        "partial_review": QCoreApplication.translate("Stage", "Partial review"),
        "batch": QCoreApplication.translate("Stage", "Batch"),
        "review": QCoreApplication.translate("Stage", "Review gate"),
        "memory": QCoreApplication.translate("Stage", "Memory update"),
        "render": QCoreApplication.translate("Stage", "Render"),
        "cleanup": QCoreApplication.translate("Stage", "Cleanup"),
        "bootstrap": QCoreApplication.translate("Stage", "Bootstrap"),
        "dream": QCoreApplication.translate("Stage", "Dreaming"),
        "pipeline": QCoreApplication.translate("Stage", "Pipeline"),
    }.get(stage, stage)


def flag_label(flag: str) -> str:
    return {
        "retry_cap": QCoreApplication.translate("Flag", "Retry limit reached"),
        "sprite_unresolved": QCoreApplication.translate("Flag", "Speaker unresolved"),
        "low_speaker_conf": QCoreApplication.translate("Flag", "Low speaker confidence"),
        "non_dialogue_suspect": QCoreApplication.translate("Flag", "Possibly on-screen text"),
        "ocr_uncertain": QCoreApplication.translate("Flag", "OCR uncertain"),
        "ocr_fragment": QCoreApplication.translate("Flag", "One-frame OCR fragment"),
        "script_suspect": QCoreApplication.translate("Flag", "Script review: check this line"),
        "script_ocr": QCoreApplication.translate("Flag", "Script review: OCR error in the Chinese (fix suggested)"),
        "script_repeat": QCoreApplication.translate("Flag", "Removed: repeat of another line"),
        "script_noise": QCoreApplication.translate("Flag", "Removed: OCR noise"),
        "script_unrelated": QCoreApplication.translate("Flag", "Removed: not part of the story"),
        "script_other": QCoreApplication.translate("Flag", "Removed by script review"),
        "check_pinyin": QCoreApplication.translate("Flag", "Check pinyin"),
        "missing_translation": QCoreApplication.translate("Flag", "Missing translation"),
        "line_too_long": QCoreApplication.translate("Flag", "Line too long"),
        "cps_exceeded": QCoreApplication.translate("Flag", "Reading speed too high"),
        "glossary_mismatch": QCoreApplication.translate("Flag", "Glossary term not used"),
        "pronoun_mismatch": QCoreApplication.translate("Flag", "Pronoun mismatch"),
        "speaker_invalid": QCoreApplication.translate("Flag", "Invalid speaker"),
        "speaker_override": QCoreApplication.translate("Flag", "Speaker differs from voice"),
        "ocr_low_conf": QCoreApplication.translate("Flag", "Low OCR confidence"),
        "not_evaluated": QCoreApplication.translate("Flag", "Not evaluated"),
        "rule_warnings": QCoreApplication.translate("Flag", "Rule warnings"),
        "partial_suggestion": QCoreApplication.translate("Flag", "Partial review suggests another speaker"),
        "partial_speaker": QCoreApplication.translate("Flag", "Speaker set by partial review"),
        "check_pronouns": QCoreApplication.translate("Flag", "Speaker changed: check the pronouns"),
    }.get(flag, flag)


def agent_label(task: str) -> str:
    return {
        "translate": QCoreApplication.translate("Agent", "Translator"),
        "evaluate": QCoreApplication.translate("Agent", "Evaluator"),
        "script_review": QCoreApplication.translate("Agent", "Script reviewer"),
        "ocr_fix": QCoreApplication.translate("Agent", "OCR correction"),
        "pinyin": QCoreApplication.translate("Agent", "Pinyin (polyphones)"),
        "briefing": QCoreApplication.translate("Agent", "Memory briefing"),
        "bootstrap": QCoreApplication.translate("Agent", "Bootstrap"),
        "dreaming": QCoreApplication.translate("Agent", "Dreaming"),
    }.get(task, task)


def error_message(code: str | None, fallback: str) -> str:
    """Plain-language message with the next action to take; falls back to the English message."""
    messages = {
        "missing_binary": QCoreApplication.translate("Errors", "A required program (ffmpeg, ffprobe or git) is not installed. Install it and restart the app."),
        "source_missing": QCoreApplication.translate("Errors", "The episode's video file was moved or deleted. Use Relink to point to its new location."),
        "budget_exceeded": QCoreApplication.translate("Errors", "The LLM budget for this episode was reached. Raise the budget in Settings, then Resume."),
        "llm_output_invalid": QCoreApplication.translate("Errors", "The AI model returned invalid output twice. Resume to try again."),
        "llm_call_failed": QCoreApplication.translate("Errors", "The AI service could not be reached. Check your internet connection and API keys, then Resume."),
        "api_key_missing": QCoreApplication.translate("Errors", "An API key is missing. Enter it in Settings > API keys."),
        "output_folder_invalid": QCoreApplication.translate("Errors", "The output folder is not set or not writable. Choose one in Settings > Files."),
        "output_exists": QCoreApplication.translate("Errors", "The output video already exists. Choose Overwrite or Keep both."),
        "review_incomplete": QCoreApplication.translate("Errors", "The review is not complete: every line must be approved and have Vietnamese text."),
        "episode_locked": QCoreApplication.translate("Errors", "Another job is already running for this episode."),
        "memory_locked": QCoreApplication.translate("Errors", "Memory is being written by another job. Try again in a moment."),
        "job_running": QCoreApplication.translate("Errors", "Not allowed while a job is running. Wait for it to finish."),
        "config_invalid": QCoreApplication.translate("Errors", "The settings are invalid. Fix them in Settings."),
        "model_unavailable": QCoreApplication.translate("Errors", "A required model package is not installed. See README for the install command."),
        "font_missing": QCoreApplication.translate("Errors", "No subtitle font was found in the fonts folder. Add NotoSans-Regular.ttf there."),
        "render_failed": QCoreApplication.translate("Errors", "Rendering failed. See the log for details, then try Render again."),
        "episode_not_found": QCoreApplication.translate("Errors", "This episode is not registered."),
        "cast_missing": QCoreApplication.translate("Errors", "Write the cast list and synopsis first (Bootstrap step 2)."),
        "seed_missing": QCoreApplication.translate("Errors", "Generate the seed first (Bootstrap step 5)."),
        "cancelled": QCoreApplication.translate("Errors", "The job was cancelled. Resume to continue where it stopped."),
    }
    text = messages.get(code or "")
    if text is None:
        return fallback
    return f"{text}\n\n{fallback}" if fallback and fallback != text else text
