from pathlib import Path
import re
import socket
import threading
import time

import uvicorn
from playwright.sync_api import expect, sync_playwright

from piste_studio.app import create_app
import piste_studio.app as app_module
from piste_studio.project import init_project
from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.media_intelligence import _write_analysis
from piste_studio.semantic_vision import store_semantic_profile, store_targeted_semantic_reference
from piste_studio.audio_intelligence import _write_analysis as _write_audio_loudness
from piste_studio.timeline import save_timeline
from piste_studio.versioning import create_timeline_version
from piste_studio.config import read_yaml, write_yaml


def _free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def test_real_browser_navigation_and_workspaces(tmp_path, monkeypatch):
    root = tmp_path / "Project"
    init_project(root, "Browser Test")
    (root / "rushes" / "malo_a.mp4").write_bytes(b"fake-a")
    (root / "rushes" / "malo_b.mp4").write_bytes(b"fake-b")
    (root / "audio" / "voice.wav").write_bytes(b"fake-audio")
    (root / "audio" / "music_a.wav").write_bytes(b"fake-music-a")
    (root / "audio" / "music_b.wav").write_bytes(b"fake-music-b")
    scan_media(root)
    rows = fetch_media_with_metadata(root)
    videos = [row for row in rows if row["kind"] == "video"]
    audios = {
        Path(row["relative_path"]).name: row
        for row in rows if row["kind"] == "audio"
    }
    audio = audios["voice.wav"]
    music_a = audios["music_a.wav"]
    music_b = audios["music_b.wav"]
    for index, row in enumerate(videos):
        tags = ["malo", "enfance"]
        if index == 0:
            tags += ["character:malo", "prop:fisher", "decor:salon"]
        set_media_metadata(
            root,
            row["id"],
            title=Path(row["relative_path"]).stem,
            duration_seconds=8.0,
            rating=4,
            tags=tags,
        )
    canon = read_yaml(root / "canon.yaml")
    canon["characters"] = {"malo": {"age": 6}}
    canon["semantic"] = {
        "allowed_tags": [],
        "forbidden_tags": ["prop:fisher"],
        "closed_facets": [],
    }
    write_yaml(root / "canon.yaml", canon)
    set_media_metadata(
        root,
        audio["id"],
        title="Voice",
        duration_seconds=8.0,
        tags=["voice", "malo"],
    )
    for music, title in ((music_a, "Music A"), (music_b, "Music B")):
        set_media_metadata(
            root,
            music["id"],
            title=title,
            duration_seconds=8.0,
            tags=["music"],
        )
    _write_audio_loudness(
        root,
        audio["id"],
        status="READY",
        integrated_lufs=-20.0,
        true_peak_dbfs=-4.0,
        loudness_range_lu=4.5,
        threshold_lufs=-30.0,
        silence=[{"start": 1.0, "end": 1.5, "duration": 0.5}],
    )
    cache = root / "cache" / "filmstrips"
    cache.mkdir(parents=True, exist_ok=True)
    for index, row in enumerate(
        [x for x in fetch_media_with_metadata(root) if x["kind"] == "video"],
        start=1,
    ):
        strip = cache / f"browser_{index}.jpg"
        strip.write_bytes(b"\xff\xd8\xff\xd9")
        _write_analysis(
            root,
            row["id"],
            status="READY",
            technical={
                "width": 1280,
                "height": 720,
                "fps": 24.0,
                "video_codec": "h264",
                "filename_tokens": ["malo"],
            },
            signature=["ffffffffffffffffffffffffffffffffffff"] * 6,
            filmstrip_path=strip.relative_to(root).as_posix(),
        )
        store_semantic_profile(
            root,
            row["id"],
            embedding=[1.0, 0.01 * index, 0.0],
            frame_count=4,
        )
    save_timeline(
        root,
        {
            "edit_name": "teaser_30",
            "duration_seconds": 30,
            "storyline": {"mode": "free", "start": 3},
            "tracks": [
                {"id": "video", "name": "VIDEO", "kind": "video"},
                {"id": "titles", "name": "TITLES", "kind": "title"},
                {"id": "vo", "name": "VO", "kind": "audio"},
                {"id": "music", "name": "MUSIC", "kind": "music"},
                {"id": "sfx", "name": "SFX", "kind": "sfx"},
            ],
            "clips": [
                {
                    "id": "v1",
                    "track": "video",
                    "label": "Malo A",
                    "start": 3,
                    "duration": 4,
                    "sourceStart": 0,
                    "mediaDbId": videos[0]["id"],
                },
                {
                    "id": "a1",
                    "track": "vo",
                    "label": "Voice",
                    "start": 5,
                    "duration": 2,
                    "sourceStart": 0,
                    "audioDbId": audio["id"],
                    "gainDb": -6,
                    "pan": 0,
                    "audioRole": "vo",
                    "fadeIn": 0.4,
                    "fadeOut": 0.5,
                    "volumeEnvelope": [],
                },
                {
                    "id": "m1",
                    "track": "music",
                    "label": "Music A",
                    "start": 3,
                    "duration": 5,
                    "sourceStart": 0,
                    "audioDbId": music_a["id"],
                    "gainDb": -6,
                    "pan": 0,
                    "audioRole": "music",
                    "fadeIn": 0.2,
                    "fadeOut": 0.2,
                    "volumeEnvelope": [],
                },
                {
                    "id": "m2",
                    "track": "music",
                    "label": "Music B",
                    "start": 8,
                    "duration": 4,
                    "sourceStart": 0,
                    "audioDbId": music_b["id"],
                    "gainDb": -6,
                    "pan": 0,
                    "audioRole": "music",
                    "fadeIn": 0.2,
                    "fadeOut": 0.2,
                    "volumeEnvelope": [],
                },
            ],
        },
    )
    master_report = root / "reports" / "audio" / "teaser_30_master_check.json"
    master_report.parent.mkdir(parents=True, exist_ok=True)
    master_report.write_text('{"evaluation":{"status":"PASS"}}\n', encoding="utf-8")
    def fake_targeted_reference_create(
        root,
        media_id,
        *,
        tag,
        timestamp_seconds,
        roi=None,
        **kwargs,
    ):
        image = root / "cache" / "vision" / "references" / "browser_targeted.jpg"
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"jpeg")
        return store_targeted_semantic_reference(
            root,
            media_id,
            tag=tag,
            timestamp_seconds=timestamp_seconds,
            roi=roi,
            embedding=[1.0, 0.0, 0.0],
            image_path=image,
            group_name=kwargs.get("group_name"),
            quality=kwargs.get("quality", "secondary"),
        )

    monkeypatch.setattr(
        app_module,
        "create_targeted_semantic_reference",
        fake_targeted_reference_create,
    )

    monkeypatch.setattr(
        app_module,
        "suggest_editorial_windows",
        lambda root, media_id, **kwargs: {
            "version": "0.22-scenes-1",
            "media_id": media_id,
            "relative_path": "rushes/malo_a.mp4",
            "duration_seconds": 8.0,
            "scene_threshold": float(kwargs.get("threshold", 0.32)),
            "scene_changes": [2.0, 5.0],
            "candidates": [
                {
                    "rank": 1,
                    "source_in": 0.0,
                    "source_out": 2.0,
                    "duration": 2.0,
                    "boundary_before": None,
                    "boundary_after": 2.0,
                    "reason": "Début du rush → rupture visuelle à 2.00 s.",
                    "method": "ffmpeg_scene_change",
                    "scene_threshold": float(kwargs.get("threshold", 0.32)),
                },
                {
                    "rank": 2,
                    "source_in": 2.0,
                    "source_out": 5.0,
                    "duration": 3.0,
                    "boundary_before": 2.0,
                    "boundary_after": 5.0,
                    "reason": "Segment entre ruptures visuelles à 2.00 s et 5.00 s.",
                    "method": "ffmpeg_scene_change",
                    "scene_threshold": float(kwargs.get("threshold", 0.32)),
                },
                {
                    "rank": 3,
                    "source_in": 5.0,
                    "source_out": 8.0,
                    "duration": 3.0,
                    "boundary_before": 5.0,
                    "boundary_after": None,
                    "reason": "Rupture visuelle à 5.00 s → fin du rush.",
                    "method": "ffmpeg_scene_change",
                    "scene_threshold": float(kwargs.get("threshold", 0.32)),
                },
            ],
            "policy": {
                "suggestion_only": True,
                "automatic_storyline_edit": False,
                "human_validation_required": True,
                "local_processing": True,
            },
        },
    )

    monkeypatch.setattr(
        app_module,
        "run_master_check",
        lambda root, timeline, **kwargs: {
            "version": "0.21-master-1",
            "edit_name": "teaser_30",
            "preset": {
                "id": "online_reference",
                "label": "Online stéréo · repère",
                "target_lufs": -16.0,
                "true_peak_ceiling": -1.0,
                "loudness_tolerance_lu": 1.0,
                "reference_only": True,
            },
            "measurement": {
                "integrated_lufs": -16.2,
                "true_peak_dbfs": -1.3,
                "loudness_range_lu": 5.0,
                "threshold_lufs": -27.0,
            },
            "evaluation": {
                "status": "PASS",
                "loudness_ok": True,
                "true_peak_ok": True,
                "loudness_delta_lu": -0.2,
                "reasons": [],
            },
            "render": {
                "relative_path": "cache/audio_delivery/teaser_30_master_check.wav",
                "duration_seconds": 30,
                "clip_count": 3,
                "limiter_enabled": bool(kwargs.get("limiter", False)),
            },
            "policy": {
                "measured_after_sum": True,
                "reference_presets_not_universal_standards": True,
                "automatic_normalization": False,
                "automatic_limiter": False,
                "limiter_requires_explicit_choice": True,
                "source_media_immutable": True,
            },
            "report_relative_path": master_report.relative_to(root).as_posix(),
            "report_name": master_report.name,
        },
    )

    app = create_app(root)
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started

    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
            page.wait_for_timeout(150)
            assert errors == [], f"JavaScript page errors on load: {errors}"

            expect(page.locator("#view-edit")).to_have_class(re.compile("active"))
            expect(page.locator(".filmstrip-cache")).to_have_count(2)
            expect(page.locator(".badge.intelligence")).to_have_count(2)

            page.get_by_role("button", name="Canon & Locks").click()
            expect(page.locator("#view-canon")).to_have_class(re.compile("active"))

            page.get_by_role("button", name="Versions").click()
            expect(page.locator("#view-versions")).to_have_class(re.compile("active"))

            page.get_by_role("button", name="Montage").click()
            expect(page.locator("#view-edit")).to_have_class(re.compile("active"))

            page.locator('[data-workspace="assemble"]').click()
            expect(page.locator("body")).to_have_class(re.compile("workspace-assemble"))

            page.locator('[data-workspace="review"]').click()
            expect(page.locator("body")).to_have_class(re.compile("workspace-review"))

            page.locator('[data-workspace="edit"]').click()
            expect(page.locator("body")).to_have_class(re.compile("workspace-edit"))

            expect(page.locator("#undoBtn")).to_be_visible()

            viewer_before = page.locator("#viewer").bounding_box()
            assert viewer_before is not None

            page.locator('[data-focus-pane="viewer"]').click()
            expect(page.locator("body")).to_have_class(re.compile("focus-viewer"))
            expect(page.locator("#focusExit")).to_be_visible()
            viewer_focus = page.locator("#viewer").bounding_box()
            assert viewer_focus is not None
            assert viewer_focus["height"] > viewer_before["height"]

            page.keyboard.press("Escape")
            expect(page.locator("body")).not_to_have_class(re.compile("focus-viewer"))

            page.locator("#overlayBtn").click()
            expect(page.locator("#overlayMenu")).to_be_visible()
            page.locator("#overlayHud").uncheck()
            expect(page.locator("#viewer")).to_have_class(re.compile("hide-hud"))
            page.locator("#overlayHud").check()
            expect(page.locator("#viewer")).not_to_have_class(re.compile("hide-hud"))
            page.keyboard.press("Escape")
            expect(page.locator("#overlayMenu")).to_be_hidden()

            page.keyboard.press("Control+K")
            expect(page.locator("#commandPalette")).to_be_visible()
            page.locator("#commandSearch").fill("Espace · Review")
            page.keyboard.press("Enter")
            expect(page.locator("#commandPalette")).to_be_hidden()
            expect(page.locator("body")).to_have_class(re.compile("workspace-review"))

            page.locator('[data-workspace="edit"]').click()
            expect(page.locator("body")).to_have_class(re.compile("workspace-edit"))

            page.locator("#readinessBtn").click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator("#editorialDrawerTitle")).to_have_text("Production Readiness")
            expect(page.locator(".readiness-capability")).to_have_count(4)
            expect(page.locator("#editorialDrawer")).to_contain_text("PROCHAINE ACTION")
            page.locator("#editorialDrawer .pane-close").click()
            expect(page.locator("#editorialDrawer")).to_be_hidden()

            page.keyboard.press("Control+K")
            expect(page.locator("#commandPalette")).to_be_visible()
            page.locator("#commandSearch").fill("Production · Readiness")
            page.keyboard.press("Enter")
            expect(page.locator("#commandPalette")).to_be_hidden()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator("#editorialDrawerTitle")).to_have_text("Production Readiness")
            page.locator("#editorialDrawer .pane-close").click()
            expect(page.locator("#editorialDrawer")).to_be_hidden()

            page.locator("#addMarkerBtn").click()
            expect(page.locator("#markerComposer")).to_be_visible()
            page.locator("#markerLabel").fill("Décision test")
            page.locator("#markerKind").select_option("decision")
            page.locator("#markerSaveBtn").click()
            expect(page.locator("#markerComposer")).to_be_hidden()
            expect(page.locator(".editorial-marker")).to_have_count(1)

            page.locator(".media-row").first.click()
            expect(page.locator(".editorial-inspector-section")).to_be_visible()
            expect(page.locator(".media-intelligence-section")).to_be_visible()

            page.get_by_role("button", name="Fenêtres IN/OUT").click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator(".selector-policy")).to_contain_text("RUPTURES VISUELLES")
            expect(page.locator(".editorial-window-card")).to_have_count(3)
            expect(page.locator("#visualWindowSensitivity")).to_have_value("normal")
            page.locator(".editorial-window-card").first.get_by_role(
                "button", name="Charger IN/OUT"
            ).click()
            expect(page.locator("#mi")).to_have_value("0")
            expect(page.locator("#mo")).to_have_value("2")
            page.locator("#editorialDrawer .pane-close").click()
            expect(page.locator("#editorialDrawer")).to_be_hidden()

            page.get_by_role("button", name="Prises proches").click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator(".suggestion-card")).to_have_count(1)
            expect(page.locator(".selector-policy")).to_contain_text("Indice local")
            page.locator("#editorialDrawer .pane-close").click()
            expect(page.locator("#editorialDrawer")).to_be_hidden()

            page.get_by_role("button", name="Alternatives").click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator(".suggestion-card")).to_have_count(1)
            expect(page.locator(".selector-policy")).to_contain_text("Validation humaine")
            page.get_by_role("button", name="Prévisualiser").click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            page.locator("#editorialDrawer .pane-close").click()
            expect(page.locator("#editorialDrawer")).to_be_hidden()

            page.locator(".media-row").nth(1).click()
            expect(page.locator(".semantic-vision-section")).to_be_visible()
            expect(page.locator(".vision-state.ready")).to_be_visible()

            page.get_by_role("button", name="Référence ciblée").click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator(".selector-policy")).to_contain_text("RÉFÉRENCE CIBLÉE")
            page.locator("#targetedReferenceFacet").select_option("prop")
            page.locator("#targetedReferenceValue").fill("fisher")
            page.locator("#targetedReferenceGroup").fill("Fisher principal")
            page.locator("#targetedReferenceQuality").select_option("primary")
            page.locator("#targetedReferenceMode").select_option("roi")
            expect(page.locator("#targetedRoiFields")).to_be_visible()
            page.locator("#targetedRoiX").fill("15")
            page.locator("#targetedRoiY").fill("20")
            page.locator("#targetedRoiW").fill("50")
            page.locator("#targetedRoiH").fill("40")
            page.get_by_role("button", name="Créer la référence").click()
            expect(page.locator(".targeted-reference-card")).to_have_count(1)
            expect(page.locator(".targeted-reference-card")).to_contain_text("prop:fisher")
            expect(page.locator(".targeted-reference-card")).to_contain_text("zone 15%, 20%")
            expect(page.locator(".targeted-reference-card")).to_contain_text("Groupe · Fisher principal")
            expect(page.locator(".targeted-reference-card")).to_contain_text("Primaire")
            expect(page.locator(".semantic-resolved")).to_contain_text("Fisher principal")
            page.locator(".targeted-reference-card input").fill("Fisher secondaire")
            page.locator(".targeted-reference-card select").select_option("low")
            page.get_by_role("button", name="Enregistrer groupe/qualité").click()
            expect(page.locator(".targeted-reference-card")).to_contain_text("Groupe · Fisher secondaire")
            expect(page.locator(".targeted-reference-card")).to_contain_text("Faible")
            page.locator("#editorialDrawer .pane-close").click()
            expect(page.locator("#editorialDrawer")).to_be_hidden()
            expect(page.locator("#inspector")).not_to_contain_text("prop:fisher")

            page.get_by_role("button", name="Proposer continuité").click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator(".semantic-proposal-card")).to_have_count(3)

            fisher_card = page.locator(".semantic-proposal-card").filter(
                has_text="prop:fisher"
            )
            expect(fisher_card).to_contain_text("CONFLIT CANON")
            expect(fisher_card.get_by_role("button", name="Examiner conflit")).to_be_visible()
            fisher_card.get_by_role("button", name="Examiner conflit").click()
            expect(page.locator("#editorialDrawerTitle")).to_contain_text("Conflit Canon")
            expect(page.locator("#editorialDrawer")).to_contain_text("explicitement interdit")
            expect(page.locator("#inspector")).not_to_contain_text("prop:fisher")
            page.get_by_role("button", name="Accepter malgré conflit").click()
            expect(page.locator("#inspector")).to_contain_text("prop:fisher")

            character_card = page.locator(".semantic-proposal-card").filter(
                has_text="character:malo"
            )
            expect(character_card).to_be_visible()
            expect(character_card).to_contain_text("CANON ALIGNÉ")
            character_card.get_by_role("button", name="Accepter").click()
            expect(page.locator("#inspector")).to_contain_text("character:malo")
            page.locator("#editorialDrawer .pane-close").click()
            expect(page.locator("#editorialDrawer")).to_be_hidden()

            expect(page.locator("#audioMeters")).to_be_visible()
            page.locator('.clip[data-clip="a1"]').click()
            page.wait_for_timeout(80)
            assert errors == [], f"Audio inspector page errors: {errors}"
            expect(page.locator(".audio-mix-section")).to_be_visible()
            expect(page.locator("#gainDbInput")).to_have_value("-6.0")
            expect(page.locator('.clip[data-clip="a1"] .fade-in-grip')).to_be_visible()
            expect(page.locator('.clip[data-clip="a1"] .fade-out-grip')).to_be_visible()

            page.locator("#gainDbInput").fill("3")
            page.get_by_role("button", name="Appliquer PATCH").click()
            expect(page.locator('.clip[data-clip="a1"] small')).to_contain_text("+3.0 dB")

            page.get_by_role("button", name="+ Point au playhead").click()
            expect(page.locator('.clip[data-clip="a1"] .automation-point')).to_have_count(1)

            vo_track = page.locator("#lane-vo").locator("..")
            vo_track.locator(".solo-btn").click()
            expect(vo_track.locator(".solo-btn")).to_have_class(re.compile("on"))

            expect(page.locator(".audio-intelligence-section")).to_be_visible()
            expect(page.locator(".audio-intelligence-section")).to_contain_text("-20.0 LUFS")
            expect(page.locator(".audio-intelligence-section")).to_contain_text("-4.0 dBTP")
            page.get_by_role("button", name="Normaliser").click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator(".loudness-proposal")).to_contain_text("+2.50 dB")
            expect(page.locator(".loudness-proposal")).to_contain_text("limité par le ceiling true peak")
            page.locator("#editorialDrawer").get_by_role("button", name="Accepter").click()
            expect(page.locator("#editorialDrawer")).to_be_hidden()
            expect(page.locator('.clip[data-clip="a1"] small')).to_contain_text("+5.5 dB")

            page.get_by_role("button", name="Clipping").click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator(".selector-policy")).to_contain_text("ESTIMATION PAR CLIP")
            page.locator("#editorialDrawer .pane-close").click()

            page.locator('.clip[data-clip="m1"]').click()
            expect(page.locator(".audio-intelligence-section")).to_be_visible()
            page.get_by_role("button", name="Ducking VO").click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator("#editorialDrawer")).to_contain_text("Voice")
            page.locator("#editorialDrawer").get_by_role("button", name="Accepter").click()
            expect(page.locator("#editorialDrawer")).to_be_hidden()
            expect(page.locator('.clip[data-clip="m1"] .automation-point')).to_have_count(4)

            page.get_by_role("button", name="Crossfade suivant").click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator("#editorialDrawer")).to_contain_text("0.50 s")
            page.locator("#editorialDrawer").get_by_role("button", name="Accepter").click()
            expect(page.locator("#editorialDrawer")).to_be_hidden()
            expect(page.locator(".crossfade-badge")).to_have_count(2)

            page.keyboard.press("Control+K")
            expect(page.locator("#commandPalette")).to_be_visible()
            page.locator("#commandSearch").fill("Audio · Master Check")
            page.keyboard.press("Enter")
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator("#editorialDrawer")).to_contain_text("MASTER RENDU")
            expect(page.locator("#masterLimiter")).not_to_be_checked()
            page.get_by_role("button", name="Mesurer le master").click()
            expect(page.locator("#masterCheckResult")).to_contain_text("PASS")
            expect(page.locator("#masterCheckResult")).to_contain_text("-16.2 LUFS")
            expect(page.locator("#masterCheckResult")).to_contain_text("-1.3 dBTP")
            expect(page.locator("#mixMeter")).to_contain_text("MASTER")
            expect(page.get_by_role("link", name="Télécharger le rapport JSON")).to_be_visible()
            page.locator("#editorialDrawer .pane-close").click()
            expect(page.locator("#editorialDrawer")).to_be_hidden()

            page.evaluate("""
                openAudioExportAdvisory({
                    status: 'STALE',
                    can_export: true,
                    previous_status: 'PASS',
                    message: 'Le mix audio a changé depuis le dernier Master Check.',
                    reasons: ['Relancer le Master Check est recommandé avant livraison.'],
                    measurement: {integrated_lufs: -16.2, true_peak_dbfs: -1.3}
                })
            """)
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator("#editorialDrawer")).to_contain_text("STALE")
            expect(page.get_by_role("button", name="Lancer Master Check")).to_be_visible()
            expect(page.get_by_role("button", name="Exporter quand même")).to_be_visible()
            expect(page.locator("#editorialDrawer")).to_contain_text("Export non bloqué")

            assert errors == []
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)



