from pathlib import Path
import json
import shutil
import subprocess

import pytest

from piste_studio.delivery import (
    DeliveryError,
    build_delivery_ffmpeg_args,
    all_delivery_targets,
    create_project_delivery_preset,
    delete_project_delivery_preset,
    duplicate_delivery_preset,
    export_delivery_preset,
    get_default_delivery_preset_id,
    import_delivery_preset,
    list_project_delivery_presets,
    delivery_file_path,
    delivery_report_path,
    delivery_targets,
    estimate_fill_crop,
    evaluate_delivery_probe,
    preflight_delivery,
    render_delivery_variant,
    resolve_delivery_target,
    set_default_delivery_preset,
    update_project_delivery_preset,
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
    assert render["conformance"]["status"] == "PASS"
    assert render["conformance"]["reasons"] == []

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



def test_delivery_conformance_warns_on_pixel_format_and_missing_audio():
    target = resolve_delivery_target("online_1080")
    result = evaluate_delivery_probe(
        target,
        {
            "video_codec": "h264",
            "width": 1920,
            "height": 1080,
            "pixel_format": "yuv422p",
            "fps": 24.0,
            "audio_codec": None,
            "audio_sample_rate": None,
            "audio_channels": None,
        },
    )
    assert result["status"] == "WARN"
    assert any("Pixel format" in x for x in result["reasons"])
    assert any("Piste audio attendue" in x for x in result["reasons"])



def test_project_delivery_preset_crud_default_and_normalization(tmp_path):
    root = tmp_path / "ProjectPresets"
    root.mkdir()

    assert get_default_delivery_preset_id(root) == "online_1080"
    assert list_project_delivery_presets(root) == []

    copy = duplicate_delivery_preset(
        root,
        "online_1080",
        label="YouTube PISTE 0",
    )
    assert copy["custom"] is True
    assert copy["id"].startswith("custom_youtube_piste_0")
    assert copy["container"] == "mp4"
    assert copy["pixel_format"] == "yuv420p"
    assert (root / "delivery-presets.yaml").exists()

    updated = update_project_delivery_preset(
        root,
        copy["id"],
        {
            "label": "Vertical PISTE 0",
            "family": "social",
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "video_codec": "libx264",
            "video_bitrate_mbps": 15,
            "audio_bitrate_kbps": 320,
            "tesseract_resolution": "1080p",
            "default_framing": "fill",
        },
    )
    assert updated["aspect_ratio"] == "9:16"
    assert updated["fps"] == 30
    assert updated["video_bitrate_mbps"] == 15
    assert updated["audio_bitrate_kbps"] == 320
    assert updated["framing_modes"] == ["fit", "fill"]
    assert updated["default_framing"] == "fill"

    resolved = resolve_delivery_target(updated["id"], root=root)
    assert resolved["label"] == "Vertical PISTE 0"
    assert resolved["custom"] is True

    assert set_default_delivery_preset(root, updated["id"]) == updated["id"]
    assert get_default_delivery_preset_id(root) == updated["id"]

    combined = all_delivery_targets(root)
    assert any(x["id"] == updated["id"] for x in combined)
    assert any(x["id"] == "festival_prores_1080" for x in combined)

    delete_project_delivery_preset(root, updated["id"])
    assert list_project_delivery_presets(root) == []
    assert get_default_delivery_preset_id(root) == "online_1080"


def test_delivery_preset_integrated_immutable_and_validation(tmp_path):
    root = tmp_path / "ProjectPresetValidation"
    root.mkdir()

    with pytest.raises(DeliveryError, match="immuable"):
        update_project_delivery_preset(
            root,
            "online_1080",
            {"label": "Nope"},
        )
    with pytest.raises(DeliveryError, match="intégré"):
        delete_project_delivery_preset(root, "online_1080")

    with pytest.raises(DeliveryError, match="paires"):
        create_project_delivery_preset(
            root,
            {
                "label": "Odd",
                "family": "custom",
                "width": 1081,
                "height": 1920,
                "fps": 24,
                "video_codec": "libx264",
            },
        )
    with pytest.raises(DeliveryError, match="24, 30 ou 60"):
        create_project_delivery_preset(
            root,
            {
                "label": "25 fps",
                "family": "custom",
                "width": 1920,
                "height": 1080,
                "fps": 25,
                "video_codec": "libx264",
            },
        )
    with pytest.raises(DeliveryError, match="1 à 200"):
        create_project_delivery_preset(
            root,
            {
                "label": "Too much",
                "family": "custom",
                "width": 1920,
                "height": 1080,
                "fps": 24,
                "video_codec": "libx264",
                "video_bitrate_mbps": 500,
            },
        )

    prores = create_project_delivery_preset(
        root,
        {
            "label": "Projection HQ",
            "family": "festival",
            "width": 1920,
            "height": 1080,
            "fps": 24,
            "video_codec": "prores_ks",
            "video_bitrate_mbps": 2,
            "audio_bitrate_kbps": 96,
        },
    )
    assert prores["container"] == "mov"
    assert prores["pixel_format"] == "yuv422p10le"
    assert prores["audio_codec"] == "pcm_s24le"
    assert "video_bitrate_mbps" not in prores
    assert "audio_bitrate_kbps" not in prores


def test_delivery_preset_export_import_round_trip(tmp_path):
    source_root = tmp_path / "PresetSource"
    target_root = tmp_path / "PresetTarget"
    source_root.mkdir()
    target_root.mkdir()

    custom = create_project_delivery_preset(
        source_root,
        {
            "label": "Festival Maison",
            "family": "festival",
            "width": 2048,
            "height": 1080,
            "fps": 24,
            "video_codec": "libx264",
            "video_bitrate_mbps": 30,
            "audio_bitrate_kbps": 320,
            "tesseract_resolution": "4k",
            "default_framing": "fit",
            "notes": ["Fiche technique test"],
        },
    )
    document = export_delivery_preset(source_root, custom["id"])
    assert document["kind"] == "piste_studio_delivery_preset"
    assert document["preset"]["label"] == "Festival Maison"

    imported = import_delivery_preset(target_root, document)
    assert imported["custom"] is True
    assert imported["label"] == "Festival Maison"
    assert imported["width"] == 2048
    assert imported["height"] == 1080
    assert imported["video_bitrate_mbps"] == 30
    assert imported["tesseract_resolution"] == "4k"
    assert imported["id"] != custom["id"] or imported["id"].startswith("custom_")
