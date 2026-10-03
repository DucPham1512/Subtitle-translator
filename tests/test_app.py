"""Smoke test of the desktop app, offscreen: every screen builds and the review workflow edits the draft."""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QSettings, QThreadPool  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from subagent.episodes import Registry  # noqa: E402
from subagent.models import LineTranslation, PinyinLine  # noqa: E402
from subagent.stages.review import gate, load_draft  # noqa: E402
from subagent.util import write_jsonl  # noqa: E402
from tests.conftest import register_episode, sample_events, seed_memory, write_events  # noqa: E402


@pytest.fixture(scope="module")
def qapp(tmp_path_factory):
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                      str(tmp_path_factory.mktemp("qsettings")))
    QCoreApplication.setOrganizationName("SubtitleAgentTest")
    app = QApplication.instance() or QApplication([])
    yield app


def settle(app) -> None:
    for _ in range(20):
        QThreadPool.globalInstance().waitForDone(5000)
        app.processEvents()


def test_every_screen_builds_and_review_edits_draft(qapp, project):
    from app.main_window import MainWindow
    from app.services import Services

    config, paths = project
    seed_memory(config, paths)
    ep = register_episode(paths, 1)
    work = paths.episode_dir(ep.id)
    events = sample_events()
    write_events(work, events)
    write_jsonl(work / "pinyin.jsonl", [PinyinLine(event_id=e.id, pinyin="pīnyīn") for e in events])
    write_jsonl(work / "translations.jsonl", [
        LineTranslation(event_id=e.id, speaker="lin_yuan", listener="shi_zun", speaker_conf=0.9,
                        vi="Sư phụ, đồ nhi đã Trúc Cơ rồi.", attempts=1, flags=["retry_cap"] if i == 2 else [])
        for i, e in enumerate(events)])
    gate(work, "human")
    Registry(paths).set_status(ep.id, "awaiting_review")

    window = MainWindow(Services(paths.root))
    settle(qapp)
    for key in ("episodes", "memory", "bootstrap", "dreaming", "settings", "review"):
        window.go(key)
        settle(qapp)

    episodes = window.views["episodes"]
    assert episodes.table.rowCount() == 1

    memory = window.views["memory"]
    window.go("memory")
    settle(qapp)
    assert memory.characters.grid.rowCount() == 2

    review = window.views["review"]
    window.show_review(ep.id)
    settle(qapp)
    assert review.table.rowCount() == 4
    assert review.visible == ["ep001:0000", "ep001:0001", "ep001:0002", "ep001:0003"]   # chronological
    first = review.current
    review.vi.setPlainText("Sư phụ, con đã Trúc Cơ.")
    review.approve_and_next()
    review._save()
    settle(qapp)
    saved = {x.event_id: x for x in load_draft(work)}
    assert saved[first].approved and saved[first].vi == "Sư phụ, con đã Trúc Cơ."
    assert saved[first].edited
    assert review.current == "ep001:0001"

    review._undo()                                     # undo the approval on the new current line is a no-op
    window.close()
    settle(qapp)


def test_vietnamese_catalogue_loads(qapp):
    from pathlib import Path

    from PySide6.QtCore import QTranslator

    qm = Path(__file__).resolve().parent.parent / "app" / "i18n" / "app_vi.qm"
    translator = QTranslator()
    assert translator.load(str(qm))
    qapp.installTranslator(translator)
    try:
        assert QCoreApplication.translate("MainWindow", "Episodes") == "Các tập"
        assert QCoreApplication.translate("Errors", "This episode is not registered.") == "Tập này chưa được đăng ký."
    finally:
        qapp.removeTranslator(translator)