def test_timeline_neighbor_continuity_drawer_and_candidate_simulation(tmp_path):
    root = tmp_path / "ContinuityBrowser"
    init_project(root, "Continuity Browser")
    for name in ("prev.mp4", "target.mp4", "next.mp4", "candidate.mp4"):
        (root / "rushes" / name).write_bytes(name.encode("utf-8"))
    scan_media(root)
    rows = {
        Path(row["relative_path"]).name: row
        for row in fetch_media_with_metadata(root)
        if row["kind"] == "video"
    }
    for name in ("prev.mp4", "target.mp4", "next.mp4"):
        set_media_metadata(
            root,
            rows[name]["id"],
            title=name.replace(".mp4", "").title(),
            duration_seconds=8,
            tags=["character:malo", "prop:fisher", "decor:salon", "look:warm"],
        )
    set_media_metadata(
        root,
        rows["candidate.mp4"]["id"],
        title="Candidate Ronan",
        duration_seconds=8,
        tags=["character:ronan", "prop:radio", "decor:cuisine", "look:cold"],
    )
    save_timeline(
        root,
        {
            "edit_name": "teaser_30",
            "duration_seconds": 20,
            "storyline": {"mode": "free", "start": 0},
            "tracks": [{"id": "video", "name": "VIDEO", "kind": "video"}],
            "clips": [
                {"id": "v1", "track": "video", "label": "Prev", "start": 0, "duration": 4, "sourceStart": 0, "mediaDbId": rows["prev.mp4"]["id"]},
                {"id": "v2", "track": "video", "label": "Target", "start": 4, "duration": 4, "sourceStart": 0, "mediaDbId": rows["target.mp4"]["id"]},
                {"id": "v3", "track": "video", "label": "Next", "start": 8, "duration": 4, "sourceStart": 0, "mediaDbId": rows["next.mp4"]["id"]},
            ],
        },
    )

    app = create_app(root)
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started

    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
            page.wait_for_timeout(150)

            page.evaluate("selectedClip='v2'; renderInspector();")
            expect(page.locator(".timeline-continuity-section")).to_be_visible()
            page.get_by_role("button", name="Analyser voisins").click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator(".selector-policy")).to_contain_text("CONTINUITÉ")
            expect(page.locator(".continuity-neighbor")).to_have_count(3)
            expect(page.locator("#editorialDrawer")).to_contain_text("PRÉCÉDENT")
            expect(page.locator("#editorialDrawer")).to_contain_text("SUIVANT")
            expect(page.locator("#editorialDrawer")).to_contain_text("BRIDGE_CONTINUITY")

            page.locator("#continuityCandidateMedia").select_option(
                str(rows["candidate.mp4"]["id"])
            )
            page.get_by_role("button", name="Tester ce candidat").click()
            expect(page.locator(".selector-policy")).to_contain_text("RUPTURE POTENTIELLE")
            expect(page.locator("#editorialDrawer")).to_contain_text("Candidate Ronan")
            expect(page.locator("#editorialDrawer")).to_contain_text("FACET_RUPTURE")
            expect(page.locator("#editorialDrawer")).to_contain_text("BRIDGE_EVIDENCE_GAP")

            timeline = (root / "edits" / "teaser_30" / "working" / "timeline.json").read_text(encoding="utf-8")
            assert '"mediaDbId": ' + str(rows["target.mp4"]["id"]) in timeline
            assert errors == []
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)



