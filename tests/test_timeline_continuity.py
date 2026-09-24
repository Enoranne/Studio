from pathlib import Path
import json

from piste_studio.config import read_yaml, write_yaml
from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.project import init_project
from piste_studio.timeline import load_timeline, save_timeline
from piste_studio.timeline_continuity import analyze_timeline_continuity


def make_project(tmp_path: Path):
    root = tmp_path / "TimelineContinuity"
    init_project(root, "Timeline Continuity")
    for name in ("prev.mp4", "target.mp4", "next.mp4", "candidate.mp4", "blank.mp4"):
        (root / "rushes" / name).write_bytes(name.encode("utf-8"))
    scan_media(root)
    rows = {
        Path(row["relative_path"]).name: row
        for row in fetch_media_with_metadata(root)
        if row["kind"] == "video"
    }
    tags = {
        "prev.mp4": [
            "character:malo", "prop:fisher", "decor:salon", "look:warm"
        ],
        "target.mp4": [
            "character:malo", "prop:fisher", "decor:salon", "look:warm"
        ],
        "next.mp4": [
            "character:malo", "prop:fisher", "decor:salon", "look:warm"
        ],
        "candidate.mp4": [
            "character:ronan", "prop:radio", "decor:cuisine", "look:cold"
        ],
        "blank.mp4": [],
    }
    for name, row in rows.items():
        set_media_metadata(
            root,
            row["id"],
            title=name.replace(".mp4", "").title(),
            duration_seconds=8.0,
            tags=tags[name],
        )
    save_timeline(
        root,
        {
            "edit_name": "teaser_30",
            "duration_seconds": 20,
            "storyline": {"mode": "free", "start": 0},
            "tracks": [{"id": "video", "name": "VIDEO", "kind": "video"}],
            "clips": [
                {
                    "id": "v-prev",
                    "track": "video",
                    "start": 0,
                    "duration": 4,
                    "sourceStart": 0,
                    "mediaDbId": rows["prev.mp4"]["id"],
                },
                {
                    "id": "v-target",
                    "track": "video",
                    "start": 4,
                    "duration": 4,
                    "sourceStart": 0,
                    "mediaDbId": rows["target.mp4"]["id"],
                },
                {
                    "id": "v-next",
                    "track": "video",
                    "start": 8,
                    "duration": 4,
                    "sourceStart": 0,
                    "mediaDbId": rows["next.mp4"]["id"],
                },
            ],
        },
    )
    return root, rows


def test_mounted_clip_preserves_neighbor_continuity(tmp_path):
    root, _rows = make_project(tmp_path)
    result = analyze_timeline_continuity(
        root,
        edit_name="teaser_30",
        clip_id="v-target",
    )
    assert result["mode"] == "MOUNTED"
    assert result["status"] == "CONTINUOUS"
    assert result["summary"]["neighbor_count"] == 2
    assert result["summary"]["warning_count"] == 0
    bridge = [
        x for x in result["findings"]
        if x["kind"] == "BRIDGE_CONTINUITY"
    ]
    assert {x["facet"] for x in bridge} == {
        "character", "prop", "decor", "look"
    }


def test_candidate_simulation_reports_explicit_neighbor_ruptures_without_mutation(tmp_path):
    root, rows = make_project(tmp_path)
    before = json.dumps(load_timeline(root, "teaser_30"), sort_keys=True)
    result = analyze_timeline_continuity(
        root,
        edit_name="teaser_30",
        clip_id="v-target",
        candidate_media_id=rows["candidate.mp4"]["id"],
    )
    after = json.dumps(load_timeline(root, "teaser_30"), sort_keys=True)

    assert result["mode"] == "CANDIDATE"
    assert result["status"] == "RUPTURE"
    assert result["target"]["media_id"] == rows["candidate.mp4"]["id"]
    assert result["target"]["original_media_id"] == rows["target.mp4"]["id"]
    assert result["summary"]["warning_count"] >= 8
    assert any(
        x["kind"] == "FACET_RUPTURE"
        and x["facet"] == "character"
        and x["side"] == "PRÉCÉDENT"
        for x in result["findings"]
    )
    assert any(
        x["kind"] == "BRIDGE_EVIDENCE_GAP"
        and x["facet"] == "prop"
        for x in result["findings"]
    )
    assert before == after
    assert result["policy"]["automatic_edit"] is False
    assert result["policy"]["automatic_candidate_rejection"] is False


def test_missing_candidate_tags_are_missing_evidence_not_claimed_visual_absence(tmp_path):
    root, rows = make_project(tmp_path)
    result = analyze_timeline_continuity(
        root,
        clip_id="v-target",
        candidate_media_id=rows["blank.mp4"]["id"],
    )
    assert result["status"] == "RUPTURE"
    assert result["policy"]["absence_of_tag_is_not_visual_proof_of_absence"] is True
    assert any(
        x["kind"] == "TARGET_EVIDENCE_MISSING"
        for x in result["findings"]
    )
    gaps = [x for x in result["findings"] if x["kind"] == "BRIDGE_EVIDENCE_GAP"]
    assert len(gaps) == 4
    assert all("preuve" in x["message"] for x in gaps)


def test_edge_clip_uses_only_existing_neighbor(tmp_path):
    root, _rows = make_project(tmp_path)
    result = analyze_timeline_continuity(
        root,
        clip_id="v-prev",
    )
    assert result["previous"] is None
    assert result["next"]["clip_id"] == "v-target"
    assert result["summary"]["neighbor_count"] == 1
    assert result["status"] == "CONTINUOUS"


def test_candidate_canon_assessments_are_exposed(tmp_path):
    root, rows = make_project(tmp_path)
    canon = read_yaml(root / "canon.yaml")
    canon["semantic"] = {
        "allowed_tags": ["character:malo"],
        "forbidden_tags": ["character:ronan"],
        "closed_facets": [],
    }
    write_yaml(root / "canon.yaml", canon)

    result = analyze_timeline_continuity(
        root,
        clip_id="v-target",
        candidate_media_id=rows["candidate.mp4"]["id"],
    )
    assessments = {x["tag"]: x for x in result["canon_assessments"]}
    assert assessments["character:ronan"]["status"] == "CONFLICT"
    assert assessments["character:ronan"]["requires_explicit_acknowledgement"] is True