def test_new_character_from_review(qapp, project):
    from app.main_window import MainWindow
    from app.services import Services
    from app.views.character_dialog import NewCharacterDialog, validate
    from subagent.memory.store import MemoryStore

    config, paths = project
    seed_memory(config, paths)
    ep = register_episode(paths, 1)
    work = paths.episode_dir(ep.id)
    events = sample_events()
    write_events(work, events)
    write_jsonl(work / "pinyin.jsonl", [PinyinLine(event_id=e.id, pinyin="x") for e in events])
    write_jsonl(work / "translations.jsonl", [
        LineTranslation(event_id=e.id, speaker=None, listener=None, speaker_conf=0.2, vi="Câu thoại.", attempts=1)
        for e in events])
    gate(work, "human")
    Registry(paths).set_status(ep.id, "awaiting_review")

    # suggestions and validation
    dialog = NewCharacterDialog(None, {"lin_yuan", "bai_xiaoxue"}, "白小雪")
    assert dialog.pinyin.text() == "Bái Xiǎo Xuě"
    assert dialog.char_id.text() == "bai_xiao_xue"
    assert validate({"id": "Bad Id", "name_zh": "abc", "name_vi": ""}, set()) == ["chinese", "vietnamese", "id_format"]
    assert validate({"id": "lin_yuan", "name_zh": "林渊", "name_vi": "Lâm Uyên"}, {"lin_yuan"}) == ["id_taken"]

    window = MainWindow(Services(paths.root))
    window.show_review(ep.id)
    settle(qapp)
    review = window.views["review"]
    current = review.current
    review.create_character({"id": "bai_xiaoxue", "name_zh": "白小雪", "name_vi": "Bạch Tiểu Tuyết",
                             "pinyin": "Bái Xiǎoxuě", "description": "sư muội", "glossary": True, "role": "speaker"})
    settle(qapp)
    store = MemoryStore(paths.memory_db)
    char = next(c for c in store.characters() if c.id == "bai_xiaoxue")
    assert char.locked and char.name_vi == "Bạch Tiểu Tuyết"
    assert store.get_row("glossary", "白小雪")["vi"] == "Bạch Tiểu Tuyết"
    assert review.lines[current].speaker == "bai_xiaoxue"
    assert review.speaker.findData("bai_xiaoxue") >= 0 and review.speaker_filter.findData("bai_xiaoxue") >= 0
    review._save()
    settle(qapp)
    assert {x.event_id: x for x in load_draft(work)}[current].speaker == "bai_xiaoxue"
    window.close()
    settle(qapp)


def test_review_delete_reset_and_discard(qapp, project):
    from app.main_window import MainWindow
    from app.services import Services

    config, paths = project
    seed_memory(config, paths)
    ep = register_episode(paths, 1)
    work = paths.episode_dir(ep.id)
    events = sample_events()
    write_events(work, events)
    write_jsonl(work / "pinyin.jsonl", [PinyinLine(event_id=e.id, pinyin="x") for e in events])
    write_jsonl(work / "translations.jsonl", [
        LineTranslation(event_id=e.id, speaker=None, listener=None, speaker_conf=0.9, vi=f"Dòng {i}.", attempts=1)
        for i, e in enumerate(events)])
    gate(work, "human")
    Registry(paths).set_status(ep.id, "awaiting_review")

    window = MainWindow(Services(paths.root))
    window.show_review(ep.id)
    settle(qapp)
    rv = window.views["review"]
    first = rv.current
    original_vi = rv.originals[first].vi               # the line it opens on depends on saved settings

    rv._toggle_delete()                                   # delete: struck out, excluded from totals, moves on
    assert rv.lines[first].deleted and rv.current != first
    assert "Deleted: 1" in rv.counter.text() and "/ 3" in rv.counter.text()
    rv._select(first)
    assert not rv.vi.isEnabled() and rv.delete_btn.text() == "Restore line"
    rv._toggle_delete()                                   # restore
    assert not rv.lines[first].deleted and rv.vi.isEnabled()

    rv.vi.setPlainText("Sửa tay.")
    assert rv.reset_btn.isEnabled()
    rv._reset_line()
    assert rv.lines[first].vi == original_vi
    rv._undo()                                            # reset can be undone
    assert rv.lines[first].vi == "Sửa tay."

    for eid in list(rv.lines):                            # approve everything but one deleted line: finish allowed
        rv.lines[eid] = rv.lines[eid].model_copy(update={"approved": True})
    rv._select(first)
    rv._toggle_delete()
    rv._update_counter()
    assert rv.finish_btn.isEnabled()

    rv.discard_review()                                   # back to the pipeline's output, saved immediately
    draft = load_draft(work)
    assert not any(x.deleted or x.approved or x.edited for x in draft)
    assert {x.event_id: x.vi for x in draft}[first] == original_vi
    window.close()
    settle(qapp)


class _FakePlayer:
    def __init__(self):
        self.seeks: list[tuple[float, str, str]] = []
        self.commands: list[str] = []
        self.pause = True
        self.props: dict = {}

    def seek(self, t, reference="relative", precision="default"):
        self.seeks.append((round(t, 3), reference, precision))

    def command(self, name, *args):
        self.commands.append(name)

    def __setitem__(self, key, value):
        self.props[key] = value