def test_editable_title_overlay_preview_and_persistence(tmp_path):
    root = tmp_path / "TitleBrowser"
    init_project(root, "Title Browser")
    (root / "rushes" / "shot.mp4").write_bytes(b"fake-video")
    scan_media(root)
    video = next(
        x for x in fetch_media_with_metadata(root)
        if x["kind"] == "video"
    )
    set_media_metadata(
        root,
        video["id"],
        title="Shot",
        duration_seconds=8,
        tags=[],
    )
    save_timeline(
        root,
        {
            "edit_name": "teaser_30",
            "duration_seconds": 12,
            "storyline": {"mode": "free", "start": 0},
            "tracks": [
                {"id": "video", "name": "VIDEO", "kind": "video"},
                {"id": "titles", "name": "TITLES", "kind": "title"},
            ],
            "clips": [
                {
                    "id": "v1",
                    "track": "video",
                    "label": "Shot",
                    "start": 0,
                    "duration": 8,
                    "sourceStart": 0,
                    "mediaDbId": video["id"],
                },
                {
                    "id": "t1",
                    "track": "titles",
                    "label": "PISTE 0",
                    "text": "PISTE 0",
                    "start": 2,
                    "duration": 3,
                    "titlePreset": "center",
                    "fontFamily": "sans",
                    "fontSize": 64,
                    "fontWeight": 700,
                    "textAlign": "center",
                    "positionX": 0.5,
                    "positionY": 0.5,
                    "boxWidth": 0.8,
                    "color": "#FFFFFF",
                    "backgroundColor": "#000000",
                    "backgroundOpacity": 0,
                    "opacity": 1,
                    "padding": 0.02,
                    "cornerRadius": 0,
                },
            ],
        },
    )

    app = create_app(root)
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started

    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
            page.wait_for_timeout(150)

            page.locator('[data-clip="t1"]').click()
            expect(page.locator(".title-style-section")).to_be_visible()
            expect(page.locator("#viewerTitle")).to_have_class(re.compile("show"))
            expect(page.locator("#viewerTitle")).to_have_text("PISTE 0")

            page.locator("#titleText").fill("PISTE 0\nBONUS TRACK")
            page.locator("#titlePreset").select_option("lower_third")
            page.locator("#titleFontFamily").select_option("serif")
            page.locator("#titleFontSize").fill("90")
            page.locator("#titleTextAlign").select_option("left")
            page.locator("#titleColor").fill("#ffcc88")
            page.locator("#titleBackgroundOpacity").fill("50")
            page.locator("#titlePadding").fill("3")
            page.locator("#titleCornerRadius").fill("2")
            page.locator("#inspector").get_by_role(
                "button", name="Appliquer PATCH"
            ).click()

            expect(page.locator("#viewerTitle")).to_have_text(
                "PISTE 0\nBONUS TRACK"
            )
            style = page.locator("#viewerTitle").get_attribute("style") or ""
            assert "top: 82%" in style
            assert "Georgia" in style
            assert "text-align: left" in style
            assert "rgb(255, 204, 136)" in style or "#ffcc88" in style.lower()

            page.locator("#saveBackendBtn").click()
            page.wait_for_timeout(100)
            timeline = (
                root
                / "edits"
                / "teaser_30"
                / "working"
                / "timeline.json"
            )
            saved = __import__("json").loads(timeline.read_text(encoding="utf-8"))
            title = next(x for x in saved["clips"] if x["id"] == "t1")
            assert saved["schema_version"] == 6
            assert title["text"] == "PISTE 0\nBONUS TRACK"
            assert title["titlePreset"] == "lower_third"
            assert title["fontFamily"] == "serif"
            assert title["fontSize"] == 90.0
            assert title["textAlign"] == "left"
            assert title["positionY"] == 0.82
            assert title["color"] == "#FFCC88"
            assert title["backgroundOpacity"] == 0.5
            assert title["padding"] == 0.03
            assert title["cornerRadius"] == 0.02

            page.get_by_role("button", name="+ Carton final").click()
            expect(page.locator(".title-style-section")).to_be_visible()
            expect(page.locator(".title-style-section")).to_contain_text("CARTON FINAL")
            expect(page.locator("#viewerTitleBackdrop")).to_have_class(re.compile("show"))
            expect(page.locator("#viewerTitle")).to_have_text("Carton final")

            page.locator("#titleText").fill("FIN")
            page.locator("#titleCanvasBackgroundColor").fill("#030201")
            page.locator("#titleCanvasBackgroundOpacity").fill("100")
            page.locator("#titleBlackTailSeconds").fill("0.8")
            page.locator("#inspector").get_by_role(
                "button", name="Appliquer PATCH"
            ).click()

            final_card = page.evaluate(
                "() => { const c=getClip(selectedClip); return {id:c.id,start:c.start,duration:c.duration,tail:c.blackTailSeconds}; }"
            )
            assert abs(final_card["start"] + final_card["duration"] - 12.0) < 1e-6
            page.evaluate(
                "(t) => setPlayhead(t)",
                final_card["start"] + final_card["duration"] - 0.4,
            )
            expect(page.locator("#viewerTitleBackdrop")).to_have_class(re.compile("show"))
            expect(page.locator("#viewerTitle")).not_to_have_class(re.compile("show"))

            page.locator("#saveBackendBtn").click()
            page.wait_for_timeout(100)
            saved = __import__("json").loads(timeline.read_text(encoding="utf-8"))
            card = next(x for x in saved["clips"] if x["id"] == final_card["id"])
            assert card["titleRole"] == "final_card"
            assert card["text"] == "FIN"
            assert card["canvasBackgroundColor"] == "#030201"
            assert card["canvasBackgroundOpacity"] == 1.0
            assert card["blackTailSeconds"] == 0.8
            assert abs(card["start"] + card["duration"] - 12.0) < 1e-6
            assert errors == []
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)



