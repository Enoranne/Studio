from pathlib import Path

import piste_studio.editorial_production_run as epr


def _patch_common(monkeypatch, root: Path):
    media = [{
        "id": 7,
        "kind": "video",
        "relative_path": "rushes/piste0_take.mp4",
        "status": "READY",
    }]
    (root / "rushes").mkdir(parents=True, exist_ok=True)
    (root / "rushes" / "piste0_take.mp4").write_bytes(b"rush")

    monkeypatch.setattr(epr, "fetch_media_with_metadata", lambda _root: media)
    monkeypatch.setattr(
        epr,
        "load_timeline",
        lambda _root, _name: {
            "edit_name": "teaser_30",
            "duration_seconds": 45,
            "storyline": {"mode": "magnetic", "start": 0},
            "clips": [{
                "id": "v1",
                "track": "video",
                "mediaDbId": 7,
                "start": 0,
                "duration": 4,
                "sourceStart": 0,
            }],
        },
    )
    monkeypatch.setattr(
        epr,
        "build_production_readiness",
        lambda *args, **kwargs: {
            "pipeline_status": "READY_FOR_AUTHORING",
            "capabilities": {
                "can_start_editing": True,
                "can_bootstrap": False,
                "can_author": True,
                "can_deliver": False,
            },
            "selection": {
                "edit_name": "teaser_30",
                "version": "V001",
            },
            "next_action": "Rendre la version avec Tesseract.",
        },
    )


def test_report_stops_at_human_validation(monkeypatch, tmp_path):
    root = tmp_path / "PISTE_0"
    root.mkdir()
    _patch_common(monkeypatch, root)

    monkeypatch.setattr(
        epr,
        "list_audio_tracks",
        lambda _root, _media_id: [{
            "track_index": 0,
            "silent": False,
            "selected_for_transcription": True,
        }],
    )
    monkeypatch.setattr(
        epr,
        "selected_audio_track",
        lambda _root, _media_id: {"track_index": 0, "silent": False},
    )
    monkeypatch.setattr(
        epr,
        "get_transcript",
        lambda _root, _media_id: {
            "id": 12,
            "phrases": [{
                "start": 0.2,
                "end": 1.3,
                "text": "Le magnétophone beige.",
            }],
        },
    )
    monkeypatch.setattr(
        epr,
        "transcript_candidates",
        lambda _root, _media_id: {
            "silence_candidates": [{"start": 1.3, "end": 1.8}],
            "filler_candidates": [],
            "retake_candidates": [],
        },
    )
    monkeypatch.setattr(
        epr,
        "list_proposals",
        lambda _root, edit_name=None: [
            {
                "id": 41,
                "edit_name": "teaser_30",
                "proposal_kind": "PROPOSED_EDIT",
                "status": "PENDING",
                "proposal": {},
            },
            {
                "id": 40,
                "edit_name": "teaser_30",
                "proposal_kind": "STRATEGY",
                "status": "PENDING",
                "proposal": {},
            },
        ],
    )
    monkeypatch.setattr(
        epr,
        "list_master_critic_reports",
        lambda _root, edit_name=None: [],
    )

    report = epr.build_editorial_production_run_report(
        root,
        edit_name="teaser_30",
        media_ids=[7],
    )

    assert report["status"] == "AWAITING_HUMAN_VALIDATION"
    assert report["proposal_summary"]["pending_proposal_id"] == 41
    stages = {x["id"]: x for x in report["stages"]}
    assert stages["rushes"]["status"] == "PASS"
    assert stages["audio_tracks"]["status"] == "PASS"
    assert stages["transcripts"]["status"] == "PASS"
    assert stages["candidates"]["counts"]["silence"] == 1
    assert stages["proposed_edit"]["status"] == "WAITING_HUMAN_VALIDATION"
    assert report["policy"]["no_storyline_mutation"] is True


def test_report_reaches_final_review_after_render_and_critic(
    monkeypatch,
    tmp_path,
):
    root = tmp_path / "PISTE_0"
    root.mkdir()
    _patch_common(monkeypatch, root)

    monkeypatch.setattr(
        epr,
        "list_audio_tracks",
        lambda _root, _media_id: [{
            "track_index": 0,
            "silent": False,
            "selected_for_transcription": True,
        }],
    )
    monkeypatch.setattr(
        epr,
        "selected_audio_track",
        lambda _root, _media_id: {"track_index": 0, "silent": False},
    )
    monkeypatch.setattr(
        epr,
        "get_transcript",
        lambda _root, _media_id: {
            "id": 12,
            "phrases": [{"start": 0, "end": 1, "text": "Malo écoute."}],
        },
    )
    monkeypatch.setattr(
        epr,
        "transcript_candidates",
        lambda *_args, **_kwargs: {
            "silence_candidates": [],
            "filler_candidates": [],
            "retake_candidates": [],
        },
    )
    monkeypatch.setattr(
        epr,
        "list_proposals",
        lambda _root, edit_name=None: [
            {
                "id": 51,
                "proposal_kind": "PROPOSED_EDIT",
                "status": "APPLIED",
                "proposal": {},
            },
            {
                "id": 50,
                "proposal_kind": "STRATEGY",
                "status": "PENDING",
                "proposal": {},
            },
        ],
    )
    monkeypatch.setattr(
        epr,
        "build_production_readiness",
        lambda *args, **kwargs: {
            "pipeline_status": "READY_FOR_DELIVERY",
            "capabilities": {
                "can_start_editing": True,
                "can_bootstrap": False,
                "can_author": True,
                "can_deliver": True,
            },
            "selection": {
                "edit_name": "teaser_30",
                "version": "V001",
            },
            "next_action": "Ouvrir Delivery Center.",
        },
    )
    monkeypatch.setattr(
        epr,
        "list_master_critic_reports",
        lambda _root, edit_name=None: [{
            "id": 9,
            "status": "PASS",
            "source_path": "edits/teaser_30/V001/master.mp4",
            "report": {"status": "PASS"},
        }],
    )

    report = epr.build_editorial_production_run_report(
        root,
        edit_name="teaser_30",
        media_ids=[7],
    )

    assert report["status"] == "AWAITING_FINAL_REVIEW"
    stages = {x["id"]: x for x in report["stages"]}
    assert stages["storyline"]["status"] == "PASS"
    assert stages["tesseract_render"]["status"] == "PASS"
    assert stages["master_critic"]["status"] == "PASS"
    assert report["policy"]["never_auto_pass_human_review"] is True


def test_save_report(monkeypatch, tmp_path):
    root = tmp_path / "PISTE_0"
    root.mkdir()
    _patch_common(monkeypatch, root)
    monkeypatch.setattr(epr, "list_audio_tracks", lambda *_args: [])
    monkeypatch.setattr(epr, "selected_audio_track", lambda *_args: None)
    monkeypatch.setattr(epr, "get_transcript", lambda *_args: None)
    monkeypatch.setattr(epr, "list_proposals", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        epr,
        "list_master_critic_reports",
        lambda *_args, **_kwargs: [],
    )

    path = epr.save_editorial_production_run_report(
        root,
        edit_name="teaser_30",
        media_ids=[7],
    )
    assert path.is_file()
    assert path.parent == root / "reports" / "production"
    assert "editorial-v026-production-run" in path.name
