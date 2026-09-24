import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from piste_studio.app import create_app
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


ROOT = Path(__file__).parents[1]
UI = ROOT / "piste_studio" / "ui" / "index.html"


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


def test_storyline_api_records_transaction_and_supports_redo(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "API Journal")
    app = create_app(root, UI)
    client = TestClient(app)

    response = client.post(
        "/api/storyline/operate",
        json={
            "timeline": timeline(3),
            "operation": "trim",
            "args": {
                "clip_id": "v1",
                "edge": "right",
                "delta": 0.5,
            },
            "edit_name": "teaser_30",
            "checkpoint_reason": "Ripple trim",
            "actor": "user",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["checkpoint"]["can_undo"] is True
    assert body["checkpoint"]["last"]["actor"] == "user"
    assert body["checkpoint"]["last"]["operation"] == "storyline.trim"
    assert body["checkpoint"]["last"]["affected"] == ["v1"]
    assert load_timeline(root, "teaser_30")["clips"][0]["duration"] == 4.5

    undone = client.post(
        "/api/history/undo",
        json={"edit_name": "teaser_30"},
    )
    assert undone.status_code == 200, undone.text
    assert undone.json()["can_redo"] is True
    assert load_timeline(root, "teaser_30")["clips"][0]["duration"] == 4

    redone = client.post(
        "/api/history/redo",
        json={"edit_name": "teaser_30"},
    )
    assert redone.status_code == 200, redone.text
    assert redone.json()["redone"]["reason"] == "Ripple trim"
    assert load_timeline(root, "teaser_30")["clips"][0]["duration"] == 4.5


def test_v030_integrates_audio_agent_and_ui_provenance():
    app_source = (ROOT / "piste_studio" / "app.py").read_text(encoding="utf-8")
    agent_source = (
        ROOT / "piste_studio" / "editorial_agent.py"
    ).read_text(encoding="utf-8")
    ui_source = (
        ROOT / "piste_studio" / "ui" / "ux-magnetic.js"
    ).read_text(encoding="utf-8")

    assert 'operation="audio.normalize"' in app_source
    assert 'operation="audio.ducking"' in app_source
    assert 'operation="audio.crossfade"' in app_source
    assert 'actor="agent"' in agent_source
    assert 'operation="editorial.apply_proposal"' in agent_source
    assert "/api/history/redo" in ui_source
    assert "redoLastEdit" in ui_source
    assert "key==='z'&&e.shiftKey" in ui_source
    assert "key==='y'" in ui_source
