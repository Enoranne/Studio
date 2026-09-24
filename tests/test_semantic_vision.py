from pathlib import Path
import json
import shutil
import subprocess

import pytest

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


def test_targeted_reference_is_independent_from_global_media_tags(tmp_path, monkeypatch):
    root, rows = make_project(tmp_path)
    source = rows["other.mp4"]
    target = rows["target.mp4"]
    frame = root / "cache" / "vision" / "references" / "targeted.jpg"
    frame.parent.mkdir(parents=True, exist_ok=True)
    frame.write_bytes(b"fake-jpeg")

    monkeypatch.setattr(
        sv,
        "extract_targeted_reference_frame",
        lambda root, media_id, timestamp_seconds, roi=None, width=448, force=False: (
            frame,
            float(timestamp_seconds),
            sv.normalize_reference_roi(roi),
        ),
    )
    reference = sv.create_targeted_semantic_reference(
        root,
        source["id"],
        tag="prop:fisher",
        timestamp_seconds=3.4,
        roi={"x": 0.2, "y": 0.25, "width": 0.5, "height": 0.4},
        provider=FakeVisionProvider(),
    )
    assert reference["tag"] == "prop:fisher"
    assert reference["facet"] == "prop"
    assert reference["media_id"] == source["id"]
    assert reference["roi"]["x"] == 0.2
    assert "prop:fisher" not in source["tags"]

    sv.store_semantic_profile(
        root,
        target["id"],
        embedding=[0.99, 0.02, 0.0],
        provider="fake_clip",
        model_id="fake/model",
    )
    result = sv.propose_semantic_tags(
        root,
        target["id"],
        provider="fake_clip",
        model_id="fake/model",
    )
    pending = {
        row["tag"]: row
        for row in result["proposals"]
        if row["status"] == "PENDING"
    }
    assert "prop:fisher" in pending
    evidence = pending["prop:fisher"]["evidence"]
    assert evidence["targeted_reference_count"] == 1
    assert evidence["legacy_reference_count"] == 0
    assert evidence["targeted_reference_ids"] == [reference["id"]]
    assert evidence["best_targeted_reference_id"] == reference["id"]
    assert evidence["method"] == "targeted_reference_centroid"


def test_targeted_reference_on_target_media_does_not_self_propose(tmp_path):
    root, rows = make_project(tmp_path)
    target = rows["target.mp4"]
    sv.store_semantic_profile(
        root,
        target["id"],
        embedding=[1.0, 0.0, 0.0],
        provider="fake_clip",
        model_id="fake/model",
    )
    sv.store_targeted_semantic_reference(
        root,
        target["id"],
        tag="character:malo",
        timestamp_seconds=1.0,
        roi={"x": 0, "y": 0, "width": 1, "height": 1},
        embedding=[1.0, 0.0, 0.0],
        provider="fake_clip",
        model_id="fake/model",
    )
    result = sv.propose_semantic_tags(
        root,
        target["id"],
        provider="fake_clip",
        model_id="fake/model",
    )
    pending = [x for x in result["proposals"] if x["status"] == "PENDING"]
    assert all(x["tag"] != "character:malo" for x in pending)


def test_targeted_reference_crud_and_roi_clamping(tmp_path):
    root, rows = make_project(tmp_path)
    source = rows["other.mp4"]
    ref = sv.store_targeted_semantic_reference(
        root,
        source["id"],
        tag="look:warm",
        timestamp_seconds=2.0,
        roi={"x": 0.98, "y": 0.99, "width": 0.8, "height": 0.7},
        embedding=[1.0, 0.0, 0.0],
        provider="fake_clip",
        model_id="fake/model",
    )
    assert ref["roi"]["x"] == 0.95
    assert ref["roi"]["y"] == 0.95
    assert ref["roi"]["width"] == 0.05
    assert ref["roi"]["height"] == 0.05
    duplicate = sv.store_targeted_semantic_reference(
        root,
        source["id"],
        tag="look:warm",
        timestamp_seconds=2.0,
        roi={"x": 0.98, "y": 0.99, "width": 0.8, "height": 0.7},
        embedding=[0.99, 0.01, 0.0],
        provider="fake_clip",
        model_id="fake/model",
    )
    assert duplicate["id"] == ref["id"]

    listed = sv.list_targeted_semantic_references(
        root,
        media_id=source["id"],
        provider="fake_clip",
        model_id="fake/model",
    )
    assert [x["id"] for x in listed] == [ref["id"]]
    assert sv.delete_targeted_semantic_reference(root, ref["id"]) is True
    assert sv.get_targeted_semantic_reference(root, ref["id"]) is None


def test_real_ffmpeg_extracts_targeted_roi_frame(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("ffmpeg/ffprobe système requis")

    root = tmp_path / "TargetedROI"
    init_project(root, "Targeted ROI")
    video = root / "rushes" / "test.mp4"
    proc = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-f", "lavfi",
            "-i", "testsrc=size=320x180:rate=24:duration=2",
            "-c:v", "mpeg4",
            "-q:v", "2",
            str(video),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    scan_media(root)
    row = next(x for x in fetch_media_with_metadata(root) if x["kind"] == "video")
    set_media_metadata(root, row["id"], title="Test", duration_seconds=2.0)

    frame, timestamp, roi = sv.extract_targeted_reference_frame(
        root,
        row["id"],
        timestamp_seconds=1.0,
        roi={"x": 0.25, "y": 0.2, "width": 0.5, "height": 0.5},
        width=320,
    )
    assert frame.exists()
    assert timestamp == 1.0
    assert roi == {"x": 0.25, "y": 0.2, "width": 0.5, "height": 0.5}

    probe = subprocess.run(
        [
            ffprobe,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "json",
            str(frame),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert probe.returncode == 0, probe.stderr
    data = json.loads(probe.stdout)
    assert data["streams"][0]["width"] == 320
    assert data["streams"][0]["height"] > 0
