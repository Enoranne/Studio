from pathlib import Path
import json
import re

from fastapi.testclient import TestClient
import pytest

from piste_studio import __version__
from piste_studio.app import create_app
from piste_studio.locks import add_lock
from piste_studio.project import init_project
from piste_studio.storyline import (
    StorylineError,
    apply_storyline_operation,
    validate_locked_change,
)
from piste_studio.timeline import validate_timeline


ROOT = Path(__file__).parents[1]
UI = ROOT / "piste_studio" / "ui" / "index.html"


def base_doc():
    return {
        "edit_name": "kernel",
        "duration_seconds": 30,
        "storyline": {"mode": "magnetic", "start": 2},
        "tracks": [
            {"id": "video", "name": "VIDEO", "kind": "video"},
            {"id": "titles", "name": "TITLES", "kind": "title"},
        ],
        "clips": [
            {
                "id": "v1",
                "track": "video",
                "start": 2,
                "duration": 3,
                "sourceStart": 0,
            },
            {
                "id": "v2",
                "track": "video",
                "start": 5,
                "duration": 2,
                "sourceStart": 0,
            },
            {
                "id": "t1",
                "track": "titles",
                "label": "Titre",
                "start": 6,
                "duration": 0.5,
                "parentClipId": "v2",
                "anchorOffset": 1,
                "connectionMode": "follow",
            },
        ],
    }


def test_canonical_operation_dispatches_move_and_trim():
    moved = apply_storyline_operation(
        base_doc(),
        "move",
        {"clip_id": "v2", "target_time": 2.1},
    )
    by_id = {clip["id"]: clip for clip in moved["clips"]}
    assert by_id["v2"]["start"] == 2
    assert by_id["v1"]["start"] == 4
    assert by_id["t1"]["start"] == 3

    trimmed = apply_storyline_operation(
        moved,
        "trim",
        {
            "clip_id": "v2",
            "edge": "right",
            "delta": 0.25,
        },
    )
    by_id = {clip["id"]: clip for clip in trimmed["clips"]}
    assert by_id["v2"]["duration"] == 2.25
    assert by_id["v1"]["start"] == 4.25
    assert by_id["t1"]["start"] == 3


def test_canonical_insert_and_remove_preserve_storyline_invariants():
    inserted = apply_storyline_operation(
        base_doc(),
        "insert",
        {
            "clip": {
                "id": "v3",
                "track": "video",
                "start": 0,
                "duration": 1.25,
                "sourceStart": 0,
            },
            "target_time": 4.9,
        },
    )
    story = sorted(
        (clip for clip in inserted["clips"] if clip["track"] == "video"),
        key=lambda clip: clip["start"],
    )
    assert [clip["id"] for clip in story] == ["v1", "v3", "v2"]
    assert [clip["start"] for clip in story] == [2, 5, 6.25]

    removed = apply_storyline_operation(
        inserted,
        "remove",
        {"clip_id": "v2"},
    )
    by_id = {clip["id"]: clip for clip in removed["clips"]}
    assert "v2" not in by_id
    assert "parentClipId" not in by_id["t1"]
    story = sorted(
        (clip for clip in removed["clips"] if clip["track"] == "video"),
        key=lambda clip: clip["start"],
    )
    assert [clip["start"] for clip in story] == [2, 5]


def test_canonical_operation_rejects_unknown_operation():
    with pytest.raises(StorylineError, match="inconnue"):
        apply_storyline_operation(base_doc(), "teleport", {})


