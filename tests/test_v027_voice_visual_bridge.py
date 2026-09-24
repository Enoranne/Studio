from pathlib import Path

import pytest

import piste_studio.voice_visual_bridge as vv
from piste_studio.editorial_agent import apply_proposal
from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.project import init_project
from piste_studio.timeline import load_timeline, save_timeline
from piste_studio.transcript_engine import import_transcript_payload


def make_project(tmp_path: Path):
    root = tmp_path / "VOICE_VISUAL"
    init_project(root, "Voice Visual")
    (root / "audio" / "vo.wav").write_bytes(b"voice")
    (root / "rushes" / "fisher.mp4").write_bytes(b"fisher")
    (root / "rushes" / "tree.mp4").write_bytes(b"tree")
    scan_media(root)
    rows = {
        Path(x["relative_path"]).name: x
        for x in fetch_media_with_metadata(root)
    }
    set_media_metadata(
        root,
        rows["vo.wav"]["id"],
        title="VO Malo",
        duration_seconds=12.0,
    )
    set_media_metadata(
        root,
        rows["fisher.mp4"]["id"],
        title="Malo et le magnétophone Fisher",
        description="Malo découvre le magnétophone beige dans le salon",
        duration_seconds=12.0,
        rating=5,
        tags=["character:malo", "prop:magnétophone", "decor:salon"],
    )
    set_media_metadata(
        root,
        rows["tree.mp4"]["id"],
        title="Arbre du jardin",
        description="Branches et vent dans le jardin",
        duration_seconds=12.0,
        rating=3,
        tags=["decor:jardin", "prop:arbre"],
    )
    # Audio-track analysis is intentionally bypassed for transcript import.
    monkey = {
        "language_code": "fr",
        "text": "Je voulais enregistrer le magnétophone. Le vent dans les arbres.",
        "words": [
            {"text": "Je", "type": "word", "start": 0.0, "end": 0.2, "speaker_id": "Malo"},
            {"text": "voulais", "type": "word", "start": 0.2, "end": 0.5, "speaker_id": "Malo"},
            {"text": "enregistrer", "type": "word", "start": 0.5, "end": 0.9, "speaker_id": "Malo"},
            {"text": "le", "type": "word", "start": 0.9, "end": 1.0, "speaker_id": "Malo"},
            {"text": "magnétophone.", "type": "word", "start": 1.0, "end": 2.0, "speaker_id": "Malo"},
            {"text": "Le", "type": "word", "start": 2.5, "end": 2.7, "speaker_id": "Malo"},
            {"text": "vent", "type": "word", "start": 2.7, "end": 3.0, "speaker_id": "Malo"},
            {"text": "dans", "type": "word", "start": 3.0, "end": 3.2, "speaker_id": "Malo"},
            {"text": "les", "type": "word", "start": 3.2, "end": 3.3, "speaker_id": "Malo"},
            {"text": "arbres.", "type": "word", "start": 3.3, "end": 4.3, "speaker_id": "Malo"},
        ],
    }
    return root, rows, monkey


def install_transcript(root, rows, payload, monkeypatch):
    monkeypatch.setattr(
        "piste_studio.transcript_engine._resolve_track_index",
        lambda *_args, **_kwargs: 0,
    )
    monkeypatch.setattr(
        "piste_studio.transcript_engine._track_info",
        lambda *_args, **_kwargs: {"track_index": 0, "silent": False},
    )
    return import_transcript_payload(
        root,
        rows["vo.wav"]["id"],
        payload,
        track_index=0,
        provider="test",
        model_id="fixture",
    )


def fake_windows(root, media_id, **kwargs):
    return {
        "media_id": media_id,
        "candidates": [
            {
                "source_in": 0.0,
                "source_out": 6.0,
                "duration": 6.0,
                "reason": "Plan continu de test.",
            },
            {
                "source_in": 6.0,
                "source_out": 12.0,
                "duration": 6.0,
                "reason": "Deuxième fenêtre.",
            },
        ],
    }


def test_voice_phrase_ranks_matching_visual_metadata(tmp_path, monkeypatch):
    root, rows, payload = make_project(tmp_path)
    install_transcript(root, rows, payload, monkeypatch)
    monkeypatch.setattr(vv, "suggest_editorial_windows", fake_windows)
    monkeypatch.setattr(
        vv,
        "_embed_intents",
        lambda texts, allow_model_download=False: (None, "model unavailable"),
    )

    mapping = vv.voice_visual_candidates(
        root,
        voice_media_id=rows["vo.wav"]["id"],
        phrase_indexes=[0],
        per_phrase=4,
    )

    assert mapping["phrases"][0]["candidates"]
    assert (
        mapping["phrases"][0]["candidates"][0]["media_id"]
        == rows["fisher.mp4"]["id"]
    )
    assert mapping["semantic_text"]["available"] is False
    assert mapping["policy"]["no_automatic_storyline_change"] is True


