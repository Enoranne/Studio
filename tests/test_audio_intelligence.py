from pathlib import Path
import subprocess

import pytest

import piste_studio.audio_intelligence as ai
from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.project import init_project
from piste_studio.timeline import TimelineError, validate_timeline


def make_audio_project(tmp_path: Path):
    root = tmp_path / "AudioIntel"
    init_project(root, "Audio Intel")
    for name in ("voice.wav", "music_a.wav", "music_b.wav"):
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


def test_measure_loudness_parses_ffmpeg_json(monkeypatch, tmp_path):
    stderr = """
    [Parsed_loudnorm] {
        "input_i" : "-20.10",
        "input_tp" : "-3.20",
        "input_lra" : "4.50",
        "input_thresh" : "-31.00",
        "output_i" : "-16.00"
    }
    """
    monkeypatch.setattr(
        ai,
        "detect_audio_tools",
        lambda: ai.AudioToolStatus(ffmpeg="/fake/ffmpeg"),
    )
    monkeypatch.setattr(
        ai,
        "_run_ffmpeg",
        lambda args: subprocess.CompletedProcess(args, 0, "", stderr),
    )
    result = ai.measure_loudness(tmp_path / "voice.wav")
    assert result["integrated_lufs"] == -20.1
    assert result["true_peak_dbfs"] == -3.2
    assert result["loudness_range_lu"] == 4.5
    assert result["threshold_lufs"] == -31.0


def test_audio_analysis_persists_with_silence(tmp_path, monkeypatch):
    root, rows = make_audio_project(tmp_path)
    voice = rows["voice.wav"]
    monkeypatch.setattr(
        ai,
        "detect_audio_tools",
        lambda: ai.AudioToolStatus(ffmpeg="/fake/ffmpeg"),
    )
    monkeypatch.setattr(
        ai,
        "measure_loudness",
        lambda path: {
            "integrated_lufs": -19.0,
            "true_peak_dbfs": -2.5,
            "loudness_range_lu": 5.2,
            "threshold_lufs": -29.0,
            "raw": {"input_i": "-19.0"},
        },
    )
    monkeypatch.setattr(
        ai,
        "detect_silence",
        lambda path: [{"start": 2.0, "end": 2.6, "duration": 0.6}],
    )
    result = ai.analyze_audio(root, voice["id"])
    assert result["status"] == "READY"
    assert result["integrated_lufs"] == -19.0
    assert result["true_peak_dbfs"] == -2.5
    assert result["silence"][0]["duration"] == 0.6


def test_normalization_is_limited_by_true_peak(tmp_path):
    root, rows = make_audio_project(tmp_path)
    voice = rows["voice.wav"]
    ai._write_analysis(
        root,
        voice["id"],
        status="READY",
        integrated_lufs=-20.0,
        true_peak_dbfs=-4.0,
        loudness_range_lu=4.0,
        threshold_lufs=-30.0,
    )
    proposal = ai.normalization_proposal(
        root,
        voice["id"],
        target_lufs=-16.0,
        true_peak_ceiling=-1.5,
    )
    assert proposal["gain_adjustment_db"] == 2.5
    assert proposal["limited_by_true_peak"] is True
    assert proposal["estimated_lufs_after"] == -17.5
    assert proposal["estimated_true_peak_after"] == -1.5
    assert proposal["policy"]["human_validation_required"] is True


def test_clipping_risk_uses_max_automation_gain(tmp_path):
    root, rows = make_audio_project(tmp_path)
    voice = rows["voice.wav"]
    ai._write_analysis(
        root,
        voice["id"],
        status="READY",
        integrated_lufs=-18,
        true_peak_dbfs=-4,
    )
    timeline = {
        "clips": [{
            "id": "a1",
            "audioDbId": voice["id"],
            "gainDb": -3,
            "volumeEnvelope": [
                {"time": 1, "gainDb": 2},
                {"time": 2, "gainDb": -6},
            ],
        }]
    }
    report = ai.clipping_risk_report(root, timeline, true_peak_ceiling=-1)
    assert report["risk_count"] == 0
    assert report["clips"][0]["estimated_true_peak_dbfs"] == -2.0
    # -2 dBTP remains below a -1 dBTP ceiling.
    assert report["clips"][0]["status"] == "OK"

    timeline["clips"][0]["volumeEnvelope"][0]["gainDb"] = 4
    report = ai.clipping_risk_report(root, timeline, true_peak_ceiling=-1)
    assert report["risk_count"] == 1
    assert report["clips"][0]["status"] == "RISK"
    assert report["clips"][0]["estimated_true_peak_dbfs"] == 0.0


def test_ducking_proposal_uses_voice_overlaps_only():
    timeline = {
        "clips": [
            {
                "id": "m1", "track": "music", "audioId": "music",
                "audioRole": "music", "start": 3, "duration": 12, "gainDb": -6,
            },
            {
                "id": "v1", "track": "vo", "audioId": "voice",
                "audioRole": "vo", "label": "VO Malo", "start": 5, "duration": 3,
            },
            {
                "id": "s1", "track": "sfx", "audioId": "click",
                "audioRole": "sfx", "start": 6, "duration": 1,
            },
        ]
    }
    p = ai.propose_ducking(
        timeline, "m1", reduction_db=8, attack_seconds=.25, release_seconds=.5
    )
    assert p["policy"]["automatic_apply"] is False
    assert [x["clip_id"] for x in p["blockers"]] == ["v1"]
    assert p["suggested_envelope"] == [
        {"time": 1.75, "gainDb": -6.0},
        {"time": 2.0, "gainDb": -14.0},
        {"time": 5.0, "gainDb": -14.0},
        {"time": 5.5, "gainDb": -6.0},
    ]


def test_crossfade_proposal_and_timeline_validation(tmp_path):
    root, rows = make_audio_project(tmp_path)
    a = rows["music_a.wav"]
    b = rows["music_b.wav"]
    timeline = {
        "edit_name": "mix",
        "duration_seconds": 30,
        "tracks": [{"id": "music", "name": "MUSIC", "kind": "music"}],
        "clips": [
            {
                "id": "a", "track": "music", "audioDbId": a["id"],
                "audioRole": "music", "start": 3, "duration": 5,
                "sourceStart": 0, "gainDb": -6,
            },
            {
                "id": "b", "track": "music", "audioDbId": b["id"],
                "audioRole": "music", "start": 8, "duration": 4,
                "sourceStart": 0, "gainDb": -6,
            },
        ],
    }
    clean = validate_timeline(root, timeline)
    p = ai.propose_crossfade(clean, "a", "b", duration_seconds=.5)
    assert p["right_start"] == 7.5
    assert p["policy"]["timing_change"] is True

    crossed = ai.apply_crossfade(clean, p)
    validated = validate_timeline(root, crossed)
    by_id = {x["id"]: x for x in validated["clips"]}
    assert by_id["a"]["crossfadeWith"] == "b"
    assert by_id["b"]["crossfadeWith"] == "a"
    assert by_id["a"]["fadeOut"] == .5
    assert by_id["b"]["fadeIn"] == .5

    broken = ai.apply_crossfade(clean, p)
    next(x for x in broken["clips"] if x["id"] == "b").pop("crossfadeWith")
    with pytest.raises(TimelineError, match="Collision"):
        validate_timeline(root, broken)
