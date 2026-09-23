from pathlib import Path
import math
import shutil
import struct
import wave

import pytest
from fastapi.testclient import TestClient

import piste_studio.audio_delivery as ad
from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.project import init_project
from piste_studio.timeline import save_timeline
from piste_studio.app import create_app
import piste_studio.app as app_module


def _write_sine_wav(path: Path, *, seconds: float = 3.0, frequency: float = 440.0, amplitude: float = 0.18):
    sample_rate = 48000
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index in range(frames):
            sample = amplitude * math.sin(2 * math.pi * frequency * index / sample_rate)
            wav.writeframesraw(struct.pack("<h", int(max(-1, min(1, sample)) * 32767)))


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


def test_audio_master_check_api_returns_downloadable_report(tmp_path, monkeypatch):
    root, rows = make_delivery_project(tmp_path)
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
    report_file = root / "reports" / "audio" / "mix_master_check.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text('{"status":"ok"}\n', encoding="utf-8")

    monkeypatch.setattr(
        app_module,
        "run_master_check",
        lambda root, clean, **kwargs: {
            "version": ad.AUDIO_DELIVERY_VERSION,
            "edit_name": "mix",
            "preset": {
                "id": "online_reference",
                "target_lufs": -16.0,
                "true_peak_ceiling": -1.0,
                "loudness_tolerance_lu": 1.0,
            },
            "measurement": {
                "integrated_lufs": -16.1,
                "true_peak_dbfs": -1.2,
                "loudness_range_lu": 4.0,
                "threshold_lufs": -27.0,
            },
            "evaluation": {"status": "PASS"},
            "render": {"limiter_enabled": False},
            "policy": {
                "measured_after_sum": True,
                "limiter_requires_explicit_choice": True,
            },
            "report_name": report_file.name,
            "report_relative_path": report_file.relative_to(root).as_posix(),
        },
    )

    app = create_app(root, Path(__file__).parents[1] / "piste_studio" / "ui" / "index.html")
    client = TestClient(app)
    presets = client.get("/api/audio/delivery/presets")
    assert presets.status_code == 200
    assert presets.json()["version"] == ad.AUDIO_DELIVERY_VERSION

    response = client.post("/api/audio/master/check", json={"timeline": timeline})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["evaluation"]["status"] == "PASS"
    assert body["report_url"].endswith("/mix_master_check.json")

    downloaded = client.get(body["report_url"])
    assert downloaded.status_code == 200
    assert downloaded.json()["status"] == "ok"


def test_master_check_status_tracks_freshness(tmp_path, monkeypatch):
    root, rows = make_delivery_project(tmp_path)
    rendered = root / "cache" / "audio_delivery" / "mix_master_check.wav"
    rendered.parent.mkdir(parents=True, exist_ok=True)
    rendered.write_bytes(b"wav")
    timeline = {
        "edit_name": "mix",
        "duration_seconds": 8,
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
            "plan": {"duration_seconds": 8, "clips": [{"clip_id": "v1"}]},
        },
    )
    monkeypatch.setattr(
        ad,
        "measure_loudness",
        lambda *args, **kwargs: {
            "integrated_lufs": -16.2,
            "true_peak_dbfs": -1.4,
            "loudness_range_lu": 3.0,
            "threshold_lufs": -27.0,
        },
    )
    ad.run_master_check(root, timeline)
    fresh = ad.master_check_status(root, timeline)
    assert fresh["status"] == "PASS"
    assert fresh["can_export"] is True

    changed = {
        **timeline,
        "clips": [{**timeline["clips"][0], "gainDb": -3}],
    }
    stale = ad.master_check_status(root, changed)
    assert stale["status"] == "STALE"
    assert stale["previous_status"] == "PASS"
    assert stale["can_export"] is True

    (root / fresh["report_relative_path"]).unlink()
    missing = ad.master_check_status(root, changed)
    assert missing["status"] == "MISSING"
    assert missing["can_export"] is True