def test_preview_transport_controls(qapp):
    from app.preview import PreviewWidget

    bootstrap_preview = PreviewWidget(line_controls=False)
    assert bootstrap_preview.replay_btn.isHidden() and bootstrap_preview.loop_btn.isHidden()
    assert not bootstrap_preview.slider.isHidden() and not bootstrap_preview.back_btn.isHidden()

    w = PreviewWidget()
    w.player = _FakePlayer()
    w._on_duration(120.0)
    assert w.slider.maximum() == 120000
    w._on_pos(10.0)
    assert w.slider.value() == 10000 and w.time_label.text() == "0:10.0 / 2:00.0"

    w.seek_relative(5000)
    w._on_pos(2.0)
    w.seek_relative(-5000)                     # clamped at the start
    w._on_pos(118.0)
    w.seek_relative(5000)                      # clamped at the end
    assert [s[0] for s in w.player.seeks] == [15.0, 0.0, 120.0]
    assert all(ref == "absolute" and prec == "exact" for _, ref, prec in w.player.seeks)

    w.play_line(30000, 32000)                  # automatic stop at the end of the line...
    assert w._end_ms == 32000
    w.frame_step(1)                            # ...is cancelled by manual control
    w.frame_step(-1)
    assert w._end_ms is None and w.player.commands == ["frame-step", "frame-back-step"]

    w.slider.setValue(60000)                   # a click on the timeline moves the handle, then jumps
    w.slider.jumped.emit(60000)
    assert w.player.seeks[-1] == (60.0, "absolute", "exact")
    w.slider.setSliderDown(True)               # while dragging, playback updates don't move the handle
    w._on_pos(61.0)
    assert w.slider.value() == 60000
    w.player = None


def test_run_panel_has_a_script_review_step(qapp, project):
    from app.views.run import RunPanel

    class _Main:
        def __init__(self):
            from app.jobs import JobRunner
            from app.services import Services

            self.services = Services(project[1].root)
            self.jobs = JobRunner(project[1].root)

    panel = RunPanel(_Main())
    stages = list(panel.bars)
    assert stages.index("sprite") < stages.index("script_review") < stages.index("review")


def test_cast_panel_shows_boxes_and_records_corrections(qapp):
    import numpy as np
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    from app.views.cast_panel import BandView, CastPanel
    from subagent.models import CastDetection, CastLine

    frame = np.zeros((540, 960, 3), np.uint8)
    frame[480:520, 300:700] = 255                                   # "subtitle" pixels
    line = CastLine(event_id="ep001:0000", talking=1, detections=[
        CastDetection(index=0, box=[100, 50, 300, 400], score=0.5, label="c", character="lin_yuan", similarity=0.81),
        CastDetection(index=1, box=[500, 60, 700, 420], score=0.6, label="c", unknown="u002", similarity=0.4)])
    panel = CastPanel()
    panel.resize(960, 900)
    panel.split.setSizes([540, 360])
    panel.show()
    got = []
    panel.review_changed.connect(got.append)
    panel.show_line(frame, line, {"cast_labels": {"1": "shi_zun"}}, {"lin_yuan": "Lâm Uyên", "shi_zun": "Sư tôn"},
                    960, True, rgb=True)
    qapp.processEvents()
    assert panel.table.rowCount() == 2
    assert panel.table.cellWidget(1, 3).currentData() == "shi_zun"   # the saved correction is shown
    assert panel.table.cellWidget(1, 2).isChecked()                  # detected talker
    panel.table.cellWidget(0, 3).setCurrentIndex(panel.table.cellWidget(0, 3).count() - 1)
    assert got[-1]["cast_labels"] == {"1": "shi_zun", "0": "_none"}

    canvas = panel.image
    r = canvas.image_rect()
    k = r.width() / 960

    def at(x, y):
        return QPoint(int(r.x() + x * k), int(r.y() + y * k))

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, at(780, 100))
    QTest.mouseMove(canvas, at(900, 450))
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, at(900, 450))
    added = got[-1]["cast_added"]
    assert len(added) == 1 and added[0]["character"] is None and abs(added[0]["box"][0] - 780) < 3
    assert panel.table.rowCount() == 3 and panel.table.item(2, 0).text() == "A1"
    panel.table.cellWidget(2, 3).setCurrentIndex(panel.table.cellWidget(2, 3).findData("lin_yuan"))
    panel.table.cellWidget(2, 2).setChecked(True)                    # the reviewer saw the drawn one talk
    assert got[-1]["cast_added"][0]["character"] == "lin_yuan" and got[-1]["cast_talking"] == "a0"

    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, at(200, 200))   # move box 1
    QTest.mouseMove(canvas, at(230, 210))
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, at(230, 210))
    moved = got[-1]["cast_boxes"]["0"]
    assert abs(moved[0] - 130) < 3 and abs(moved[1] - 60) < 3

    panel.table.cellWidget(2, 2).setChecked(False)                   # nobody on screen talks
    assert got[-1]["cast_talking"] == "none"
    panel.table.cellWidget(2, 3).setCurrentIndex(panel.table.cellWidget(2, 3).count() - 1)   # remove the drawn box
    assert got[-1]["cast_added"] == [] and panel.table.rowCount() == 2

    band = BandView()
    band.resize(600, 50)
    band.show_band(frame, (300, 470, 600, 70))
    assert band.has_image() and band.height() == 70
    band.show_band(None, None, "missing video")
    assert band.text() == "missing video"