def test_graphical_connection_point_drag_changes_parent_without_moving_child(tmp_path):
    root = tmp_path / "ConnectionPointBrowser"
    init_project(root, "Connection Point Browser")
    save_timeline(
        root,
        {
            "edit_name": "teaser_30",
            "duration_seconds": 30,
            "storyline": {"mode": "magnetic", "start": 0},
            "tracks": [
                {"id": "video", "name": "VIDEO", "kind": "video"},
                {"id": "titles", "name": "TITLES", "kind": "title"},
            ],
            "clips": [
                {
                    "id": "v1",
                    "track": "video",
                    "label": "Plan A",
                    "start": 0,
                    "duration": 5,
                    "sourceStart": 0,
                },
                {
                    "id": "v2",
                    "track": "video",
                    "label": "Plan B",
                    "start": 5,
                    "duration": 5,
                    "sourceStart": 0,
                },
                {
                    "id": "t1",
                    "track": "titles",
                    "label": "Titre connecté",
                    "text": "Titre connecté",
                    "start": 2,
                    "duration": 1,
                    "parentClipId": "v1",
                    "anchorOffset": 2,
                    "connectionPointOffset": 2,
                    "connectionMode": "follow",
                },
            ],
        },
    )

    app = create_app(root)
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started

    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
            page.wait_for_timeout(180)

            page.locator('.clip[data-clip="t1"]').click()
            page.wait_for_timeout(80)
            expect(page.locator(".connection-line")).to_have_count(1)
            expect(page.locator(".connection-point.selected")).to_have_count(1)
            expect(page.locator("#connectionPointInput")).to_have_value("2.00")
            expect(page.locator(".connection-badge")).to_contain_text(
                "Plan A · +2.0s"
            )

            before = page.evaluate(
                "() => { const c=getClip('t1'); return {start:c.start,parent:c.parentClipId,anchor:c.anchorOffset,point:c.connectionPointOffset}; }"
            )
            assert before == {
                "start": 2,
                "parent": "v1",
                "anchor": 2,
                "point": 2,
            }

            handle = page.locator(".connection-point.selected").bounding_box()
            lane = page.locator("#lane-video").bounding_box()
            assert handle is not None and lane is not None
            target_x = lane["x"] + lane["width"] * (6.0 / 30.0)
            target_y = handle["y"] + handle["height"] / 2
            page.mouse.move(
                handle["x"] + handle["width"] / 2,
                target_y,
            )
            page.mouse.down()
            page.mouse.move(target_x, target_y, steps=8)
            page.mouse.up()
            page.wait_for_timeout(220)

            after = page.evaluate(
                "() => { const c=getClip('t1'); return {start:c.start,parent:c.parentClipId,anchor:c.anchorOffset,point:c.connectionPointOffset}; }"
            )
            assert after["start"] == 2
            assert after["parent"] == "v2"
            assert after["anchor"] == -3
            assert abs(after["point"] - 1.0) < 1e-6
            expect(page.locator(".connection-badge")).to_contain_text(
                "Plan B · +1.0s"
            )
            expect(page.locator("#connectionPointInput")).to_have_value("1.00")

            page.locator("#saveBackendBtn").click()
            page.wait_for_timeout(120)
            timeline_path = (
                root
                / "edits"
                / "teaser_30"
                / "working"
                / "timeline.json"
            )
            saved = __import__("json").loads(
                timeline_path.read_text(encoding="utf-8")
            )
            child = next(x for x in saved["clips"] if x["id"] == "t1")
            assert saved["schema_version"] == 6
            assert child["start"] == 2
            assert child["parentClipId"] == "v2"
            assert child["anchorOffset"] == -3
            assert child["connectionPointOffset"] == 1

            page.keyboard.press("Control+Z")
            page.wait_for_timeout(180)
            restored = page.evaluate(
                "() => { const c=getClip('t1'); return {start:c.start,parent:c.parentClipId,point:c.connectionPointOffset}; }"
            )
            assert restored == {"start": 2, "parent": "v1", "point": 2}
            assert errors == []
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)



