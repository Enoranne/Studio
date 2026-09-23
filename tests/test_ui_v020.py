from pathlib import Path

from fastapi.testclient import TestClient

from piste_studio.app import create_app
from piste_studio.project import init_project

ROOT = Path(__file__).parents[1]
UI = ROOT / "piste_studio" / "ui"


def test_v022_ui_structure_and_assets(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "UI Test")
    app = create_app(root, UI / "index.html")
    client = TestClient(app)
    html = client.get("/").text

    assert "PISTE Studio — Local App v0.22" in html
    assert 'id="audioMeters"' in html
    assert 'id="editorialDrawer"' in html
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
        "ux-editorial-vision.js",
        "ux-semantic-vision.js",
        "ux-audio-mix.js",
        "ux-audio-intelligence.js",
        "ux-audio-delivery.js",
        "backend.js",
    )
    for asset in assets:
        r = client.get(f"/ui/{asset}")
        assert r.status_code == 200
        assert len(r.content) > 100


def test_v021_ux_contains_audio_intelligence_patterns():
    ux = (UI / "ux-audio-intelligence.js").read_text(encoding="utf-8")
    assert "LUFS-I" in ux
    assert "TRUE PEAK" in ux
    assert "openNormalizationProposal" in ux
    assert "openClippingReport" in ux
    assert "openDuckingProposal" in ux
    assert "openCrossfadeProposal" in ux
    assert "human" not in ux.lower() or "Validation humaine" in ux


def test_v021_ux_contains_master_delivery_patterns():
    ux = (UI / "ux-audio-delivery.js").read_text(encoding="utf-8")
    assert "Master Check" in ux
    assert "LUFS-I MASTER" in ux
    assert "TRUE PEAK" in ux
    assert "limiteur" in ux.lower()
    assert "Télécharger le rapport JSON" in ux
    assert "openAudioExportAdvisory" in ux
    assert "Exporter quand même" in ux
    assert "Export non bloqué" in ux


def test_v022_ux_contains_editorial_vision_patterns():
    ux = (UI / "ux-editorial-vision.js").read_text(encoding="utf-8")
    media_ux = (UI / "ux-media-intelligence.js").read_text(encoding="utf-8")
    polish = (UI / "ux-polish.js").read_text(encoding="utf-8")
    assert "Fenêtres IN/OUT" in ux
    assert "RUPTURES VISUELLES" in ux
    assert "aucune coupe automatique" in ux
    assert "Charger IN/OUT" in ux
    assert "Fenêtres IN/OUT" in media_ux
    assert "Vision · Fenêtres IN/OUT" in polish
