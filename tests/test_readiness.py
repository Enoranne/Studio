from pathlib import Path
import json
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from piste_studio.app import create_app
from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.project import init_project
from piste_studio.readiness import build_production_readiness
from piste_studio.tesseract_bridge import save_tesseract_config
from piste_studio.versioning import create_timeline_version


FAKE_CLI = r'''#!/usr/bin/python3
import sys
if sys.argv[1:] == ['--version']:
    print('Tesseract CLI v0.2.0')
    raise SystemExit(0)
print('unsupported', file=sys.stderr)
raise SystemExit(2)
'''


def make_project(tmp_path: Path, *, with_media: bool = True) -> Path:
    root = tmp_path / "PISTE_0"
    init_project(root, "PISTE 0")
    if with_media:
        (root / "rushes" / "shot.mp4").write_bytes(b"video")
        (root / "audio" / "voice.wav").write_bytes(b"audio")
        scan_media(root)
        for row in fetch_media_with_metadata(root):
            set_media_metadata(
                root,
                row["id"],
                title=Path(row["relative_path"]).stem,
                duration_seconds=10.0,
            )
    return root


def publish_timeline(root: Path):
    rows = fetch_media_with_metadata(root)
    video_id = next(row["id"] for row in rows if row["kind"] == "video")
    timeline = {
        "edit_name": "teaser_30",
        "duration_seconds": 30,
        "tracks": [
            {"id": "video", "name": "VIDEO", "kind": "video"},
        ],
        "clips": [
            {
                "id": "v1",
                "track": "video",
                "label": "shot",
                "start": 0,
                "duration": 4,
                "sourceStart": 0,
                "mediaDbId": video_id,
            },
        ],
    }
    return create_timeline_version(root, timeline)


def check_by_id(report: dict, check_id: str) -> dict:
    return next(item for item in report["checks"] if item["id"] == check_id)


@patch("piste_studio.readiness.shutil.which", side_effect=lambda name: f"/usr/bin/{name}")
def test_readiness_blocks_when_no_video_is_available(_which, tmp_path):
    root = make_project(tmp_path, with_media=False)
    report = build_production_readiness(root)
    assert report["capabilities"]["can_start_editing"] is False
    assert report["pipeline_status"] == "BLOCKED"
    assert check_by_id(report, "media")["status"] == "BLOCKED"
    assert "rush vidéo" in report["next_action"]


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable fixture")
@patch("piste_studio.readiness.shutil.which", side_effect=lambda name: f"/usr/bin/{name}")
def test_readiness_tracks_real_pipeline_stages(_which, tmp_path):
    root = make_project(tmp_path)
    rec = publish_timeline(root)
    cli = tmp_path / "tsrct"
    cli.write_text(FAKE_CLI, encoding="utf-8")
    cli.chmod(0o755)
    save_tesseract_config(root, cli_path=str(cli), expected_version="0.2.0")

    report = build_production_readiness(root, edit_name=rec.edit_name)
    assert report["selection"] == {
        "edit_name": rec.edit_name,
        "version": rec.version_label,
    }
    assert report["capabilities"]["can_start_editing"] is True
    assert report["capabilities"]["can_bootstrap"] is True
    assert report["capabilities"]["can_author"] is False
    assert "bootstrap" in report["next_action"]
    assert check_by_id(report, "authoring_plan")["video_cuts"] == 1

    version_dir = rec.directory
    (version_dir / f"{rec.edit_name}_{rec.version_label}.tsrct").write_bytes(b"project")
    work = version_dir / ".tesseract-work"
    work.mkdir(parents=True, exist_ok=True)
    (work / "document.schema.json").write_text(json.dumps({"title": "schema"}), encoding="utf-8")

    report = build_production_readiness(root, edit_name=rec.edit_name)
    assert report["capabilities"]["can_author"] is True
    assert "tesseract author" in report["next_action"]

    (version_dir / "authoring-manifest.json").write_text("{}", encoding="utf-8")
    report = build_production_readiness(root, edit_name=rec.edit_name)
    assert "tesseract export" in report["next_action"]

    (version_dir / f"{rec.edit_name}_{rec.version_label}.mp4").write_bytes(b"render")
    report = build_production_readiness(root, edit_name=rec.edit_name)
    assert report["capabilities"]["can_deliver"] is True
    assert report["pipeline_status"] == "READY_FOR_DELIVERY"
    assert "Delivery Center" in report["next_action"]


@patch("piste_studio.readiness.shutil.which", side_effect=lambda name: f"/usr/bin/{name}")
def test_readiness_does_not_guess_between_multiple_edits(_which, tmp_path):
    root = make_project(tmp_path)
    first = publish_timeline(root)
    rows = fetch_media_with_metadata(root)
    video_id = next(row["id"] for row in rows if row["kind"] == "video")
    create_timeline_version(root, {
        "edit_name": "alternate_cut",
        "duration_seconds": 30,
        "tracks": [{"id": "video", "name": "VIDEO", "kind": "video"}],
        "clips": [{
            "id": "v2", "track": "video", "start": 0, "duration": 3,
            "sourceStart": 0, "mediaDbId": video_id,
        }],
    })

    report = build_production_readiness(root)
    assert first.edit_name == "teaser_30"
    assert report["selection"]["version"] is None
    assert "Plusieurs montages" in check_by_id(report, "published_version")["message"]


@patch("piste_studio.readiness.shutil.which", side_effect=lambda name: f"/usr/bin/{name}")
def test_readiness_api_exposes_same_report(_which, tmp_path):
    root = make_project(tmp_path)
    app = create_app(
        root,
        Path(__file__).parents[1] / "piste_studio" / "ui" / "index.html",
    )
    client = TestClient(app)
    response = client.get("/api/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "0.24.0"
    assert body["project_name"] == "PISTE 0"
    assert "capabilities" in body
    assert "next_action" in body