def test_delivery_center_vertical_crop_preflight_and_export(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "DeliveryBrowser"
    init_project(root, "Delivery Browser")
    timeline_doc = {
        "edit_name": "teaser_30",
        "duration_seconds": 10,
        "storyline": {"mode": "magnetic", "start": 0},
        "tracks": [
            {"id": "video", "name": "VIDEO", "kind": "video"},
        ],
        "clips": [
            {
                "id": "v1",
                "track": "video",
                "label": "Plan",
                "start": 0,
                "duration": 10,
                "sourceStart": 0,
            },
        ],
    }
    save_timeline(root, timeline_doc)
    clean = __import__("json").loads(
        (
            root
            / "edits"
            / "teaser_30"
            / "working"
            / "timeline.json"
        ).read_text(encoding="utf-8")
    )
    version = create_timeline_version(root, clean)
    assert version.version_label == "V001"
    (version.directory / "authoring-plan.json").write_text(
        __import__("json").dumps(
            {
                "deliverable": {
                    "canvas": {"width": 1920, "height": 1080}
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        app_module,
        "master_check_status",
        lambda root_arg, timeline: {
            "status": "PASS",
            "can_export": True,
            "message": "Master Check valide pour le mix courant.",
            "reasons": [],
        },
    )

    def fake_execute_export(
        root_arg,
        edit_name,
        version_name,
        *,
        output_name=None,
        resolution="1080p",
        fps=24,
        format_name="mp4",
    ):
        path = (
            root_arg
            / "edits"
            / edit_name
            / version_name
            / (output_name or "source.mp4")
        )
        path.write_bytes(b"fake-source")
        return path

    def fake_render_delivery(
        root_arg,
        source_path,
        *,
        edit_name,
        version,
        target_id,
        framing_mode=None,
        allow_crop=False,
    ):
        target = app_module.resolve_delivery_target(target_id)
        folder = root_arg / "exports" / edit_name / version
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{edit_name}_{version}_{target_id}.mp4"
        path.write_bytes(b"browser-delivery")
        return {
            "path": path,
            "relative_path": path.relative_to(root_arg).as_posix(),
            "target": target,
            "framing_mode": framing_mode or target["default_framing"],
            "probe": {
                "video_codec": "h264",
                "width": target["width"],
                "height": target["height"],
                "pixel_format": "yuv420p",
                "fps": 24.0,
                "audio_codec": "aac",
                "audio_sample_rate": 48000,
                "audio_channels": 2,
                "duration_seconds": 10.0,
                "size_bytes": path.stat().st_size,
            },
            "conformance": {"status": "PASS", "reasons": []},
            "ffmpeg_args": ["ffmpeg"],
        }

    monkeypatch.setattr(app_module, "execute_export", fake_execute_export)
    monkeypatch.setattr(
        app_module,
        "render_delivery_variant",
        fake_render_delivery,
    )

    app = create_app(root)
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started

    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
            page.wait_for_timeout(160)

            page.get_by_role("button", name="Export", exact=True).click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator("#editorialDrawerTitle")).to_have_text(
                "Delivery Center"
            )
            expect(page.locator(".selector-policy")).to_contain_text(
                "Presets & export"
            )

            page.locator("#deliveryTarget").select_option(
                "social_vertical_1080x1920"
            )
            expect(page.locator("#deliveryFraming")).to_have_value("fit")
            expect(page.locator("#deliveryPreflight")).to_contain_text(
                "Version publiée"
            )
            expect(page.locator("#deliveryPreflight")).to_contain_text(
                "PASS"
            )
            expect(page.locator("#deliveryExportBtn")).to_be_enabled()

            page.locator("#deliveryFraming").select_option("fill")
            expect(page.locator("#deliveryCropRow")).to_be_visible()
            expect(page.locator("#deliveryPreflight")).to_contain_text(
                "BLOCKED"
            )
            expect(page.locator("#deliveryExportBtn")).to_be_disabled()

            page.locator("#deliveryAllowCrop").check()
            expect(page.locator("#deliveryPreflight")).to_contain_text(
                "68.4%"
            )
            expect(page.locator("#deliveryExportBtn")).to_be_enabled()
            expect(page.locator("#deliveryExportBtn")).to_have_text(
                "Exporter avec avertissements"
            )

            page.locator("#deliveryExportBtn").click()
            expect(page.locator(".delivery-success")).to_be_visible()
            expect(page.locator(".delivery-success")).to_contain_text(
                "1080×1920"
            )
            expect(page.locator(".delivery-conformance")).to_contain_text(
                "CONFORMITÉ"
            )
            expect(page.locator(".delivery-conformance")).to_contain_text(
                "PASS"
            )
            expect(
                page.get_by_role("link", name="Télécharger le livrable")
            ).to_be_visible()
            expect(
                page.get_by_role("link", name="Rapport JSON")
            ).to_be_visible()

            page.locator("#editorialDrawerBody").get_by_role(
                "button", name="Dupliquer"
            ).click()
            expect(page.locator(".delivery-preset-editor")).to_be_visible()
            custom_id = page.locator("#deliveryTarget").input_value()
            assert custom_id.startswith("custom_")
            page.locator("#deliveryPresetLabel").fill("Preset navigateur 9x16")
            page.locator("#deliveryPresetFps").select_option("30")
            page.locator("#deliveryPresetVideoBitrate").fill("14")
            page.get_by_role("button", name="Enregistrer le preset").click()
            expect(page.locator(".delivery-target-summary")).to_contain_text(
                "Preset navigateur 9x16"
            )
            expect(page.locator(".delivery-target-summary")).to_contain_text(
                "30 fps"
            )
            expect(page.locator(".delivery-target-summary")).to_contain_text(
                "14 Mb/s"
            )
            page.get_by_role("button", name="Définir par défaut").click()
            expect(page.locator(".delivery-target-summary")).to_contain_text(
                "PERSONNALISÉ · DÉFAUT"
            )

            page.locator("#editorialDrawer .pane-close").click()
            page.get_by_role("button", name="Export", exact=True).click()
            expect(page.locator("#deliveryTarget")).to_have_value(custom_id)
            expect(page.locator("#deliveryPresetLabel")).to_have_value(
                "Preset navigateur 9x16"
            )

            page.locator("#editorialDrawerBody").get_by_role(
                "button", name="Supprimer"
            ).click()
            expect(page.locator("#deliveryTarget")).to_have_value(
                "online_1080"
            )
            assert errors == []
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