def test_reject_window_is_removed_from_candidates(tmp_path, monkeypatch):
    root, rows, payload = make_project(tmp_path)
    install_transcript(root, rows, payload, monkeypatch)
    monkeypatch.setattr(vv, "suggest_editorial_windows", fake_windows)
    monkeypatch.setattr(
        vv,
        "_embed_intents",
        lambda texts, allow_model_download=False: (None, None),
    )
    monkeypatch.setattr(
        vv,
        "list_editorial_ranges",
        lambda _root: [{
            "media_id": rows["fisher.mp4"]["id"],
            "kind": "reject",
            "source_in": 0.0,
            "source_out": 6.0,
        }],
    )

    mapping = vv.voice_visual_candidates(
        root,
        voice_media_id=rows["vo.wav"]["id"],
        phrase_indexes=[0],
        per_phrase=10,
    )
    fisher = [
        x for x in mapping["phrases"][0]["candidates"]
        if x["media_id"] == rows["fisher.mp4"]["id"]
    ]
    assert all(x["source_in"] >= 6.0 for x in fisher)


def test_voice_visual_proposal_stays_virtual_then_applies(tmp_path, monkeypatch):
    root, rows, payload = make_project(tmp_path)
    install_transcript(root, rows, payload, monkeypatch)
    monkeypatch.setattr(vv, "suggest_editorial_windows", fake_windows)
    monkeypatch.setattr(
        vv,
        "_embed_intents",
        lambda texts, allow_model_download=False: (None, None),
    )

    save_timeline(
        root,
        {
            "edit_name": "teaser_30",
            "duration_seconds": 20,
            "storyline": {"mode": "magnetic", "start": 0},
            "tracks": [
                {"id": "video", "name": "VIDEO", "kind": "video"},
                {"id": "vo", "name": "VO", "kind": "vo"},
            ],
            "clips": [{
                "id": "vo-main",
                "track": "vo",
                "audioDbId": rows["vo.wav"]["id"],
                "audioId": "vo-source",
                "start": 0.0,
                "duration": 8.0,
                "sourceStart": 0.0,
                "gainDb": 0.0,
                "pan": 0.0,
                "fadeIn": 0.0,
                "fadeOut": 0.0,
                "audioRole": "vo",
                "volumeEnvelope": [],
            }],
        },
    )
    before = load_timeline(root, "teaser_30")

    proposal = vv.propose_voice_visual_edit(
        root,
        edit_name="teaser_30",
        voice_media_id=rows["vo.wav"]["id"],
        per_phrase=6,
        max_shot_seconds=3.0,
    )

    assert proposal["mode"] == "VOICE_VISUAL"
    assert proposal["policy"]["storyline_unchanged"] is True
    assert proposal["mapping_mode"] == "existing_voice_clip"
    assert load_timeline(root, "teaser_30")["clips"] == before["clips"]
    candidate = proposal["candidate_timeline"]
    assert any(x["track"] == "video" for x in candidate["clips"])
    assert any(x["id"] == "vo-main" for x in candidate["clips"])

    applied = apply_proposal(
        root,
        proposal["proposal_id"],
        confirm=True,
    )
    assert applied["ok"] is True
    timeline = load_timeline(root, "teaser_30")
    assert any(x["track"] == "video" for x in timeline["clips"])
    assert any(x["id"] == "vo-main" for x in timeline["clips"])


def test_compare_visual_candidates_does_not_pick_winner():
    mapping = {
        "phrases": [{
            "phrase_index": 2,
            "text": "Le vent.",
            "candidates": [
                {
                    "media_id": 1,
                    "source_in": 0,
                    "source_out": 2,
                    "score": 0.8,
                    "tags": ["decor:jardin"],
                },
                {
                    "media_id": 2,
                    "source_in": 3,
                    "source_out": 5,
                    "score": 0.75,
                    "tags": ["decor:jardin", "prop:arbre"],
                },
            ],
        }],
    }
    result = vv.compare_visual_candidates(
        mapping,
        phrase_index=2,
    )
    assert len(result["candidates"]) == 2
    assert result["policy"]["best_shot_not_selected_automatically"] is True