def test_master_check_real_ffmpeg_end_to_end(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg système requis pour le test end-to-end")

    root = tmp_path / "RealFFmpeg"
    init_project(root, "Real FFmpeg")
    _write_sine_wav(root / "audio" / "voice.wav", frequency=330.0)
    _write_sine_wav(root / "audio" / "music.wav", frequency=550.0, amplitude=0.12)
    scan_media(root)
    rows = [x for x in fetch_media_with_metadata(root) if x["kind"] == "audio"]
    by_name = {Path(x["relative_path"]).name: x for x in rows}
    for row in rows:
        set_media_metadata(
            root,
            row["id"],
            title=Path(row["relative_path"]).stem,
            duration_seconds=3.0,
        )

    timeline = {
        "edit_name": "real_mix",
        "duration_seconds": 3.0,
        "tracks": [
            {"id": "vo", "kind": "audio"},
            {"id": "music", "kind": "music"},
        ],
        "clips": [
            {
                "id": "v1",
                "track": "vo",
                "audioDbId": by_name["voice.wav"]["id"],
                "start": 0,
                "duration": 3,
                "sourceStart": 0,
                "gainDb": -6,
                "pan": -0.15,
                "fadeIn": 0.1,
                "fadeOut": 0.1,
                "volumeEnvelope": [
                    {"time": 0, "gainDb": -9},
                    {"time": 1.5, "gainDb": -6},
                    {"time": 3, "gainDb": -9},
                ],
            },
            {
                "id": "m1",
                "track": "music",
                "audioDbId": by_name["music.wav"]["id"],
                "start": 0,
                "duration": 3,
                "sourceStart": 0,
                "gainDb": -12,
                "pan": 0.2,
                "fadeIn": 0.2,
                "fadeOut": 0.2,
            },
        ],
    }
    report = ad.run_master_check(
        root,
        timeline,
        target_lufs=-20,
        true_peak_ceiling=-0.1,
        loudness_tolerance_lu=20,
    )
    measurement = report["measurement"]
    assert measurement["integrated_lufs"] is not None
    assert measurement["true_peak_dbfs"] is not None
    assert measurement["loudness_range_lu"] is not None
    assert report["evaluation"]["status"] == "PASS"
    assert report["audio_mix_fingerprint"] == ad.audio_mix_fingerprint(timeline)
    assert (root / report["render"]["relative_path"]).exists()
    assert (root / report["report_relative_path"]).exists()


def test_export_api_reports_audio_preflight_without_blocking(tmp_path, monkeypatch):
    root, rows = make_delivery_project(tmp_path)
    timeline = {
        "edit_name": "mix",
        "duration_seconds": 8,
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
    save_timeline(root, timeline)
    report_dir = root / "reports" / "audio"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "mix_master_check.json"
    report_path.write_text(
        __import__("json").dumps({
            "created_at": "2026-09-23T00:00:00+00:00",
            "audio_mix_fingerprint": ad.audio_mix_fingerprint(timeline),
            "evaluation": {"status": "PASS", "reasons": []},
            "measurement": {"integrated_lufs": -16.0, "true_peak_dbfs": -1.2},
            "preset": {"target_lufs": -16.0, "true_peak_ceiling": -1.0},
        }),
        encoding="utf-8",
    )

    changed = {
        **timeline,
        "clips": [{**timeline["clips"][0], "gainDb": -3}],
    }
    save_timeline(root, changed)
    output = root / "exports" / "test.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"export")
    monkeypatch.setattr(app_module, "execute_export", lambda *args, **kwargs: output)

    app = create_app(root, Path(__file__).parents[1] / "piste_studio" / "ui" / "index.html")
    client = TestClient(app)
    status = client.get("/api/audio/master/status?edit_name=mix")
    assert status.status_code == 200
    assert status.json()["status"] == "STALE"
    assert status.json()["can_export"] is True

    exported = client.post(
        "/api/tesseract/V001/export",
        json={"edit_name": "mix", "resolution": "1080p", "fps": 24, "format": "mp4"},
    )
    assert exported.status_code == 200, exported.text
    assert exported.json()["path"] == "exports/test.mp4"
    assert exported.json()["audio_delivery"]["status"] == "STALE"
    assert exported.json()["audio_delivery"]["can_export"] is True