def test_partial_review_suggestions_in_review(qapp, project, monkeypatch):
    from app.main_window import MainWindow
    from app.services import Services
    from subagent.models import PartialSuggestion
    from subagent.partial_review import OUTPUT

    config, paths = project
    seed_memory(config, paths)
    ep = register_episode(paths, 1)
    work = paths.episode_dir(ep.id)
    events = sample_events()
    write_events(work, events)
    write_jsonl(work / "pinyin.jsonl", [PinyinLine(event_id=e.id, pinyin="x") for e in events])
    write_jsonl(work / "translations.jsonl", [
        LineTranslation(event_id=e.id, speaker="lin_yuan", listener=None, speaker_conf=0.5, vi="Câu.", attempts=1)
        for e in events])
    gate(work, "human")
    Registry(paths).set_status(ep.id, "awaiting_review")
    monkeypatch.setattr("app.views.review.QMessageBox.information", lambda *a, **k: None)

    window = MainWindow(Services(paths.root))
    window.show_review(ep.id)
    settle(qapp)
    review = window.views["review"]
    target = events[2].id
    write_jsonl(work / OUTPUT, [PartialSuggestion(event_id=target, talking="shi_zun", suggested_speaker="shi_zun",
                                                  reason="talking on screen")])
    review._partial_job = "partial_review"
    review._job_finished("partial_review", 0, {})
    settle(qapp)
    line = review.lines[target]                      # the suggestion is set on the remaining line
    assert line.speaker == "shi_zun" and {"partial_speaker", "check_pronouns"} <= set(line.flags)
    assert review.lines[events[1].id].speaker == "lin_yuan"     # no suggestion: untouched
    review._select(target)
    settle(qapp)
    assert not review.suggest_btn.isVisibleTo(review)          # nothing left to apply by hand
    review._undo()                                             # one undo step per line restores it
    line = review.lines[target]
    assert line.speaker == "lin_yuan" and "partial_speaker" not in line.flags
    window.close()
    settle(qapp)


def test_audit_screen_and_audit_mode(qapp, project):
    from app.main_window import MainWindow
    from app.services import Services
    from subagent import audit
    from subagent.models import EpisodeState
    from subagent.state import save_state

    config, paths = project
    seed_memory(config, paths)
    ep = register_episode(paths, 1)
    work = paths.episode_dir(ep.id)
    events = sample_events()
    write_events(work, events)
    write_jsonl(work / "pinyin.jsonl", [PinyinLine(event_id=e.id, pinyin="x") for e in events])
    write_jsonl(work / "translations.jsonl", [
        LineTranslation(event_id=e.id, speaker="lin_yuan", listener=None, speaker_conf=0.9, vi="Câu.", attempts=1,
                        flags=["cps_exceeded"] if i == 0 else []) for i, e in enumerate(events)])
    gate(work, "auto")
    save_state(work, EpisodeState(episode_id=ep.id, mode="auto"))
    Registry(paths).set_status(ep.id, "done")
    config.audit.sample_size = 3

    window = MainWindow(Services(paths.root))
    window.services.config.audit.sample_size = 3
    window.services.config.audit.min_per_stratum = 1
    view = window.go("audit")
    settle(qapp)
    assert view.table.rowCount() == 1 and view.table.item(0, 3).text() == "–"      # not sampled yet
    view._sample()
    settle(qapp)
    assert view.table.item(0, 3).text() == "3"
    view.table.selectRow(0)
    view._open()
    settle(qapp)
    review = window.views["review"]
    assert review.audit_mode and review.audit_bar.isVisibleTo(review) and review.data.read_only
    sampled = set(review.audit_sample)
    assert len(review.visible) == 3 and set(review.visible) == sampled             # only the sampled lines
    first = review.current
    review.approve_and_next()                                                      # Ctrl+Enter: all correct, next
    assert review.audit_marks[first].speaker is True and review.current != first
    second = review.current
    review.audit_bar.buttons[("speaker", "wrong")].click()
    review.audit_bar.buttons[("pronouns", "na")].click()
    mark = review.audit_marks[second]
    assert mark.speaker is False and mark.na == ["pronouns"] and mark.any_wrong()
    assert review.audit_bar.correct.isVisibleTo(review.audit_bar)           # "who really speaks" appears on ✗
    assert mark.speaker_value == review.lines[second].speaker
    review.audit_bar.correct.setCurrentIndex(review.audit_bar.correct.findData("shi_zun"))
    assert review.audit_marks[second].correct_speaker == "shi_zun"
    review.flush()
    saved = audit.load_marks(work)
    assert saved[first].translation is True and saved[second].speaker is False
    text, path = window.services.audit_report()
    assert "Speaker:" in text and path.is_file()
    window.go("audit")
    settle(qapp)
    assert view.table.item(0, 4).text() == "2 / 3"
    window.close()
    settle(qapp)


