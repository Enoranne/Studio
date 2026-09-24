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

    assert "PISTE Studio — Local App v0.27.0" in html
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
        "ux-targeted-references.js",
        "ux-timeline-continuity.js",
        "ux-titles.js",
        "ux-audio-mix.js",
        "ux-audio-intelligence.js",
        "ux-audio-delivery.js",
        "ux-delivery.js",
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


def test_v022_ux_contains_targeted_reference_patterns():
    ux = (UI / "ux-targeted-references.js").read_text(encoding="utf-8")
    semantic = (UI / "ux-semantic-vision.js").read_text(encoding="utf-8")
    polish = (UI / "ux-polish.js").read_text(encoding="utf-8")
    assert "RÉFÉRENCE CIBLÉE" in ux
    assert "Utiliser le frame affiché" in ux
    assert "Zone de l’image" in ux
    assert "aucun tag global ajouté au rush" in ux
    assert "openTargetedReferenceManager" in semantic
    assert "targeted_reference_count" in semantic
    assert "Vision · Référence ciblée" in polish


def test_v022_ux_contains_reference_group_quality_patterns():
    ux = (UI / "ux-targeted-references.js").read_text(encoding="utf-8")
    semantic = (UI / "ux-semantic-vision.js").read_text(encoding="utf-8")
    assert "GROUPES DE RÉFÉRENCES" in ux
    assert "Primaire · 1,5×" in ux
    assert "Secondaire · 1,0×" in ux
    assert "Faible · 0,5×" in ux
    assert "Enregistrer groupe/qualité" in ux
    assert "/api/vision/reference-groups" in ux
    assert "reference_group_count" in semantic
    assert "quality_distribution" in semantic


def test_v022_ux_contains_canon_conflict_patterns():
    semantic = (UI / "ux-semantic-vision.js").read_text(encoding="utf-8")
    backend = (UI / "backend.js").read_text(encoding="utf-8")
    assert "CONFLIT CANON" in semantic
    assert "CANON ALIGNÉ" in semantic
    assert "NON VÉRIFIÉ" in semantic
    assert "Accepter malgré conflit" in semantic
    assert "requires_explicit_acknowledgement" in semantic
    assert "Règles sémantiques" in backend
    assert "Facets fermés" in backend


def test_v022_ux_contains_timeline_neighbor_continuity_patterns():
    ux = (UI / "ux-timeline-continuity.js").read_text(encoding="utf-8")
    assert "CONTINUITÉ DE VOISINAGE" in ux
    assert "Analyser voisins" in ux
    assert "Tester un autre rush à cette position" in ux
    assert "Tester ce candidat" in ux
    assert "/api/vision/timeline-continuity" in ux
    assert "continuityFindingMarkup" in ux
    assert "RUPTURE POTENTIELLE" in ux
    assert "À VÉRIFIER" in ux
    assert "Aucun remplacement n’est appliqué automatiquement" in ux
    assert "Vision · Continuité voisins" in ux


def test_v023_ux_contains_editable_title_patterns():
    ux = (UI / "ux-titles.js").read_text(encoding="utf-8")
    assert "TITRE / OVERLAY" in ux
    assert "Lower third" in ux
    assert "titleFontSize" in ux
    assert "titlePositionX" in ux
    assert "titleBackgroundOpacity" in ux
    assert "Familles génériques" in ux
    assert "Titre / overlay mis à jour" in ux
    assert "applyViewerTitleStyle" in ux


def test_v023_final_card_patterns():
    html = (UI / "index.html").read_text(encoding="utf-8")
    ux = (UI / "ux-titles.js").read_text(encoding="utf-8")
    assert "+ Carton final" in html
    assert "viewerTitleBackdrop" in html
    assert "CARTON FINAL" in ux
    assert "blackTailSeconds" in ux
    assert "canvasBackgroundColor" in ux
    assert "Titre · Ajouter un carton final" in ux
    assert "FIN DE TIMELINE" in ux
    assert "Carton final ajouté · texte à personnaliser" in ux



def test_v023_graphical_connection_point_patterns():
    ux = (UI / "ux-magnetic.js").read_text(encoding="utf-8")
    css = (UI / "style.css").read_text(encoding="utf-8")
    assert "connectionPointOffset" in ux
    assert "renderConnectionPoints" in ux
    assert "beginConnectionPointDrag" in ux
    assert "Point sur parent (s)" in ux
    assert "Appliquer le point" in ux
    assert "Point de connexion déplacé" in ux
    assert ".connection-overlay" in css
    assert ".connection-line.selected" in css
    assert ".connection-point.selected" in css



def test_v0234_delivery_center_patterns():
    ux = (UI / "ux-delivery.js").read_text(encoding="utf-8")
    html = (UI / "index.html").read_text(encoding="utf-8")
    css = (UI / "style.css").read_text(encoding="utf-8")
    assert "Delivery Center" in ux
    assert "Festival / social" in ux
    assert "FILL · plein cadre avec crop" in ux
    assert "Autoriser explicitement le crop centré" in ux
    assert "Préflight" in ux or "PRÉFLIGHT" in ux
    assert "Exporter avec avertissements" in ux
    assert "Télécharger le livrable" in ux
    assert "Delivery · Festival / social" in ux
    assert 'onclick="openDeliveryCenter()"' in html
    assert '/ui/ux-delivery.js' in html
    assert ".delivery-preflight-head" in css
    assert ".delivery-crop-estimate" in css



def test_v0235_delivery_preset_patterns():
    ux = (UI / "ux-delivery.js").read_text(encoding="utf-8")
    css = (UI / "style.css").read_text(encoding="utf-8")
    assert "V0.23.5 · DELIVERY" in ux
    assert "PRESET PERSONNALISÉ" in ux
    assert "Dupliquer" in ux
    assert "Définir par défaut" in ux
    assert "Enregistrer le preset" in ux
    assert "Exporter JSON" in ux
    assert "Importer JSON" in ux
    assert "Preset intégré immuable" in ux
    assert "24,30,60" not in ux or "deliveryPresetFps" in ux
    assert ".delivery-preset-editor" in css
    assert ".delivery-preset-head" in css
