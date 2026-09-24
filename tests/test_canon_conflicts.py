from pathlib import Path

from piste_studio.canon_conflicts import (
    assess_semantic_tag_against_canon,
    canonical_semantic_index,
    normalize_semantic_tag,
)
from piste_studio.config import read_yaml, write_yaml
from piste_studio.locks import add_lock
from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.project import init_project
from piste_studio.timeline import save_timeline


def make_project(tmp_path: Path):
    root = tmp_path / "CanonConflict"
    init_project(root, "Canon Conflict")
    (root / "rushes" / "shot.mp4").write_bytes(b"shot")
    scan_media(root)
    row = next(x for x in fetch_media_with_metadata(root) if x["kind"] == "video")
    set_media_metadata(root, row["id"], title="Shot", duration_seconds=8.0)
    return root, row


def test_normalize_semantic_tag_is_stable():
    assert normalize_semantic_tag(" Look : Warm_Tungsten ") == (
        "look",
        "warm-tungsten",
        "look:warm-tungsten",
    )
    assert normalize_semantic_tag("character:Mâlo")[2] == "character:malo"


def test_canon_index_uses_entities_look_and_explicit_rules(tmp_path):
    root, _row = make_project(tmp_path)
    canon = read_yaml(root / "canon.yaml")
    canon["characters"] = {"Malo": {"age": 6}}
    canon["props"] = {"Fisher": {}}
    canon["decors"] = {"Salon cheminée": {}}
    canon["visual"]["look"] = ["Warm Tungsten"]
    canon["visual"]["avoid"] = ["Modern Glossy", "prop:smartphone"]
    canon["semantic"] = {
        "allowed_tags": ["look:kodak-500t"],
        "forbidden_tags": ["decor:spaceship"],
        "closed_facets": ["character"],
    }
    write_yaml(root / "canon.yaml", canon)

    index = canonical_semantic_index(canon)
    assert "character:malo" in index["allowed_tags"]
    assert "prop:fisher" in index["allowed_tags"]
    assert "decor:salon-cheminee" in index["allowed_tags"]
    assert "look:warm-tungsten" in index["allowed_tags"]
    assert "look:kodak-500t" in index["allowed_tags"]
    assert "look:modern-glossy" in index["forbidden_tags"]
    assert "prop:smartphone" in index["forbidden_tags"]
    assert "decor:spaceship" in index["forbidden_tags"]
    assert index["closed_facets"] == ["character"]


def test_canon_assessment_distinguishes_alignment_conflict_and_unknown(tmp_path):
    root, row = make_project(tmp_path)
    canon = read_yaml(root / "canon.yaml")
    canon["characters"] = {"Malo": {}}
    canon["props"] = {"Fisher": {}}
    canon["visual"]["avoid"] = ["Modern Glossy"]
    canon["semantic"] = {
        "allowed_tags": [],
        "forbidden_tags": ["prop:smartphone"],
        "closed_facets": ["character"],
    }
    write_yaml(root / "canon.yaml", canon)

    aligned = assess_semantic_tag_against_canon(
        root, media_id=row["id"], tag="character:malo"
    )
    assert aligned["status"] == "ALIGNED"
    assert aligned["requires_explicit_acknowledgement"] is False

    forbidden = assess_semantic_tag_against_canon(
        root, media_id=row["id"], tag="prop:smartphone"
    )
    assert forbidden["status"] == "CONFLICT"
    assert forbidden["requires_explicit_acknowledgement"] is True

    avoided = assess_semantic_tag_against_canon(
        root, media_id=row["id"], tag="look:modern-glossy"
    )
    assert avoided["status"] == "CONFLICT"

    closed = assess_semantic_tag_against_canon(
        root, media_id=row["id"], tag="character:jasper"
    )
    assert closed["status"] == "CONFLICT"
    assert closed["findings"][0]["allowed_for_facet"] == ["character:malo"]

    unknown = assess_semantic_tag_against_canon(
        root, media_id=row["id"], tag="decor:cuisine"
    )
    assert unknown["status"] == "UNVERIFIED"
    assert unknown["policy"]["absence_is_not_conflict"] is True
    assert unknown["requires_explicit_acknowledgement"] is False


def test_hard_lock_context_requires_ack_only_when_semantic_operation_applies(tmp_path):
    root, row = make_project(tmp_path)
    save_timeline(
        root,
        {
            "edit_name": "teaser_30",
            "duration_seconds": 12,
            "tracks": [{"id": "video", "kind": "video"}],
            "clips": [{
                "id": "v1",
                "track": "video",
                "mediaDbId": row["id"],
                "start": 2,
                "duration": 4,
                "sourceStart": 0,
            }],
        },
    )
    add_lock(
        root,
        "Image verrouillée",
        0,
        7,
        "HARD",
        ["semantic_tag_accept"],
    )
    result = assess_semantic_tag_against_canon(
        root,
        media_id=row["id"],
        tag="prop:fisher",
        edit_name="teaser_30",
    )
    assert result["status"] == "HARD_LOCK"
    assert result["requires_explicit_acknowledgement"] is True
    hard = next(x for x in result["findings"] if x["kind"] == "HARD_LOCK")
    assert hard["clip_id"] == "v1"

    other_root = tmp_path / "TrimOnly"
    init_project(other_root, "Trim Only")
    (other_root / "rushes" / "shot.mp4").write_bytes(b"shot")
    scan_media(other_root)
    other = next(
        x for x in fetch_media_with_metadata(other_root)
        if x["kind"] == "video"
    )
    set_media_metadata(other_root, other["id"], duration_seconds=8)
    save_timeline(
        other_root,
        {
            "edit_name": "teaser_30",
            "duration_seconds": 12,
            "tracks": [{"id": "video", "kind": "video"}],
            "clips": [{
                "id": "v1",
                "track": "video",
                "mediaDbId": other["id"],
                "start": 2,
                "duration": 4,
                "sourceStart": 0,
            }],
        },
    )
    add_lock(other_root, "Trim only", 0, 7, "HARD", ["trim"])
    result = assess_semantic_tag_against_canon(
        other_root,
        media_id=other["id"],
        tag="prop:fisher",
    )
    assert result["status"] == "UNVERIFIED"
    assert all(x["kind"] != "HARD_LOCK" for x in result["findings"])


def test_soft_semantic_lock_is_review_not_blocking(tmp_path):
    root, row = make_project(tmp_path)
    save_timeline(
        root,
        {
            "edit_name": "teaser_30",
            "duration_seconds": 10,
            "tracks": [{"id": "video", "kind": "video"}],
            "clips": [{
                "id": "v1",
                "track": "video",
                "mediaDbId": row["id"],
                "start": 1,
                "duration": 3,
                "sourceStart": 0,
            }],
        },
    )
    add_lock(root, "À confirmer", 0, 5, "SOFT", ["semantic"])
    result = assess_semantic_tag_against_canon(
        root,
        media_id=row["id"],
        tag="prop:fisher",
    )
    assert result["status"] == "REVIEW"
    assert result["requires_explicit_acknowledgement"] is False
    assert any(x["kind"] == "SOFT_LOCK" for x in result["findings"])
