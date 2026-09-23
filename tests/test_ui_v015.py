from pathlib import Path

from fastapi.testclient import TestClient

from piste_studio.app import create_app
from piste_studio.project import init_project

ROOT = Path(__file__).parents[1]
UI = ROOT / "piste_studio" / "ui"


def test_v015_ui_structure_and_assets(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "UI Test")
    app = create_app(root, UI / "index.html")
    client = TestClient(app)
    html = client.get("/").text

    assert "PISTE Studio — Local App v0.15" in html
    assert 'data-workspace="assemble"' in html
    assert 'data-workspace="edit"' in html
    assert 'data-workspace="review"' in html
    assert 'id="overlayBtn"' in html
    assert 'id="commandPalette"' in html
    assert 'id="focusExit"' in html
    assert 'data-focus-pane="viewer"' in html
    assert 'data-focus-pane="timeline"' in html
    assert 'id="undoBtn"' in html
    assert "Storyline magnétique" in html

    assets = (
        "style.css",
        "state.js",
        "editor.js",
        "ux-browser.js",
        "ux-timeline.js",
        "ux-magnetic.js",
        "ux-shell.js",
        "ux-polish.js",
        "backend.js",
    )
    for asset in assets:
        r = client.get(f"/ui/{asset}")
        assert r.status_code == 200
        assert len(r.content) > 100


def test_v015_ux_contains_user_facing_refinements():
    ux = "".join(
        (UI / name).read_text(encoding="utf-8")
        for name in (
            "state.js",
            "ux-browser.js",
            "ux-timeline.js",
            "ux-magnetic.js",
            "ux-shell.js",
            "ux-polish.js",
        )
    )
    assert "PisteState" in ux
    assert "setFocusPane" in ux
    assert "openCommandPalette" in ux
    assert "toggleOverlayMenu" in ux
    assert "overlayHud" in ux
    assert "overlayMix" in ux
    assert "overlayRange" in ux
    assert "checkpointBeforeMagnetic" in ux
    assert "undoLastEdit" in ux
