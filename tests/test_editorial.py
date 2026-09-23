from pathlib import Path

from piste_studio.db import connect
from piste_studio.editorial import (
    add_marker,
    delete_editorial_range,
    delete_marker,
    list_editorial_ranges,
    list_markers,
    set_editorial_range,
    suggest_alternatives,
)
from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.project import init_project


def make_editorial_project(tmp_path: Path) -> Path:
    root = tmp_path / "Editorial"
    init_project(root, "Editorial")
    for name in ("malo_fisher.mp4", "malo_radio.mp4", "ronan_rire.mp4"):
        (root / "rushes" / name).write_bytes(name.encode())
    scan_media(root)
    rows = fetch_media_with_metadata(root)
    by_name = {Path(r["relative_path"]).name: r for r in rows}
    set_media_metadata(
        root,
        by_name["malo_fisher.mp4"]["id"],
        title="Malo Fisher",
        duration_seconds=12,
        rating=4,
        tags=["malo", "enfance", "fisher"],
    )
    set_media_metadata(
        root,
        by_name["malo_radio.mp4"]["id"],
        title="Malo Radio",
        duration_seconds=10,
        rating=5,
        tags=["malo", "enfance", "radio"],
    )
    set_media_metadata(
        root,
        by_name["ronan_rire.mp4"]["id"],
        title="Ronan Rire",
        duration_seconds=8,
        rating=3,
        tags=["ronan", "rire"],
    )
    conn = connect(root / "media.sqlite")
    try:
        conn.execute(
            "UPDATE media SET status='APPROVED', trailer_safe=1 WHERE id IN (?, ?, ?)",
            (
                by_name["malo_fisher.mp4"]["id"],
                by_name["malo_radio.mp4"]["id"],
                by_name["ronan_rire.mp4"]["id"],
            ),
        )
        conn.execute(
            "UPDATE media SET canonical=1 WHERE id=?",
            (by_name["malo_radio.mp4"]["id"],),
        )
        conn.commit()
    finally:
        conn.close()
    return root


def test_editorial_ranges_persist_and_opposite_overlap_is_removed(tmp_path):
    root = make_editorial_project(tmp_path)
    media = fetch_media_with_metadata(root)
    mid = next(x["id"] for x in media if x["title"] == "Malo Fisher")

    favorite = set_editorial_range(
        root, mid, kind="favorite", source_in=2, source_out=6
    )
    assert favorite["kind"] == "favorite"
    assert list_editorial_ranges(root, mid)[0]["source_in"] == 2

    reject = set_editorial_range(
        root, mid, kind="reject", source_in=4, source_out=7
    )
    ranges = list_editorial_ranges(root, mid)
    assert len(ranges) == 1
    assert ranges[0]["kind"] == "reject"

    assert delete_editorial_range(root, reject["id"]) is True
    assert list_editorial_ranges(root, mid) == []


def test_markers_persist_per_edit(tmp_path):
    root = make_editorial_project(tmp_path)
    marker = add_marker(
        root,
        edit_name="teaser_30",
        time_seconds=7.5,
        label="Respiration",
        kind="decision",
    )
    assert marker["label"] == "Respiration"
    markers = list_markers(root, "teaser_30")
    assert len(markers) == 1
    assert markers[0]["time_seconds"] == 7.5
    assert list_markers(root, "other_edit") == []
    assert delete_marker(root, marker["id"]) is True


def test_source_selector_is_explainable_and_prefers_strong_match(tmp_path):
    root = make_editorial_project(tmp_path)
    media = fetch_media_with_metadata(root)
    by_title = {x["title"]: x for x in media}
    reference = by_title["Malo Fisher"]
    alternative = by_title["Malo Radio"]

    set_editorial_range(
        root,
        alternative["id"],
        kind="favorite",
        source_in=1.5,
        source_out=5.5,
    )

    result = suggest_alternatives(
        root, reference["id"], limit=5, max_spoiler=0
    )
    assert result["policy"]["human_validation_required"] is True
    assert result["policy"]["automatic_replacement"] is False
    assert result["suggestions"][0]["media_id"] == alternative["id"]
    assert result["suggestions"][0]["source_in"] == 1.5
    reasons = " ".join(result["suggestions"][0]["reasons"])
    assert "Tags communs" in reasons
    assert "Média canonique" in reasons
    assert "plage Favorite" in reasons
