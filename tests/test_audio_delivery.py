from pathlib import Path

import piste_studio.audio_delivery as ad
from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.project import init_project


def make_delivery_project(tmp_path: Path):
    root = tmp_path / "Delivery"
    init_project(root, "Delivery")
    for name in ("voice.wav", "music.wav"):
        (root / "audio" / name).write_bytes(name.encode())
    scan_media(root)
    rows = [x for x in fetch_media_with_metadata(root) if x["kind"] == "audio"]
    by_name = {Path(x["relative_path"]).name: x for x in rows}
    for row in rows:
        set_media_metadata(
            root,
            row["id"],
            title=Path(row["relative_path"]).stem,
            duration_seconds=12.0,
        )
    return root, by_name


def test_delivery_presets_are_reference_only():
    presets = ad.delivery_presets()
    assert {x["id"] for x in presets} >= {"online_reference", "broadcast_reference", "custom"}
    assert all(x["reference_only"] is True for x in presets)


def test_master_render_plan_uses_sum_automation_fades_pan_and_solo(tmp_path):
    root, rows = make_delivery_project(tmp_path)
    timeline = {
        "edit_name": "mix",
        "duration_seconds": 20,
        "tracks": [
            {"id": "vo", "kind": "audio", "solo": True},
            {"id": "music", "kind": "music", "solo": False},
        ],
        "clips": [
            {
                "id": "v1",
                "track": "vo",
                "audioDbId": rows["voice.wav"]["id"],
                "start": 2,
                "duration": 5,
                "sourceStart": 1,
                "gainDb": -6,
                "pan": 0.25,
                "fadeIn": 0.2,
                "fadeOut": 0.4,
                "volumeEnvelope": [
                    {"time": 0, "gainDb": -6},
                    {"time": 2.5, "gainDb": -12},
                    {"time": 5, "gainDb": -6},
                ],
            },
            {
                "id": "m1",
                "track": "music",
                "audioDbId": rows["music.wav"]["id"],
                "start": 0,
                "duration": 10,
                "sourceStart": 0,
                "gainDb": -10,
            },
        ],
    }
    plan = ad.build_master_render_plan(root, timeline)
    assert len(plan["inputs"]) == 1
    assert plan["clips"][0]["clip_id"] == "v1"
    assert "volume='" in plan["filter_complex"]
    assert "afade=t=in" in plan["filter_complex"]
    assert "afade=t=out" in plan["filter_complex"]
    assert "pan=stereo" in plan["filter_complex"]
    assert "adelay=2000|2000" in plan["filter_complex"]
    assert "amix=inputs=1" in plan["filter_complex"]
    assert plan["limiter"] is False


def test_limiter_is_opt_in(tmp_path):
    root, rows = make_delivery_project(tmp_path)
    timeline = {
        "duration_seconds": 10,
        "tracks": [{"id": "music", "kind": "music"}],
        "clips": [{
            "id": "m1",
            "track": "music",
            "audioDbId": rows["music.wav"]["id"],
            "start": 0,
            "duration": 5,
            "sourceStart": 0,
            "gainDb": -6,
        }],
    }
    clean = ad.build_master_render_plan(root, timeline, limiter=False)
    limited = ad.build_master_render_plan(root, timeline, limiter=True, limiter_ceiling_db=-1)
    assert "alimiter=" not in clean["filter_complex"]
    assert "alimiter=" in limited["filter_complex"]
    assert limited["limiter"] is True


def test_master_evaluation_reports_loudness_and_peak_separately():
    good = ad.evaluate_master_measurement(
        {"integrated_lufs": -16.4, "true_peak_dbfs": -1.2},
        target_lufs=-16,
        true_peak_ceiling=-1,
        loudness_tolerance_lu=1,
    )
    assert good["status"] == "PASS"
    assert good["loudness_ok"] is True
    assert good["true_peak_ok"] is True

    bad = ad.evaluate_master_measurement(
        {"integrated_lufs": -13.0, "true_peak_dbfs": -0.2},
        target_lufs=-16,
        true_peak_ceiling=-1,
        loudness_tolerance_lu=1,
    )
    assert bad["status"] == "WARN"
    assert bad["loudness_ok"] is False
    assert bad["true_peak_ok"] is False
    assert len(bad["reasons"]) == 2


def test_master_check_writes_exportable_report(tmp_path, monkeypatch):
    root, rows = make_delivery_project(tmp_path)
    rendered = root / "cache" / "audio_delivery" / "mix_master_check.wav"
    rendered.parent.mkdir(parents=True, exist_ok=True)
    rendered.write_bytes(b"wav")
    timeline = {
        "edit_name": "mix",
        "duration_seconds": 10,
        "tracks": [{"id": "vo", "kind": "audio"}],
        "clips": [{
            "id": "v1",
            "track": "vo",
            "audioDbId": rows["voice.wav"]["id"],
            "start": 0,
            "duration": 5,
            "sourceStart": 0,
            "gainDb": -6,
        }],
    }

    monkeypatch.setattr(
        ad,
        "render_master_mix",
        lambda root, timeline, limiter=False, limiter_ceiling_db=-1: {
            "path": rendered,
            "relative_path": rendered.relative_to(root).as_posix(),
            "plan": {"duration_seconds": 10, "clips": [{"clip_id": "v1"}]},
        },
    )
    monkeypatch.setattr(
        ad,
        "measure_loudness",
        lambda path, target_lufs=-16, true_peak_ceiling=-1: {
            "integrated_lufs": -16.2,
            "true_peak_dbfs": -1.3,
            "loudness_range_lu": 5.1,
            "threshold_lufs": -27.0,
        },
    )

    report = ad.run_master_check(root, timeline)
    assert report["evaluation"]["status"] == "PASS"
    assert report["policy"]["measured_after_sum"] is True
    assert report["policy"]["automatic_limiter"] is False
    assert report["render"]["limiter_enabled"] is False
    path = root / report["report_relative_path"]
    assert path.exists()
    assert ad.report_path(root, report["report_name"]) == path
