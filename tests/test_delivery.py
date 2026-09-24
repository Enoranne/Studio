from pathlib import Path
import json
import shutil
import subprocess

import pytest

from piste_studio.delivery import (
    DeliveryError,
    build_delivery_ffmpeg_args,
    delivery_file_path,
    delivery_report_path,
    delivery_targets,
    estimate_fill_crop,
    preflight_delivery,
    render_delivery_variant,
    resolve_delivery_target,
    timeline_delivery_fingerprint,
    write_delivery_report,
)


def _timeline():
    return {
        "schema_version": 6,
        "edit_name": "teaser_30",
        "duration_seconds": 10,
        "storyline": {"mode": "magnetic", "start": 0},
        "tracks": [
            {"id": "video", "name": "VIDEO", "kind": "video"},
            {"id": "titles", "name": "TITLES", "kind": "title"},
        ],
        "clips": [
            {
                "id": "v1",
                "track": "video",
                "label": "Plan",
                "start": 0,
                "duration": 10,
                "sourceStart": 0,
            },
            {
                "id": "t1",
                "track": "titles",
                "label": "Titre",
                "text": "Titre",
                "start": 2,
                "duration": 2,
                "sourceStart": 0,
            },
        ],
    }


def _published_version(root: Path, timeline: dict):
    version_dir = root / "edits" / "teaser_30" / "V001"
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / "timeline.json").write_text(
        json.dumps(timeline),
        encoding="utf-8",
    )
    (version_dir / "authoring-plan.json").write_text(
        json.dumps(
            {
                "deliverable": {
                    "canvas": {"width": 1920, "height": 1080}
                }
            }
        ),
        encoding="utf-8",
    )
    (version_dir / "authoring-manifest.json").write_text(
        json.dumps(
            {
                "title_layers": [],
                "unmaterialized_titles": [{"clip_id": "t1"}],
            }
        ),
        encoding="utf-8",
    )
    return version_dir


def test_delivery_targets_cover_festival_online_and_social():
    targets = {item["id"]: item for item in delivery_targets()}
    assert "festival_prores_1080" in targets
    assert "festival_h264_1080" in targets
    assert "online_1080" in targets
    assert "social_vertical_1080x1920" in targets
    assert "social_square_1080" in targets
    assert targets["festival_prores_1080"]["container"] == "mov"
    assert targets["social_vertical_1080x1920"]["framing_modes"] == [
        "fit",
        "fill",
    ]


def test_vertical_fill_crop_estimate_and_explicit_permission():
    target = resolve_delivery_target("social_vertical_1080x1920")
    crop = estimate_fill_crop(16 / 9, target["width"], target["height"])
    assert crop["axis"] == "width"
    assert crop["percent"] == pytest.approx(68.4, abs=0.1)

    with pytest.raises(DeliveryError, match="autorisation explicite"):
        build_delivery_ffmpeg_args(
            "ffmpeg",
            Path("source.mp4"),
            Path("out.mp4"),
            target,
            framing_mode="fill",
            allow_crop=False,
        )
    args = build_delivery_ffmpeg_args(
        "ffmpeg",
        Path("source.mp4"),
        Path("out.mp4"),
        target,
        framing_mode="fill",
        allow_crop=True,
    )
    assert any("crop=1080:1920" in item for item in args)


def test_timeline_delivery_fingerprint_ignores_updated_at():
    a = _timeline()
    b = {**a, "updated_at": "tomorrow"}
    assert timeline_delivery_fingerprint(a) == timeline_delivery_fingerprint(b)
    b["clips"] = [dict(x) for x in a["clips"]]
    b["clips"][0]["duration"] = 9
    assert timeline_delivery_fingerprint(a) != timeline_delivery_fingerprint(b)


def test_preflight_reports_titles_audio_and_crop(tmp_path):
    root = tmp_path / "Project"
    root.mkdir()
    timeline = _timeline()
    _published_version(root, timeline)

    blocked = preflight_delivery(
        root,
        timeline,
        edit_name="teaser_30",
        version="V001",
        target_id="social_vertical_1080x1920",
        framing_mode="fill",
        allow_crop=False,
        audio_status={
            "status": "WARN",
            "message": "Master Check avec écart.",
            "reasons": ["LUFS hors cible."],
        },
    )
    assert blocked["checks"]["published_version"]["status"] == "PASS"
    assert blocked["checks"]["titles"]["status"] == "WARN"
    assert blocked["checks"]["audio"]["status"] == "WARN"
    assert blocked["checks"]["framing"]["status"] == "BLOCKED"
    assert blocked["can_export"] is False

    allowed = preflight_delivery(
        root,
        timeline,
        edit_name="teaser_30",
        version="V001",
        target_id="social_vertical_1080x1920",
        framing_mode="fill",
        allow_crop=True,
        audio_status={
            "status": "PASS",
            "message": "Master Check valide.",
            "reasons": [],
        },
    )
    assert allowed["can_export"] is True
    assert allowed["requires_confirmation"] is True
    assert allowed["checks"]["framing"]["crop_estimate"]["percent"] == pytest.approx(
        68.4,
        abs=0.1,
    )
    assert allowed["checks"]["titles"]["unmaterialized_count"] == 1

    changed = _timeline()
    changed["clips"] = [dict(x) for x in changed["clips"]]
    changed["clips"][0]["duration"] = 9
    stale = preflight_delivery(
        root,
        changed,
        edit_name="teaser_30",
        version="V001",
        target_id="festival_h264_1080",
        audio_status={"status": "PASS", "message": "OK", "reasons": []},
    )
    assert stale["checks"]["published_version"]["status"] == "STALE"


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="ffmpeg/ffprobe requis",
)
def test_real_ffmpeg_social_vertical_fit_and_report(tmp_path):
    root = tmp_path / "Project"
    root.mkdir()
    source = root / "source.mp4"
    create = subprocess.run(
        [
            shutil.which("ffmpeg"),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:sample_rate=48000",
            "-t",
            "0.25",
            "-c:v",
            "mpeg4",
            "-q:v",
            "5",
            "-c:a",
            "aac",
            str(source),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert create.returncode == 0, create.stderr

    render = render_delivery_variant(
        root,
        source,
        edit_name="teaser_30",
        version="V001",
        target_id="social_vertical_1080x1920",
        framing_mode="fit",
    )
    assert render["path"].exists()
    assert render["probe"]["width"] == 1080
    assert render["probe"]["height"] == 1920
    assert render["probe"]["video_codec"] == "h264"
    assert render["probe"]["audio_codec"] == "aac"
    assert render["probe"]["audio_sample_rate"] == 48000

    preflight = {
        "version": "test",
        "can_export": True,
        "checks": {},
    }
    report = write_delivery_report(
        root,
        edit_name="teaser_30",
        version="V001",
        preflight=preflight,
        render=render,
        source_relative_path="source.mp4",
    )
    assert delivery_report_path(root, report["report_name"]).exists()
    assert delivery_file_path(
        root,
        "teaser_30",
        "V001",
        render["path"].name,
    ) == render["path"]
