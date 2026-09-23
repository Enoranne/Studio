from pathlib import Path

import piste_studio.semantic_vision as sv
from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.project import init_project


class FakeVisionProvider:
    provider = "fake_clip"
    model_id = "fake/model"

    def embed_images(self, image_paths, *, allow_model_download=False):
        assert image_paths
        return [1.0, 0.0, 0.0]


def make_project(tmp_path: Path):
    root = tmp_path / "Semantic"
    init_project(root, "Semantic Vision")
    for name in ("ref_malo.mp4", "target.mp4", "other.mp4"):
        (root / "rushes" / name).write_bytes(name.encode())
    scan_media(root)
    rows = fetch_media_with_metadata(root)
    by_name = {Path(x["relative_path"]).name: x for x in rows}
    set_media_metadata(
        root,
        by_name["ref_malo.mp4"]["id"],
        title="Référence Malo",
        duration_seconds=8,
        tags=["character:malo", "prop:fisher", "decor:salon"],
    )
    set_media_metadata(
        root,
        by_name["target.mp4"]["id"],
        title="Candidat",
        duration_seconds=8,
        tags=["enfance"],
    )
    set_media_metadata(
        root,
        by_name["other.mp4"]["id"],
        title="Autre",
        duration_seconds=8,
        tags=["character:ronan", "decor:cuisine"],
    )
    return root, {
        Path(x["relative_path"]).name: x
        for x in fetch_media_with_metadata(root)
    }


def test_cosine_similarity_is_normalized():
    assert sv.cosine_similarity([2, 0], [10, 0]) == 1.0
    assert abs(sv.cosine_similarity([1, 0], [0, 1])) < 1e-9


def test_semantic_profile_can_be_created_with_fake_provider(tmp_path, monkeypatch):
    root, rows = make_project(tmp_path)
    target = rows["target.mp4"]
    frame = root / "cache" / "vision" / "fake.jpg"
    frame.parent.mkdir(parents=True, exist_ok=True)
    frame.write_bytes(b"fake-jpeg")
    monkeypatch.setattr(
        sv,
        "extract_reference_frames",
        lambda root, media_id, force=False: [frame],
    )

    profile = sv.analyze_semantic_media(
        root,
        target["id"],
        provider=FakeVisionProvider(),
    )
    assert profile["status"] == "READY"
    assert profile["provider"] == "fake_clip"
    assert profile["model_id"] == "fake/model"
    assert profile["frame_count"] == 1
    assert profile["embedding"] == [1.0, 0.0, 0.0]


def test_reference_based_proposals_require_human_resolution(tmp_path):
    root, rows = make_project(tmp_path)
    ref = rows["ref_malo.mp4"]
    target = rows["target.mp4"]
    other = rows["other.mp4"]

    sv.store_semantic_profile(
        root,
        ref["id"],
        embedding=[1.0, 0.0, 0.0],
    )
    sv.store_semantic_profile(
        root,
        target["id"],
        embedding=[0.99, 0.03, 0.0],
    )
    sv.store_semantic_profile(
        root,
        other["id"],
        embedding=[0.0, 1.0, 0.0],
    )

    result = sv.propose_semantic_tags(root, target["id"])
    assert result["policy"]["human_validation_required"] is True
    assert result["policy"]["automatic_tag_write"] is False
    assert result["policy"]["automatic_storyline_change"] is False

    pending = {
        row["tag"]: row
        for row in result["proposals"]
        if row["status"] == "PENDING"
    }
    assert "character:malo" in pending
    assert "prop:fisher" in pending
    assert "decor:salon" in pending
    assert "character:ronan" not in pending
    assert pending["character:malo"]["confidence"] > 0.98
    assert pending["character:malo"]["evidence"]["reference_media_ids"] == [
        ref["id"]
    ]

    accepted = sv.resolve_semantic_proposal(
        root,
        pending["character:malo"]["id"],
        accept=True,
    )
    assert accepted["status"] == "ACCEPTED"
    target_after = next(
        x for x in fetch_media_with_metadata(root)
        if int(x["id"]) == int(target["id"])
    )
    assert "character:malo" in target_after["tags"]

    rejected = sv.resolve_semantic_proposal(
        root,
        pending["prop:fisher"]["id"],
        accept=False,
    )
    assert rejected["status"] == "REJECTED"

    rerun = sv.propose_semantic_tags(root, target["id"])
    statuses = {x["tag"]: x["status"] for x in rerun["proposals"]}
    assert statuses["prop:fisher"] == "REJECTED"

    reset = sv.propose_semantic_tags(
        root,
        target["id"],
        reset_rejected=True,
    )
    statuses = {x["tag"]: x["status"] for x in reset["proposals"]}
    assert statuses["prop:fisher"] == "PENDING"


def test_status_is_safe_without_optional_dependencies(monkeypatch):
    monkeypatch.setattr(
        sv,
        "_dependency_status",
        lambda: (False, "Dépendances vision manquantes : torch"),
    )
    monkeypatch.setattr(sv.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    status = sv.detect_semantic_vision()
    assert status.ready is False
    assert status.dependencies_ready is False
    assert status.model_cached is None