def test_episodes_batch_from_selection(qapp, project, monkeypatch):
    from PySide6.QtCore import QItemSelectionModel

    from app.main_window import MainWindow
    from app.services import Services

    config, paths = project
    for n in (1, 2, 3):
        register_episode(paths, n)
    Registry(paths).set_status("ep001", "done")
    window = MainWindow(Services(paths.root))
    view = window.go("episodes")
    view.refresh()
    settle(qapp)
    started = []
    monkeypatch.setattr("app.views.episodes.confirm", lambda *a, **k: True)
    monkeypatch.setattr(window.jobs, "start", lambda name, args: started.append(args) or True)
    sel = view.table.selectionModel()
    for row in range(view.table.rowCount()):
        sel.select(view.table.model().index(row, 0),
                   QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
    assert view.selected_ids() == ["ep001", "ep002", "ep003"]
    view._run("auto")
    # Run always runs again, the done episode too (after the confirmation)
    assert started == [["batch", "ep001", "ep002", "ep003", "--mode", "auto", "--rerun", "--on-exists", "fail"]]
    started.clear()
    sel.clearSelection()
    view.table.selectRow(0)
    settle(qapp)
    view._run("human")
    assert started == [["run", "ep001", "--mode", "human", "--rerun"]]
    started.clear()
    view._resume()                                     # Resume does only what is missing
    assert started and "--rerun" not in started[0]
    window.close()
    settle(qapp)


def test_new_npc_in_review_is_an_episode_id_without_memory(qapp, project):
    from app.main_window import MainWindow
    from app.services import Services

    config, paths = project
    seed_memory(config, paths)
    ep = register_episode(paths, 1)
    work = paths.episode_dir(ep.id)
    events = sample_events()
    write_events(work, events)
    write_jsonl(work / "pinyin.jsonl", [PinyinLine(event_id=e.id, pinyin="x") for e in events])
    write_jsonl(work / "translations.jsonl", [
        LineTranslation(event_id=e.id, speaker="lin_yuan", listener=None, speaker_conf=0.5, vi="Câu.", attempts=1)
        for e in events])
    gate(work, "human")
    Registry(paths).set_status(ep.id, "awaiting_review")
    window = MainWindow(Services(paths.root))
    window.show_review(ep.id)
    settle(qapp)
    review = window.views["review"]
    review._select(events[1].id)
    settle(qapp)
    review.new_npc_btn.click()
    settle(qapp)
    assert review.lines[events[1].id].speaker == "npc_001_01"
    review._select(events[2].id)
    settle(qapp)
    review.new_npc_btn.click()                       # the next one gets the next number
    settle(qapp)
    assert review.lines[events[2].id].speaker == "npc_001_02"
    assert "npc_001_01" not in review.services.store.character_ids()      # nothing written to memory
    review._save_timer.stop()
    review.services.save_draft(ep.id, list(review.lines.values()))
    assert {"npc_001_01", "npc_001_02"} <= set(Services(paths.root).new_voice_ids(ep.id))   # valid at finish
    window.close()
    settle(qapp)


def test_greyscale_images_can_be_shown(qapp):
    import numpy as np

    from app.views.cast_panel import BandView, to_pixmap

    grey = np.full((48, 300), 128, np.uint8)
    assert to_pixmap(grey).width() == 300
    view = BandView()
    view.show_band(grey, (0, 0, 300, 48))                 # what the review screen does with an OCR crop
    assert view.has_image()
