from pathlib import Path

from fastapi.testclient import TestClient

from piste_studio.app import create_app
from piste_studio.config import write_yaml
from piste_studio.media import scan_media
from piste_studio.metadata import set_media_metadata, fetch_media_with_metadata
from piste_studio.project import init_project


def make_project(tmp_path: Path) -> Path:
    root = tmp_path / "Project"
    init_project(root, "Test Film")
    write_yaml(root / "canon.yaml", {
        "schema_version": 1,
        "project": {"title": "Test Film", "subtitle": "Teaser"},
        "visual": {"aspect_ratio": "16:9", "look": ["warm"], "avoid": []},
        "editing": {"principles": ["restrained"], "avoid": []},
        "sound": {"motifs": ["cassette hiss"], "ending_sequence": ["click"]},
        "characters": {}, "props": {},
    })
    write_yaml(root / "locks.yaml", {
        "schema_version": 1,
        "locks": [{"name": "Opening", "start": 0.0, "end": 3.0, "level": "HARD", "forbidden": ["trim"]}],
    })
    (root / "rushes" / "clip.mp4").write_bytes(b"fake-mp4-bytes")
    (root / "audio" / "voice.wav").write_bytes(b"fake-wav-bytes")
    scan_media(root)
    rows = fetch_media_with_metadata(root)
    for r in rows:
        set_media_metadata(root, r["id"], title=Path(r["relative_path"]).stem, duration_seconds=10.0)
    return root


def test_state_and_media_stream(tmp_path):
    root = make_project(tmp_path)
    app = create_app(root, Path(__file__).parents[1] / "piste_studio" / "ui" / "index.html")
    client = TestClient(app)
    state = client.get("/api/state")
    assert state.status_code == 200
    body = state.json()
    assert body["project"]["project"]["name"] == "Test Film"
    assert len(body["media"]) == 2
    assert body["locks"]["locks"][0]["level"] == "HARD"
    video = next(x for x in body["media"] if x["kind"] == "video")
    media = client.get(video["stream_url"])
    assert media.status_code == 200
    assert media.content == b"fake-mp4-bytes"


def test_timeline_persists_and_reloads(tmp_path):
    root = make_project(tmp_path)
    app = create_app(root, Path(__file__).parents[1] / "piste_studio" / "ui" / "index.html")
    client = TestClient(app)
    media = client.get("/api/state").json()["media"]
    video_id = next(x["id"] for x in media if x["kind"] == "video")
    audio_id = next(x["id"] for x in media if x["kind"] == "audio")
    payload = {
        "edit_name": "teaser_30",
        "duration_seconds": 30,
        "tracks": [
            {"id": "video", "name": "VIDEO", "kind": "video"},
            {"id": "vo", "name": "VO", "kind": "audio"},
        ],
        "clips": [
            {"id": "v1", "track": "video", "label": "clip", "start": 3, "duration": 4, "sourceStart": 1, "mediaDbId": video_id},
            {"id": "a1", "track": "vo", "label": "voice", "start": 3, "duration": 5, "sourceStart": 0, "audioDbId": audio_id, "gain": 0.8, "fadeIn": 0.2, "fadeOut": 0.3},
        ],
    }
    saved = client.post("/api/timeline", json=payload)
    assert saved.status_code == 200, saved.text
    reloaded = client.get("/api/timeline?edit_name=teaser_30").json()["timeline"]
    assert reloaded["clips"][0]["mediaDbId"] == video_id
    assert reloaded["clips"][1]["audioDbId"] == audio_id


def test_timeline_collision_rejected(tmp_path):
    root = make_project(tmp_path)
    app = create_app(root, Path(__file__).parents[1] / "piste_studio" / "ui" / "index.html")
    client = TestClient(app)
    payload = {
        "edit_name": "teaser_30", "duration_seconds": 30,
        "tracks": [{"id": "video", "name": "VIDEO", "kind": "video"}],
        "clips": [
            {"id": "v1", "track": "video", "start": 3, "duration": 4},
            {"id": "v2", "track": "video", "start": 6, "duration": 4},
        ],
    }
    r = client.post("/api/timeline", json=payload)
    assert r.status_code == 422
    assert "Collision" in r.text


def test_lock_check_uses_core_engine(tmp_path):
    root = make_project(tmp_path)
    app = create_app(root, Path(__file__).parents[1] / "piste_studio" / "ui" / "index.html")
    client = TestClient(app)
    blocked = client.post("/api/locks/check", json={"operation": "trim", "start": 1, "end": 2, "target": "timeline"})
    assert blocked.status_code == 200
    assert blocked.json()["allowed"] is False
    allowed = client.post("/api/locks/check", json={"operation": "trim", "start": 4, "end": 5, "target": "timeline"})
    assert allowed.json()["allowed"] is True


