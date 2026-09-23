from piste_studio.history import (
    HistoryError,
    create_checkpoint,
    history_status,
    undo_checkpoint,
)
from piste_studio.project import init_project
from piste_studio.timeline import load_timeline, save_timeline


def timeline(start=3.0):
    return {
        "edit_name": "teaser_30",
        "duration_seconds": 30,
        "storyline": {"mode": "magnetic", "start": start},
        "tracks": [
            {"id": "video", "name": "VIDEO", "kind": "video"},
            {"id": "titles", "name": "TITLES", "kind": "title"},
        ],
        "clips": [
            {
                "id": "v1",
                "track": "video",
                "label": "A",
                "start": start,
                "duration": 4,
                "sourceStart": 0,
            },
            {
                "id": "t1",
                "track": "titles",
                "label": "Titre",
                "start": start + 1,
                "duration": 1,
                "sourceStart": 0,
                "parentClipId": "v1",
                "anchorOffset": 1,
                "connectionMode": "follow",
            },
        ],
    }


def test_checkpoint_and_undo_restore_timeline(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "History")
    before = timeline()
    save_timeline(root, before)
    cp = create_checkpoint(root, before, reason="before ripple")
    assert cp["can_undo"] is True
    assert cp["count"] == 1

    changed = timeline(5)
    save_timeline(root, changed)
    restored = undo_checkpoint(root, "teaser_30")
    assert restored["restored"]["reason"] == "before ripple"
    current = load_timeline(root, "teaser_30")
    assert current["storyline"]["start"] == 3
    assert current["clips"][0]["start"] == 3
    assert history_status(root, "teaser_30")["can_undo"] is False


def test_new_checkpoint_after_undo_discards_redo_branch(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "History")
    first = timeline()
    create_checkpoint(root, first, reason="first")
    second = timeline(5)
    create_checkpoint(root, second, reason="second")
    undo_checkpoint(root, "teaser_30")

    create_checkpoint(root, second, reason="branch")
    status = history_status(root, "teaser_30")
    assert status["count"] == 2
    assert status["cursor"] == 2
    assert status["last"]["reason"] == "branch"


def test_undo_without_checkpoint_is_explicit(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "History")
    try:
        undo_checkpoint(root, "teaser_30")
    except HistoryError as exc:
        assert "Aucun checkpoint" in str(exc)
    else:
        raise AssertionError("HistoryError attendu")
