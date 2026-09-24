from pathlib import Path
import subprocess

import pytest

import piste_studio.audio_tracks as at
import piste_studio.editorial_agent as ea
import piste_studio.master_critic as mc
import piste_studio.transcript_engine as te
from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.project import init_project
from piste_studio.timeline import load_timeline, save_timeline


def make_project(tmp_path: Path):
    root = tmp_path / "V026"
    init_project(root, "V0.26")
    for name in ("take_a.mp4", "take_b.mp4"):
        (root / "rushes" / name).write_bytes(name.encode())
    scan_media(root)
    rows = {
        Path(x["relative_path"]).name: x
        for x in fetch_media_with_metadata(root)
    }
    for row in rows.values():
        set_media_metadata(
            root,
            row["id"],
            title=Path(row["relative_path"]).stem,
            duration_seconds=20.0,
            rating=4,
        )
    save_timeline(
        root,
        {
            "edit_name": "agent_test",
            "duration_seconds": 30,
            "storyline": {"mode": "magnetic", "start": 0},
            "tracks": [
                {"id": "video", "name": "VIDEO", "kind": "video"},
                {"id": "vo", "name": "VO", "kind": "vo"},
            ],
            "clips": [],
        },
    )
    return root, rows


def install_tracks(root, media_id, monkeypatch):
    monkeypatch.setattr(
        at,
        "detect_audio_track_tools",
        lambda: at.AudioTrackTools(
            ffmpeg="/fake/ffmpeg",
            ffprobe="/fake/ffprobe",
        ),
    )
    monkeypatch.setattr(
        at,
        "probe_audio_streams",
        lambda path: [
            {
                "track_index": 0,
                "stream_index": 1,
                "codec": "aac",
                "channels": 2,
                "channel_layout": "stereo",
                "sample_rate": 48000,
                "language": None,
                "title": "System",
                "default": True,
                "forced": False,
            },
            {
                "track_index": 1,
                "stream_index": 2,
                "codec": "aac",
                "channels": 1,
                "channel_layout": "mono",
                "sample_rate": 48000,
                "language": "fra",
                "title": "Mic",
                "default": False,
                "forced": False,
            },
        ],
    )
    monkeypatch.setattr(
        at,
        "measure_audio_track",
        lambda path, track_index: {
            "mean_dbfs": -90.0 if track_index == 0 else -22.0,
            "peak_dbfs": -80.0 if track_index == 0 else -3.0,
            "silent": track_index == 0,
            "detected_silence_seconds": 8.0 if track_index == 0 else 1.2,
        },
    )
    return at.analyze_audio_tracks(root, media_id)


def transcript_payload(text_variant="base"):
    phrase = (
        "je voulais enregistrer tous les sons"
        if text_variant == "base"
        else "je voulais enregistrer absolument tous les sons"
    )
    words = [
        {"text": "euh", "type": "word", "start": 0.1, "end": 0.3, "speaker_id": "speaker_0"},
        {"text": "je", "type": "word", "start": 0.35, "end": 0.5, "speaker_id": "speaker_0"},
        {"text": "voulais", "type": "word", "start": 0.52, "end": 0.8, "speaker_id": "speaker_0"},
        {"text": "enregistrer", "type": "word", "start": 0.82, "end": 1.15, "speaker_id": "speaker_0"},
        {"text": "tous", "type": "word", "start": 1.18, "end": 1.35, "speaker_id": "speaker_0"},
        {"text": "les", "type": "word", "start": 1.37, "end": 1.5, "speaker_id": "speaker_0"},
        {"text": "sons", "type": "word", "start": 1.52, "end": 1.8, "speaker_id": "speaker_0"},
        {"text": "je", "type": "word", "start": 2.45, "end": 2.6, "speaker_id": "speaker_0"},
        {"text": "voulais", "type": "word", "start": 2.62, "end": 2.88, "speaker_id": "speaker_0"},
        {"text": "enregistrer", "type": "word", "start": 2.9, "end": 3.2, "speaker_id": "speaker_0"},
        {"text": "tous", "type": "word", "start": 3.22, "end": 3.38, "speaker_id": "speaker_0"},
        {"text": "les", "type": "word", "start": 3.4, "end": 3.52, "speaker_id": "speaker_0"},
        {"text": "sons", "type": "word", "start": 3.54, "end": 3.8, "speaker_id": "speaker_0"},
    ]
    if text_variant != "base":
        words.insert(
            10,
            {"text": "absolument", "type": "word", "start": 3.05, "end": 3.19, "speaker_id": "speaker_0"},
        )
    return {
        "language_code": "fr",
        "language_probability": 0.99,
        "text": f"euh {phrase}. {phrase}.",
        "words": words,
    }


def test_audio_track_intelligence_requires_explicit_non_silent_selection(
    tmp_path,
    monkeypatch,
):
    root, rows = make_project(tmp_path)
    media_id = rows["take_a.mp4"]["id"]
    result = install_tracks(root, media_id, monkeypatch)
    assert len(result["tracks"]) == 2
    assert result["recommended_track_index"] == 1
    with pytest.raises(
        at.AudioTrackIntelligenceError,
        match="silencieuse",
    ):
        at.select_audio_track(root, media_id, 0)
    selected = at.select_audio_track(root, media_id, 1)
    assert selected["selected_track_index"] == 1
    assert selected["policy"]["automatic_transcription"] is False


