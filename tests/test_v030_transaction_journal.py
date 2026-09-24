import json

import pytest

from piste_studio.history import (
    HistoryError,
    create_checkpoint,
    history_status,
    record_transaction,
    redo_checkpoint,
    undo_checkpoint,
)
from piste_studio.project import init_project
from piste_studio.timeline import load_timeline, save_timeline


def timeline(start=3.0, label="A"):
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
                "label": label,
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


def test_transaction_undo_redo_round_trip(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "Journal")
    before = timeline(3)
    after = timeline(5)

    result = record_transaction(
        root,
        before,
        after,
        reason="Move Storyline",
        actor="user",
        operation="storyline.move",
        affected=["v1"],
    )
    assert result["can_undo"] is True
    assert result["can_redo"] is False
    assert result["transaction"]["actor"] == "user"
    assert result["transaction"]["operation"] == "storyline.move"
    assert result["transaction"]["affected"] == ["v1"]
    assert load_timeline(root, "teaser_30")["storyline"]["start"] == 5

    undone = undo_checkpoint(root, "teaser_30")
    assert undone["can_redo"] is True
    assert undone["undone"]["reason"] == "Move Storyline"
    assert load_timeline(root, "teaser_30")["storyline"]["start"] == 3

    redone = redo_checkpoint(root, "teaser_30")
    assert redone["can_undo"] is True
    assert redone["can_redo"] is False
    assert redone["redone"]["reason"] == "Move Storyline"
    assert load_timeline(root, "teaser_30")["storyline"]["start"] == 5


def test_new_transaction_after_undo_discards_redo_branch_without_reusing_id(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "Branching Journal")

    first = record_transaction(
        root,
        timeline(1),
        timeline(2),
        reason="first",
        operation="storyline.move",
    )
    second = record_transaction(
        root,
        timeline(2),
        timeline(3),
        reason="second",
        operation="storyline.move",
    )
    assert first["transaction"]["id"] == "H000001"
    assert second["transaction"]["id"] == "H000002"

    undo_checkpoint(root, "teaser_30")
    assert history_status(root, "teaser_30")["can_redo"] is True

    branched = record_transaction(
        root,
        timeline(2),
        timeline(4),
        reason="branch",
        operation="storyline.move",
    )
    status = history_status(root, "teaser_30")
    assert branched["transaction"]["id"] == "H000003"
    assert status["count"] == 2
    assert status["cursor"] == 2
    assert status["can_redo"] is False
    with pytest.raises(HistoryError, match="Aucun checkpoint"):
        redo_checkpoint(root, "teaser_30")


def test_explicit_coalesce_keeps_original_before_and_latest_after(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "Coalesce")

    first = record_transaction(
        root,
        timeline(1),
        timeline(2),
        reason="drag 1",
        actor="user",
        operation="storyline.move",
        affected=["v1"],
        coalesce_key="drag:v1",
        coalesce_window_ms=60_000,
    )
    second = record_transaction(
        root,
        timeline(2),
        timeline(3),
        reason="drag 2",
        actor="user",
        operation="storyline.move",
        affected=["v1"],
        coalesce_key="drag:v1",
        coalesce_window_ms=60_000,
    )
    assert first["transaction"]["id"] == second["transaction"]["id"]
    assert second["transaction"]["coalesced_count"] == 2
    assert history_status(root, "teaser_30")["count"] == 1

    undo_checkpoint(root, "teaser_30")
    assert load_timeline(root, "teaser_30")["storyline"]["start"] == 1
    redo_checkpoint(root, "teaser_30")
    assert load_timeline(root, "teaser_30")["storyline"]["start"] == 3


def test_legacy_checkpoint_acquires_redo_state_on_first_undo(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "Legacy Redo")
    before = timeline(3)
    after = timeline(6)
    create_checkpoint(root, before, reason="legacy")
    save_timeline(root, after)

    undone = undo_checkpoint(root, "teaser_30")
    assert undone["can_redo"] is True
    assert load_timeline(root, "teaser_30")["storyline"]["start"] == 3

    redo_checkpoint(root, "teaser_30")
    assert load_timeline(root, "teaser_30")["storyline"]["start"] == 6


def test_history_index_migrates_schema_v1_without_rewriting_project(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "Migration")
    before = timeline(3)
    cp = create_checkpoint(root, before, reason="old")
    index_path = root / "edits" / "teaser_30" / "history" / "index.json"
    legacy = json.loads(index_path.read_text(encoding="utf-8"))
    legacy["schema_version"] = 1
    legacy.pop("next_sequence", None)
    for entry in legacy["entries"]:
        for key in [
            "kind",
            "actor",
            "operation",
            "transaction_id",
            "affected",
            "before_snapshot",
        ]:
            entry.pop(key, None)
    index_path.write_text(json.dumps(legacy), encoding="utf-8")

    status = history_status(root, "teaser_30")
    assert status["schema_version"] == 2
    assert status["can_undo"] is True
    assert cp["checkpoint"]["id"] == "H000001"


def test_actor_is_explicitly_limited(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "Actor")
    with pytest.raises(HistoryError, match="user, agent ou system"):
        record_transaction(
            root,
            timeline(1),
            timeline(2),
            actor="robot",
        )
