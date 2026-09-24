from piste_studio.project import init_project
from piste_studio.storyline import attach_clip, magnetic_reflow
from piste_studio.timeline import validate_timeline
from piste_studio.timebase import (
    TICKS_PER_SECOND,
    frame_time_ticks,
    seconds_to_ticks,
    ticks_to_seconds,
)


def test_integer_timebase_normalizes_binary_float_noise():
    noisy = 0.1 + 0.2
    assert seconds_to_ticks(noisy) == 300_000
    assert ticks_to_seconds(seconds_to_ticks(noisy)) == 0.3
    assert TICKS_PER_SECOND == 1_000_000


def test_rational_frame_time_is_deterministic():
    assert frame_time_ticks(24, 24, 1) == 1_000_000
    assert frame_time_ticks(24_000, 24_000, 1001) == 1_001_000_000
    assert frame_time_ticks(1, 24_000, 1001) == 41_708


def test_storyline_reflow_uses_integer_timebase_without_drift():
    clips = [
        {
            "id": f"v{i}",
            "track": "video",
            "start": 0,
            "duration": 0.1,
            "sourceStart": 0,
        }
        for i in range(100)
    ]
    doc = {
        "duration_seconds": 20,
        "storyline": {"mode": "magnetic", "start": 0.1},
        "clips": clips,
    }
    reflowed = magnetic_reflow(doc, story_start=0.1)
    story = sorted(reflowed["clips"], key=lambda c: c["start"])
    assert story[0]["start"] == 0.1
    assert story[49]["start"] == 5.0
    assert story[-1]["start"] == 10.0


def test_connection_offset_is_normalized_to_ticks():
    doc = {
        "duration_seconds": 10,
        "clips": [
            {"id": "v1", "track": "video", "start": 0.1, "duration": 1.0},
            {
                "id": "t1",
                "track": "titles",
                "start": 0.1 + 0.2,
                "duration": 0.2,
            },
        ],
    }
    attached = attach_clip(doc, "t1", "v1")
    child = next(c for c in attached["clips"] if c["id"] == "t1")
    assert child["anchorOffset"] == 0.2
    assert child["start"] == 0.3


def test_timeline_validator_normalizes_public_seconds_to_same_timebase(tmp_path):
    root = tmp_path / "TimebaseProject"
    init_project(root, "Timebase")
    noisy_start = 0.1 + 0.2
    doc = {
        "edit_name": "timebase",
        "duration_seconds": 2,
        "storyline": {"mode": "magnetic", "start": noisy_start},
        "tracks": [
            {"id": "video", "name": "VIDEO", "kind": "video"},
            {"id": "titles", "name": "TITLES", "kind": "title"},
        ],
        "clips": [
            {
                "id": "v1",
                "track": "video",
                "start": noisy_start,
                "duration": 0.4,
                "sourceStart": 0,
            },
            {
                "id": "t1",
                "track": "titles",
                "label": "Titre",
                "start": 0.5,
                "duration": 0.1,
                "parentClipId": "v1",
                "anchorOffset": 0.2,
                "connectionMode": "follow",
            },
        ],
    }
    clean = validate_timeline(root, doc)
    by_id = {clip["id"]: clip for clip in clean["clips"]}
    assert clean["storyline"]["start"] == 0.3
    assert by_id["v1"]["start"] == 0.3
    assert by_id["t1"]["anchorOffset"] == 0.2
    assert by_id["t1"]["connectionPointOffset"] == 0.2