def test_transcript_import_builds_phrases_and_candidates(
    tmp_path,
    monkeypatch,
):
    root, rows = make_project(tmp_path)
    media_id = rows["take_a.mp4"]["id"]
    install_tracks(root, media_id, monkeypatch)
    at.select_audio_track(root, media_id, 1)

    transcript = te.import_transcript_payload(
        root,
        media_id,
        transcript_payload(),
        provider="test",
        model_id="fixture",
    )
    assert transcript["language_code"] == "fr"
    assert len(transcript["phrases"]) == 2
    assert transcript["phrases"][0]["start"] == 0.1
    assert transcript["phrases"][1]["start"] == 2.45

    candidates = ea.transcript_candidates(root, media_id)
    assert candidates["filler_candidates"][0]["text"] == "euh"
    assert candidates["silence_candidates"][0]["duration"] == pytest.approx(
        0.65,
        abs=0.01,
    )
    assert candidates["retake_candidates"]
    assert candidates["policy"]["automatic_cut"] is False


def test_take_comparator_and_ai_timeline_view(tmp_path, monkeypatch):
    root, rows = make_project(tmp_path)
    for index, name in enumerate(("take_a.mp4", "take_b.mp4")):
        media_id = rows[name]["id"]
        install_tracks(root, media_id, monkeypatch)
        at.select_audio_track(root, media_id, 1)
        te.import_transcript_payload(
            root,
            media_id,
            transcript_payload("base" if index == 0 else "alt"),
            provider="test",
            model_id="fixture",
        )

    comparison = ea.compare_takes(
        root,
        [rows["take_a.mp4"]["id"], rows["take_b.mp4"]["id"]],
        threshold=0.6,
    )
    assert comparison["matches"]
    assert comparison["policy"]["best_take_not_selected_automatically"]

    view = ea.build_ai_timeline_view(
        root,
        rows["take_a.mp4"]["id"],
    )
    assert view["transcript"]["phrases"]
    assert len(view["audio_tracks"]) == 2
    assert view["policy"]["storyline_unchanged"] is True


def test_proposed_edit_is_virtual_then_transactional_on_confirm(
    tmp_path,
    monkeypatch,
):
    root, rows = make_project(tmp_path)
    ids = []
    for name in ("take_a.mp4", "take_b.mp4"):
        media_id = rows[name]["id"]
        ids.append(media_id)
        install_tracks(root, media_id, monkeypatch)
        at.select_audio_track(root, media_id, 1)
        te.import_transcript_payload(
            root,
            media_id,
            transcript_payload(),
            provider="test",
            model_id="fixture",
        )

    before = load_timeline(root, "agent_test")
    proposal = ea.propose_edit(
        root,
        edit_name="agent_test",
        media_ids=ids,
        target_seconds=8,
        brief="Teaser test",
    )
    assert proposal["segments"]
    assert proposal["policy"]["storyline_unchanged"] is True
    assert load_timeline(root, "agent_test")["clips"] == before["clips"]

    with pytest.raises(
        ea.EditorialAgentError,
        match="Confirmation humaine",
    ):
        ea.apply_proposal(
            root,
            proposal["proposal_id"],
            confirm=False,
        )

    applied = ea.apply_proposal(
        root,
        proposal["proposal_id"],
        confirm=True,
    )
    assert applied["ok"] is True
    assert applied["proposal"]["status"] == "APPLIED"
    timeline = load_timeline(root, "agent_test")
    assert timeline["clips"]
    assert all(
        x["track"] == "video"
        for x in timeline["clips"]
    )
    assert timeline["storyline"]["mode"] == "magnetic"


def test_proposal_is_stale_if_storyline_changes(tmp_path, monkeypatch):
    root, rows = make_project(tmp_path)
    media_id = rows["take_a.mp4"]["id"]
    install_tracks(root, media_id, monkeypatch)
    at.select_audio_track(root, media_id, 1)
    te.import_transcript_payload(
        root,
        media_id,
        transcript_payload(),
        provider="test",
        model_id="fixture",
    )
    proposal = ea.propose_edit(
        root,
        edit_name="agent_test",
        media_ids=[media_id],
        target_seconds=5,
    )
    timeline = load_timeline(root, "agent_test")
    timeline["duration_seconds"] = 31
    save_timeline(root, timeline)
    with pytest.raises(ea.EditorialAgentError, match="a changé"):
        ea.apply_proposal(
            root,
            proposal["proposal_id"],
            confirm=True,
        )


def test_master_critic_persists_diagnostic_only_report(
    tmp_path,
    monkeypatch,
):
    root, _rows = make_project(tmp_path)
    render = root / "edits" / "agent_test" / "final.mp4"
    render.parent.mkdir(parents=True, exist_ok=True)
    render.write_bytes(b"fake")

    monkeypatch.setattr(
        mc,
        "_probe",
        lambda path: {
            "duration_seconds": 30.0,
            "width": 1920,
            "height": 1080,
            "video_codec": "h264",
            "pixel_format": "yuv420p",
            "audio_codec": "aac",
            "audio_channels": 2,
            "sample_rate": 48000,
            "has_video": True,
            "has_audio": True,
        },
    )
    monkeypatch.setattr(
        mc,
        "_black_frames",
        lambda path: [],
    )
    monkeypatch.setattr(
        mc,
        "measure_loudness",
        lambda path: {
            "integrated_lufs": -14.0,
            "true_peak_dbfs": -1.0,
            "loudness_range_lu": 5.0,
        },
    )

    report = mc.critique_render(
        root,
        edit_name="agent_test",
        source_path="edits/agent_test/final.mp4",
        version_label="V001",
    )
    assert report["status"] == "PASS"
    assert report["policy"]["automatic_edit"] is False
    stored = mc.list_master_critic_reports(
        root,
        edit_name="agent_test",
    )
    assert stored[0]["id"] == report["report_id"]
