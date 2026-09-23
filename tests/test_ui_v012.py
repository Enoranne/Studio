from pathlib import Path
from fastapi.testclient import TestClient
from piste_studio.app import create_app
from piste_studio.project import init_project

ROOT = Path(__file__).parents[1]
UI = ROOT / 'piste_studio' / 'ui'


def test_v012_ui_structure_and_assets(tmp_path):
    root = tmp_path / 'Project'
    init_project(root, 'UI Test')
    app = create_app(root, UI / 'index.html')
    client = TestClient(app)
    html = client.get('/').text
    assert 'PISTE Studio — Local App v0.12' in html
    assert 'data-workspace="assemble"' in html
    assert 'data-workspace="edit"' in html
    assert 'data-workspace="review"' in html
    assert 'data-monitor="source"' in html
    assert 'data-monitor="program"' in html
    assert 'id="timelineIndex"' in html
    assert 'id="browserPanel"' in html
    assert 'id="inspectorPanel"' in html
    for asset in ('style.css','editor.js','ux-browser.js','ux-timeline.js','ux-shell.js','backend.js'):
        r = client.get(f'/ui/{asset}')
        assert r.status_code == 200
        assert len(r.content) > 100


def test_ux_has_reference_patterns_without_claiming_true_magnetic_timeline():
    ux = ''.join((UI / name).read_text(encoding='utf-8') for name in ('ux-browser.js','ux-timeline.js','ux-shell.js'))
    html = (UI / 'index.html').read_text(encoding='utf-8')
    assert 'setViewerMode' in ux
    assert 'markRange' in ux
    assert 'renderIndex' in ux
    assert 'setWorkspace' in ux
    assert 'Storyline principale' in html
    assert 'Storyline magnétique' not in html
