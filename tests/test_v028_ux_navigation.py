from pathlib import Path

ROOT = Path(__file__).parents[1]
UI = ROOT / "piste_studio" / "ui"


def read(name: str) -> str:
    return (UI / name).read_text(encoding="utf-8")


def test_v028_contextual_design_tokens_and_controls():
    css = read("style.css")
    html = read("index.html")

    for token in (
        "--domain-video",
        "--domain-audio",
        "--domain-transcript",
        "--domain-editorial",
        "--domain-delivery",
        "--context-accent",
    ):
        assert token in css

    assert 'id="contextDomainChip"' in html
    assert 'id="helpModeBtn"' in html
    assert 'id="preferencesBtn"' in html
    assert 'id="universalSearchBtn"' in html
    assert 'id="contextQuickActions"' in html
    assert 'id="actionStateBadge"' in html


def test_v028_contextual_help_is_optional_and_persisted():
    help_js = read("ux-help.js")
    prefs_js = read("ux-preferences.js")
    state = read("state.js")

    assert '"guided"' in help_js
    assert '"minimal"' in help_js
    assert '"off"' in help_js
    assert "piste.ui.helpMode" in help_js
    assert "openHelpCenterBtn" in help_js
    assert "openResourcesBtn" in help_js

    assert "piste.ui.density" in prefs_js
    assert "piste.ui.contextColors" in prefs_js
    assert "piste.ui.contextActions" in prefs_js
    assert 'helpMode: "guided"' in state
    assert 'uiDensity: "comfortable"' in state


def test_v028_universal_search_covers_actions_menus_help_and_resources():
    search = read("ux-universal-search.js")
    html = read("index.html")

    assert 'kind:"action"' in search
    assert 'kind:"goto"' in search
    assert 'kind:"help"' in search
    assert 'kind:"resource"' in search
    assert "Espace · Review" in search
    assert "Production · Readiness" in search
    assert "Aide · VO vers image" in search
    assert "Ressource · Glossaire PISTE" in search

    assert 'data-command-filter="action"' in html
    assert 'data-command-filter="goto"' in html
    assert 'data-command-filter="help"' in html
    assert 'data-command-filter="resource"' in html


def test_v028_context_controller_keeps_color_secondary_to_text():
    context = read("ux-context.js")
    css = read("style.css")

    assert "LABELS" in context
    assert "VIDEO" in context
    assert "AUDIO" in context
    assert "TRANSCRIPT" in context
    assert "EDITORIAL" in context
    assert "DELIVERY" in context

    # Color is accompanied by visible labels/dots and can be neutralized.
    assert ".context-chip" in css
    assert "body[data-context-colors=\"off\"]" in css
    assert "body[data-context-actions=\"off\"]" in css