def test_scan_endpoint(tmp_path):
    root = make_project(tmp_path)
    app = create_app(root, Path(__file__).parents[1] / "piste_studio" / "ui" / "index.html")
    client = TestClient(app)
    (root / "rushes" / "second.mov").write_bytes(b"second-video")
    r = client.post("/api/scan", json={})
    assert r.status_code == 200
    assert r.json()["scan"]["inserted"] == 1
    assert len(r.json()["media"]) == 3


def test_publish_timeline_creates_version_and_tesseract_dry_run(tmp_path):
    root = make_project(tmp_path)
    app = create_app(root, Path(__file__).parents[1] / "piste_studio" / "ui" / "index.html")
    client = TestClient(app)
    media = client.get("/api/state").json()["media"]
    video_id = next(x["id"] for x in media if x["kind"] == "video")
    audio_id = next(x["id"] for x in media if x["kind"] == "audio")
    payload = {
        "edit_name": "teaser_30", "duration_seconds": 30,
        "tracks": [
            {"id": "video", "name": "VIDEO", "kind": "video"},
            {"id": "vo", "name": "VO", "kind": "audio"},
        ],
        "clips": [
            {"id": "v1", "track": "video", "label": "clip", "start": 3, "duration": 4, "sourceStart": 1, "mediaDbId": video_id},
            {"id": "a1", "track": "vo", "label": "voice", "start": 3, "duration": 5, "sourceStart": 0, "audioDbId": audio_id, "gain": 0.8, "fadeIn": 0.2, "fadeOut": 0.3},
        ],
    }
    assert client.post("/api/timeline", json=payload).status_code == 200
    published = client.post("/api/publish", json={"edit_name": "teaser_30"})
    assert published.status_code == 200, published.text
    assert published.json()["version"] == "V001"
    version_dir = root / "edits" / "teaser_30" / "V001"
    assert (version_dir / "timeline.json").exists()
    assert (version_dir / "brief.yaml").exists()
    dry = client.post("/api/tesseract/V001/author", json={"edit_name": "teaser_30", "execute": False})
    assert dry.status_code == 200, dry.text
    plan = dry.json()["plan"]
    assert len(plan["cuts"]) == 1
    assert len(plan["audio_cuts"]) == 1


def test_storyline_validate_endpoint_accepts_magnetic_connection(tmp_path):
    root = make_project(tmp_path)
    app = create_app(root, Path(__file__).parents[1] / "piste_studio" / "ui" / "index.html")
    client = TestClient(app)
    timeline = {
        "edit_name": "teaser_30",
        "duration_seconds": 30,
        "storyline": {"mode": "magnetic", "start": 5},
        "tracks": [
            {"id": "video", "name": "VIDEO", "kind": "video"},
            {"id": "vo", "name": "VO", "kind": "audio"},
        ],
        "clips": [
            {"id": "v1", "track": "video", "start": 5, "duration": 4, "sourceStart": 0},
            {"id": "a1", "track": "vo", "start": 6, "duration": 1, "sourceStart": 0,
             "parentClipId": "v1", "anchorOffset": 1, "connectionMode": "follow"},
        ],
    }
    r = client.post("/api/storyline/validate", json={"before": timeline, "after": timeline})
    assert r.status_code == 200, r.text
    assert r.json()["timeline"]["storyline"]["mode"] == "magnetic"


def test_history_api_checkpoint_and_undo(tmp_path):
    root = make_project(tmp_path)
    app = create_app(root, Path(__file__).parents[1] / "piste_studio" / "ui" / "index.html")
    client = TestClient(app)
    base = {
        "edit_name": "teaser_30",
        "duration_seconds": 30,
        "storyline": {"mode": "magnetic", "start": 5},
        "tracks": [{"id": "video", "name": "VIDEO", "kind": "video"}],
        "clips": [{"id": "v1", "track": "video", "start": 5, "duration": 4, "sourceStart": 0}],
    }
    assert client.post("/api/timeline", json=base).status_code == 200
    cp = client.post(
        "/api/history/checkpoint",
        json={"edit_name": "teaser_30", "reason": "before move", "timeline": base},
    )
    assert cp.status_code == 200, cp.text
    assert cp.json()["can_undo"] is True

    changed = {
        **base,
        "storyline": {"mode": "magnetic", "start": 7},
        "clips": [{"id": "v1", "track": "video", "start": 7, "duration": 4, "sourceStart": 0}],
    }
    assert client.post("/api/timeline", json=changed).status_code == 200

    undo = client.post("/api/history/undo", json={"edit_name": "teaser_30"})
    assert undo.status_code == 200, undo.text
    assert undo.json()["timeline"]["storyline"]["start"] == 5
    current = client.get("/api/timeline?edit_name=teaser_30").json()["timeline"]
    assert current["storyline"]["start"] == 5
