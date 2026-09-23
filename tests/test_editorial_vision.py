from pathlib import Path
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

import piste_studio.app as app_module
import piste_studio.editorial_vision as ev
from piste_studio.app import create_app
from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.project import init_project


def make_project(tmp_path: Path):
    root = tmp_path / "EditorialVision"
    init_project(root, "Editorial Vision")
    (root / "rushes" / "take.mp4").write_bytes(b"fake-video")
    scan_media(root)
    row = next(x for x in fetch_media_with_metadata(root) if x["kind"] == "video")
    set_media_metadata(
        root,
        row["id"],
        title="Take",
        duration_seconds=8.0,
    )
    return root, row


def test_parse_scene_change_times_deduplicates_showinfo():
    log = """
    [Parsed_showinfo_1] n:0 pts:24000 pts_time:1.000 pos:1
    [Parsed_showinfo_1] n:1 pts:24001 pts_time:1.010 pos:2
    [Parsed_showinfo_1] n:2 pts:48000 pts_time:2.000 pos:3
    """
    assert ev.parse_scene_change_times(log) == [1.0, 2.0]


def test_candidate_windows_are_chronological_and_explainable():
    rows = ev.build_candidate_windows(
        duration_seconds=8.0,
        scene_changes=[2.0, 5.0],
        min_window_seconds=0.75,
        threshold=0.32,
    )
    assert [(x["source_in"], x["source_out"]) for x in rows] == [
        (0.0, 2.0),
        (2.0, 5.0),
        (5.0, 8.0),
    ]
    assert "rupture visuelle" in rows[0]["reason"]
    assert rows[1]["boundary_before"] == 2.0
    assert rows[1]["boundary_after"] == 5.0
    assert all(x["method"] == "ffmpeg_scene_change" for x in rows)


def test_candidate_windows_fallback_when_segments_too_short():
    rows = ev.build_candidate_windows(
        duration_seconds=1.0,
        scene_changes=[0.3, 0.6],
        min_window_seconds=0.75,
    )
    assert len(rows) == 1
    assert rows[0]["source_in"] == 0.0
    assert rows[0]["source_out"] == 1.0
    assert rows[0]["method"] == "ffmpeg_scene_change_fallback"


def test_editorial_windows_api_is_suggestion_only(tmp_path, monkeypatch):
    root, row = make_project(tmp_path)
    monkeypatch.setattr(
        app_module,
        "suggest_editorial_windows",
        lambda root, media_id, **kwargs: {
            "version": ev.EDITORIAL_VISION_VERSION,
            "media_id": media_id,
            "duration_seconds": 8.0,
            "scene_threshold": kwargs["threshold"],
            "scene_changes": [2.0, 5.0],
            "candidates": [
                {
                    "rank": 1,
                    "source_in": 0.0,
                    "source_out": 2.0,
                    "duration": 2.0,
                    "reason": "Début du rush → rupture visuelle à 2.00 s.",
                    "method": "ffmpeg_scene_change",
                    "scene_threshold": kwargs["threshold"],
                }
            ],
            "policy": {
                "suggestion_only": True,
                "automatic_storyline_edit": False,
                "human_validation_required": True,
                "local_processing": True,
            },
        },
    )
    app = create_app(root, Path(__file__).parents[1] / "piste_studio" / "ui" / "index.html")
    client = TestClient(app)
    response = client.get(
        f"/api/media/{row['id']}/editorial-windows?threshold=0.22&min_duration=0.75&limit=12"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["scene_threshold"] == 0.22
    assert body["policy"]["suggestion_only"] is True
    assert body["policy"]["automatic_storyline_edit"] is False
    assert body["candidates"][0]["source_out"] == 2.0


def test_real_ffmpeg_detects_hard_visual_breaks(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg système requis")

    root = tmp_path / "RealScene"
    init_project(root, "Real Scene")
    output = root / "rushes" / "colors.mp4"
    proc = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-f", "lavfi", "-i", "color=c=red:s=160x90:d=1:r=24",
            "-f", "lavfi", "-i", "color=c=blue:s=160x90:d=1:r=24",
            "-f", "lavfi", "-i", "color=c=green:s=160x90:d=1:r=24",
            "-filter_complex",
            "[0:v][1:v][2:v]concat=n=3:v=1:a=0,format=yuv420p",
            "-c:v", "mpeg4",
            "-q:v", "2",
            str(output),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    scan_media(root)
    row = next(x for x in fetch_media_with_metadata(root) if x["kind"] == "video")
    set_media_metadata(root, row["id"], title="Colors", duration_seconds=3.0)

    result = ev.suggest_editorial_windows(
        root,
        row["id"],
        threshold=0.10,
        min_window_seconds=0.50,
        limit=8,
    )
    assert len(result["scene_changes"]) >= 2
    assert any(abs(x - 1.0) < 0.15 for x in result["scene_changes"])
    assert any(abs(x - 2.0) < 0.15 for x in result["scene_changes"])
    assert len(result["candidates"]) >= 3
    assert result["policy"]["automatic_storyline_edit"] is False
