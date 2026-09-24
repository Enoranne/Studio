from pathlib import Path

import pytest

from piste_studio.locks import add_lock
from piste_studio.project import init_project
from piste_studio.storyline import (
    StorylineError,
    attach_clip,
    detach_clip,
    magnetic_reflow,
    move_story_clip,
    trim_story_clip,
    validate_locked_change,
)
from piste_studio.timeline import TimelineError, validate_timeline


def base_doc():
    return {
        "edit_name": "teaser_30",
        "duration_seconds": 30,
        "storyline": {"mode": "magnetic", "start": 3},
        "tracks": [
            {"id": "video", "name": "VIDEO", "kind": "video"},
            {"id": "titles", "name": "TITLES", "kind": "title"},
            {"id": "vo", "name": "VO", "kind": "audio"},
        ],
        "clips": [
            {"id": "v1", "track": "video", "label": "A", "start": 3, "duration": 4, "sourceStart": 0},
            {"id": "v2", "track": "video", "label": "B", "start": 7, "duration": 3, "sourceStart": 0},
            {"id": "v3", "track": "video", "label": "C", "start": 10, "duration": 2, "sourceStart": 0},
            {"id": "t1", "track": "titles", "label": "Titre", "start": 8, "duration": 1, "parentClipId": "v2", "anchorOffset": 1, "connectionMode": "follow"},
        ],
    }


def test_move_story_clip_reorders_and_child_follows():
    moved = move_story_clip(base_doc(), "v2", 3.1, story_start=3)
    by_id = {c["id"]: c for c in moved["clips"]}
    assert by_id["v2"]["start"] == 3
    assert by_id["v1"]["start"] == 6
    assert by_id["v3"]["start"] == 10
    assert by_id["t1"]["start"] == 4
    assert by_id["t1"]["anchorOffset"] == 1


def test_ripple_trim_moves_downstream_and_connected_child():
    trimmed = trim_story_clip(
        base_doc(), "v1", edge="right", delta=2, story_start=3
    )
    by_id = {c["id"]: c for c in trimmed["clips"]}
    assert by_id["v1"]["duration"] == 6
    assert by_id["v2"]["start"] == 9
    assert by_id["v3"]["start"] == 12
    assert by_id["t1"]["start"] == 10


def test_left_trim_changes_source_without_creating_gap():
    trimmed = trim_story_clip(
        base_doc(), "v2", edge="left", delta=1, story_start=3
    )
    by_id = {c["id"]: c for c in trimmed["clips"]}
    assert by_id["v2"]["start"] == 7
    assert by_id["v2"]["sourceStart"] == 1
    assert by_id["v2"]["duration"] == 2
    assert by_id["v3"]["start"] == 9
    assert by_id["t1"]["start"] == 8


def test_attach_and_detach_clip():
    doc = base_doc()
    doc["clips"].append(
        {"id": "a1", "track": "vo", "start": 4.5, "duration": 1}
    )
    attached = attach_clip(doc, "a1", "v1")
    a1 = next(c for c in attached["clips"] if c["id"] == "a1")
    assert a1["parentClipId"] == "v1"
    assert a1["anchorOffset"] == 1.5
    detached = detach_clip(attached, "a1")
    a1 = next(c for c in detached["clips"] if c["id"] == "a1")
    assert "parentClipId" not in a1
    assert a1["start"] == 4.5


def test_magnetic_reflow_rejects_incomplete_order():
    with pytest.raises(StorylineError):
        magnetic_reflow(base_doc(), story_start=3, order=["v1", "v2"])


def test_timeline_validator_accepts_connections_and_rejects_drift(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "Test")
    clean = validate_timeline(root, base_doc())
    assert clean["schema_version"] == 5
    assert clean["storyline"]["mode"] == "magnetic"
    assert next(c for c in clean["clips"] if c["id"] == "t1")["parentClipId"] == "v2"

    broken = base_doc()
    next(c for c in broken["clips"] if c["id"] == "t1")["start"] = 8.5
    with pytest.raises(TimelineError, match="Connexion incohérente"):
        validate_timeline(root, broken)


def test_lock_validation_blocks_ripple_through_hard_lock(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "Test")
    add_lock(root, "Protected opening", 0, 5, "HARD", ["reorder", "trim"])
    before = base_doc()
    after = move_story_clip(before, "v2", 3.1, story_start=3)
    with pytest.raises(StorylineError, match="HARD LOCK"):
        validate_locked_change(root, before, after)