def test_storyline_operation_api_uses_kernel_and_returns_validated_candidate(tmp_path):
    root = tmp_path / "KernelAPI"
    init_project(root, "Kernel API")
    app = create_app(root, UI)
    client = TestClient(app)

    response = client.post(
        "/api/storyline/operate",
        json={
            "timeline": base_doc(),
            "operation": "connection_point",
            "args": {
                "child_id": "t1",
                "target_time": 3.5,
            },
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["operation"] == "connection_point"
    candidate = body["timeline"]
    child = next(clip for clip in candidate["clips"] if clip["id"] == "t1")
    assert child["start"] == 6
    assert child["parentClipId"] == "v1"
    assert child["connectionPointOffset"] == 1.5
    assert validate_timeline(root, candidate)["storyline"]["mode"] == "magnetic"


def test_storyline_operation_api_rejects_bad_operation(tmp_path):
    root = tmp_path / "KernelAPIBad"
    init_project(root, "Kernel API")
    app = create_app(root, UI)
    client = TestClient(app)

    response = client.post(
        "/api/storyline/operate",
        json={
            "timeline": base_doc(),
            "operation": "teleport",
            "args": {},
        },
    )
    assert response.status_code == 422
    assert "inconnue" in response.text


def test_magnetic_ui_delegates_core_gestures_to_backend_kernel():
    script = (ROOT / "piste_studio" / "ui" / "ux-magnetic.js").read_text(
        encoding="utf-8"
    )
    assert "/api/storyline/operate" in script
    assert "commitBackendMagneticOperation" in script
    assert "'move'" in script
    assert "'trim'" in script
    assert "'connection_point'" in script
    assert "backendConnected" in script


def test_storyline_insert_respects_existing_reorder_hard_lock(tmp_path):
    root = tmp_path / "InsertLock"
    init_project(root, "Insert lock")
    add_lock(root, "Protected Story", 2.0, 4.5, "HARD", ["reorder"])
    before = base_doc()
    after = apply_storyline_operation(
        before,
        "insert",
        {
            "clip": {
                "id": "v3",
                "track": "video",
                "start": 0,
                "duration": 0.5,
                "sourceStart": 0,
            },
            "target_time": 2.1,
        },
    )
    with pytest.raises(StorylineError, match="HARD LOCK"):
        validate_locked_change(root, before, after)


def test_storyline_remove_respects_existing_reorder_hard_lock(tmp_path):
    root = tmp_path / "RemoveLock"
    init_project(root, "Remove lock")
    add_lock(root, "Protected Story", 2.0, 4.5, "HARD", ["reorder"])
    before = {
        "edit_name": "kernel",
        "duration_seconds": 30,
        "storyline": {"mode": "magnetic", "start": 2},
        "tracks": [{"id": "video", "name": "VIDEO", "kind": "video"}],
        "clips": [
            {
                "id": "v1",
                "track": "video",
                "start": 2,
                "duration": 3,
                "sourceStart": 0,
            }
        ],
    }
    after = apply_storyline_operation(
        before,
        "remove",
        {"clip_id": "v1"},
    )
    with pytest.raises(StorylineError, match="HARD LOCK"):
        validate_locked_change(root, before, after)


def test_magnetic_ui_delegates_insert_remove_and_serializes_media_for_kernel():
    script = (ROOT / "piste_studio" / "ui" / "ux-magnetic.js").read_text(
        encoding="utf-8"
    )
    assert "function backendClipPayload" in script
    assert "{clip:backendClipPayload(newClip),target_time:start}" in script
    assert "{clip:backendClipPayload(c)}" in script
    assert "'remove'," in script
    assert "{clip_id:c.id}" in script


def test_v029_version_is_aligned_across_python_desktop_ui_and_smoke_test():
    expected = "0.29.1"
    assert __version__ == expected

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project_block = pyproject.split("[project]", 1)[1].split("[", 1)[0]
    match = re.search(r'^version\s*=\s*"([^"]+)"', project_block, re.MULTILINE)
    assert match is not None
    assert match.group(1) == expected

    package = json.loads(
        (ROOT / "desktop" / "package.json").read_text(encoding="utf-8")
    )
    tauri = json.loads(
        (ROOT / "desktop" / "src-tauri" / "tauri.conf.json").read_text(
            encoding="utf-8"
        )
    )
    assert package["version"] == expected
    assert tauri["version"] == expected

    cargo = (ROOT / "desktop" / "src-tauri" / "Cargo.toml").read_text(
        encoding="utf-8"
    )
    assert f'version = "{expected}"' in cargo

    html = (ROOT / "piste_studio" / "ui" / "index.html").read_text(
        encoding="utf-8"
    )
    assert f"Local App v{expected}" in html
    assert f"v{expected} · LOCAL" in html

    workflow = (
        ROOT / ".github" / "workflows" / "desktop-macos.yml"
    ).read_text(encoding="utf-8")
    assert f'\"version\":\"{expected}\"' in workflow


def test_storyline_operation_api_can_checkpoint_atomically(tmp_path):
    root = tmp_path / "AtomicKernel"
    init_project(root, "Atomic kernel")
    app = create_app(root, UI)
    client = TestClient(app)

    response = client.post(
        "/api/storyline/operate",
        json={
            "timeline": base_doc(),
            "operation": "move",
            "args": {"clip_id": "v2", "target_time": 2.1},
            "edit_name": "kernel",
            "checkpoint_reason": "Move Storyline",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["checkpoint"]["can_undo"] is True
    assert body["checkpoint"]["last"]["reason"] == "Move Storyline"

    history = client.get("/api/history", params={"edit_name": "kernel"})
    assert history.status_code == 200
    assert history.json()["can_undo"] is True
    assert history.json()["last"]["reason"] == "Move Storyline"


def test_magnetic_ui_requests_atomic_checkpoint_with_backend_operation():
    script = (ROOT / "piste_studio" / "ui" / "ux-magnetic.js").read_text(
        encoding="utf-8"
    )
    assert "checkpoint_reason:message" in script
