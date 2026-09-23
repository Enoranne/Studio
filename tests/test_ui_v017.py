from pathlib import Path

from fastapi.testclient import TestClient

from piste_studio.app import create_app
from piste_studio.project import init_project

ROOT = Path(__file__).parents[1]
UI = ROOT / "piste_studio" / "ui"


def test_v017_ui_structure_and_assets(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "UI Test")
    app = create_app(root, UI / "index.html")
    client = TestClient(app)
    html = client.get("/").text

    assert "PISTE Studio — Local App v0.17" in html
    assert 'id="analyzeMediaBtn"' in html
    assert 'id="editorialDrawer"' in html
    assert 'id="markerComposer"' in html
    assert 'id="commandPalette"' in html
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
        "ux-editorial.js",
        "ux-media-intelligence.js",
        "backend.js",
    )
    for asset in assets:
        r = client.get(f"/ui/{asset}")
        assert r.status_code == 200
        assert len(r.content) > 100


def test_v017_ux_contains_media_intelligence_patterns():
    ux = "".join(
        (UI / name).read_text(encoding="utf-8")
        for name in (
            "ux-browser.js",
            "ux-editorial.js",
            "ux-media-intelligence.js",
            "backend.js",
        )
    )
    assert "filmstripUrl" in ux
    assert "analyzeMediaCatalog" in ux
    assert "analyzeSelectedMedia" in ux
    assert "openSimilarTakes" in ux
    assert "visual_similarity" in ux
    assert "openSourceSelector" in ux
    assert "editorialRanges" in ux
