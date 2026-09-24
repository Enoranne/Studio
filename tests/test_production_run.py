from pathlib import Path
import json

from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.production_run import build_production_run_report, save_production_run_report
from piste_studio.project import init_project
from piste_studio.versioning import create_timeline_version


def make_project(tmp_path: Path) -> Path:
    root = tmp_path / "PISTE_0"
    init_project(root, "PISTE 0")
    for index in range(5):
        (root / "rushes" / f"shot_{index}.mp4").write_bytes(b"video")
    (root / "audio" / "voice.wav").write_bytes(b"audio")
    scan_media(root)
    for row in fetch_media_with_metadata(root):
        set_media_metadata(
            root,
            row["id"],
            title=Path(row["relative_path"]).stem,
            duration_seconds=10.0,
        )
    return root


def publish_representative_timeline(root: Path):
    rows = fetch_media_with_metadata(root)
    videos = [row for row in rows if row["kind"] == "video"]
    audio = next(row for row in rows if row["kind"] == "audio")
    clips = []
    for index, row in enumerate(videos[:5]):
        clips.append({
            "id": f"v{index+1}",
            "track": "video",
            "label": f"Plan {index+1}",
            "start": index * 4,
            "duration": 4,
            "sourceStart": 0,
            "mediaDbId": row["id"],
        })
    clips.extend([
        {
            "id": "a1",
            "track": "vo",
            "label": "VO",
            "start": 1,
            "duration": 8,
            "sourceStart": 0,
            "audioDbId": audio["id"],
            "fadeIn": 0.3,
            "fadeOut": 0.4,
            "volumeEnvelope": [{"time": 0, "gainDb": -6}, {"time": 4, "gainDb": -9}],
            "parentClipId": "v1",
            "anchorOffset": 1,
            "connectionPointOffset": 1,
            "connectionMode": "follow",
        },
        {
            "id": "t1",
            "track": "titles",
            "label": "Titre",
            "text": "PISTE 0",
            "titleRole": "overlay",
            "start": 2,
            "duration": 2,
            "parentClipId": "v1",
            "anchorOffset": 2,
            "connectionPointOffset": 2,
            "connectionMode": "follow",
        },
        {
            "id": "t2",
            "track": "titles",
            "label": "Fin",
            "text": "PISTE 0",
            "titleRole": "final_card",
            "start": 18,
            "duration": 2,
        },
    ])
    return create_timeline_version(root, {
        "edit_name": "teaser_30",
        "duration_seconds": 20,
        "tracks": [
            {"id": "video", "name": "VIDEO", "kind": "video"},
            {"id": "titles", "name": "TITLES", "kind": "title"},
            {"id": "vo", "name": "VO", "kind": "audio"},
        ],
        "clips": clips,
    })


def test_production_run_reports_representative_edit(tmp_path):
    root = make_project(tmp_path)
    rec = publish_representative_timeline(root)
    report = build_production_run_report(root, edit_name=rec.edit_name)
    by_id = {x["id"]: x for x in report["criteria"]}
    assert by_id["real_video_sequence"]["status"] == "PASS"
    assert by_id["audio_present"]["status"] == "PASS"
    assert by_id["audio_fade"]["status"] == "PASS"
    assert by_id["audio_automation"]["status"] == "PASS"
    assert by_id["title_overlay"]["status"] == "PASS"
    assert by_id["final_card"]["status"] == "PASS"
    assert by_id["storyline_connection"]["status"] == "PASS"
    assert by_id["delivery_artifact"]["status"] == "MISSING"
    assert report["human_review_required"] is True
    assert report["machine_complete"] is False


def test_production_run_never_auto_passes_human_review(tmp_path):
    root = make_project(tmp_path)
    rec = publish_representative_timeline(root)
    version_dir = rec.directory
    (version_dir / f"{rec.edit_name}_{rec.version_label}.mp4").write_bytes(b"render")

    report_dir = root / "reports" / "delivery"
    report_dir.mkdir(parents=True, exist_ok=True)
    export_dir = root / "exports" / rec.edit_name / rec.version_label
    export_dir.mkdir(parents=True, exist_ok=True)
    output = export_dir / f"{rec.edit_name}_{rec.version_label}_online_1080.mp4"
    output.write_bytes(b"delivery")
    (report_dir / f"{rec.edit_name}_{rec.version_label}_online_1080.json").write_text(
        json.dumps({
            "output_relative_path": output.relative_to(root).as_posix(),
            "conformance": {"status": "PASS", "reasons": []},
        }),
        encoding="utf-8",
    )

    report = build_production_run_report(root, edit_name=rec.edit_name)
    assert report["machine_complete"] is True
    assert report["status"] in {"IN_PROGRESS", "AWAITING_HUMAN_REVIEW"}
    assert report["status"] != "PASS"
    assert report["policy"]["never_auto_pass_human_review"] is True


def test_production_run_report_can_be_saved(tmp_path):
    root = make_project(tmp_path)
    rec = publish_representative_timeline(root)
    path = save_production_run_report(root, edit_name=rec.edit_name)
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == "0.24.1"
    assert data["published_version"] == rec.version_label
