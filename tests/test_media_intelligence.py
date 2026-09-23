from pathlib import Path

import piste_studio.media_intelligence as mi
from piste_studio.db import connect
from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.project import init_project


def make_project(tmp_path: Path) -> tuple[Path, list[dict]]:
    root = tmp_path / "MediaIntel"
    init_project(root, "Media Intel")
    for name in ("malo_take_a.mp4", "malo_take_b.mp4", "ronan_rire.mp4"):
        (root / "rushes" / name).write_bytes(name.encode())
    scan_media(root)
    rows = fetch_media_with_metadata(root)
    for row in rows:
        set_media_metadata(
            root,
            row["id"],
            title=Path(row["relative_path"]).stem,
            duration_seconds=10.0,
            rating=3,
            tags=["test"],
        )
    return root, fetch_media_with_metadata(root)


def test_filename_tokens_and_signature_similarity():
    assert mi.filename_tokens("rushes/Malo_Take_03_Fisher.mp4") == [
        "fisher",
        "malo",
    ]
    same = ["ffffffffffffffffffffffffffffffffffff"] * 3
    near = ["ffffffffffffffffffffffffffffffffffff"] * 2 + [
        "fffffffffffffffffffffffffffffffffffe"
    ]
    different = ["000000000000000000000000000000000000"] * 3
    assert mi.signature_similarity(same, same) == 1.0
    assert mi.signature_similarity(same, near) > 0.99
    assert mi.signature_similarity(same, different) < 0.05


def test_analysis_persists_without_real_ffmpeg(tmp_path, monkeypatch):
    root, rows = make_project(tmp_path)
    item = rows[0]

    monkeypatch.setattr(
        mi,
        "detect_media_tools",
        lambda: mi.ToolStatus(ffmpeg="/fake/ffmpeg", ffprobe="/fake/ffprobe"),
    )
    monkeypatch.setattr(
        mi,
        "probe_media",
        lambda path: {
            "duration_seconds": 10.0,
            "width": 1280,
            "height": 720,
            "fps": 24.0,
            "video_codec": "h264",
        },
    )
    monkeypatch.setattr(
        mi,
        "visual_signature",
        lambda path, duration_seconds: ["abcd"] * 6,
    )
    fake_strip = root / "cache" / "filmstrips" / "fake.jpg"
    fake_strip.parent.mkdir(parents=True, exist_ok=True)
    fake_strip.write_bytes(b"jpeg")
    monkeypatch.setattr(
        mi,
        "generate_filmstrip",
        lambda root, media_id, force=False: fake_strip,
    )

    result = mi.analyze_media(root, item["id"], make_filmstrip=True)
    assert result["status"] == "READY"
    assert result["technical"]["width"] == 1280
    assert result["visual_signature"] == ["abcd"] * 6
    assert result["filmstrip_path"] == "cache/filmstrips/fake.jpg"

    loaded = mi.get_media_analysis(root, item["id"])
    assert loaded["analyzer_version"] == mi.ANALYZER_VERSION
    assert loaded["technical"]["fps"] == 24.0


def test_media_similarity_prefers_visual_match(tmp_path):
    root, rows = make_project(tmp_path)
    by_name = {Path(x["relative_path"]).name: x for x in rows}
    a = by_name["malo_take_a.mp4"]
    b = by_name["malo_take_b.mp4"]
    ronan = by_name["ronan_rire.mp4"]

    mi._write_analysis(
        root,
        a["id"],
        status="READY",
        technical={"filename_tokens": ["malo"]},
        signature=["ffffffffffffffffffffffffffffffffffff"] * 6,
        filmstrip_path=None,
    )
    mi._write_analysis(
        root,
        b["id"],
        status="READY",
        technical={"filename_tokens": ["malo"]},
        signature=["ffffffffffffffffffffffffffffffffffff"] * 6,
        filmstrip_path=None,
    )
    mi._write_analysis(
        root,
        ronan["id"],
        status="READY",
        technical={"filename_tokens": ["ronan", "rire"]},
        signature=["000000000000000000000000000000000000"] * 6,
        filmstrip_path=None,
    )

    result = mi.media_similarity(root, a["id"])
    assert result[0]["media_id"] == b["id"]
    assert result[0]["visual_similarity"] == 1.0
    assert result[-1]["media_id"] == ronan["id"]
    assert result[-1]["visual_similarity"] < 0.05


def test_tools_unavailable_is_explicit_not_failure(tmp_path, monkeypatch):
    root, rows = make_project(tmp_path)
    monkeypatch.setattr(
        mi,
        "detect_media_tools",
        lambda: mi.ToolStatus(ffmpeg=None, ffprobe=None),
    )
    result = mi.analyze_media(root, rows[0]["id"])
    assert result["status"] == "TOOLS_UNAVAILABLE"
    assert result["technical"]["ffmpeg_available"] is False
