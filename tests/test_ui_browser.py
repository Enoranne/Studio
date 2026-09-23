from pathlib import Path
import re
import socket
import threading
import time

import uvicorn
from playwright.sync_api import expect, sync_playwright

from piste_studio.app import create_app
from piste_studio.project import init_project
from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.media_intelligence import _write_analysis
from piste_studio.semantic_vision import store_semantic_profile
from piste_studio.timeline import save_timeline


def _free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def test_real_browser_navigation_and_workspaces(tmp_path):
    root = tmp_path / "Project"
    init_project(root, "Browser Test")
    (root / "rushes" / "malo_a.mp4").write_bytes(b"fake-a")
    (root / "rushes" / "malo_b.mp4").write_bytes(b"fake-b")
    (root / "audio" / "voice.wav").write_bytes(b"fake-audio")
    scan_media(root)
    rows = fetch_media_with_metadata(root)
    videos = [row for row in rows if row["kind"] == "video"]
    audio = next(row for row in rows if row["kind"] == "audio")
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
    set_media_metadata(
        root,
        audio["id"],
        title="Voice",
        duration_seconds=8.0,
        tags=["voice", "malo"],
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
                    "start": 3,
                    "duration": 5,
                    "sourceStart": 0,
                    "audioDbId": audio["id"],
                    "gainDb": -6,
                    "pan": 0,
                    "audioRole": "vo",
                    "fadeIn": 0.4,
                    "fadeOut": 0.5,
                    "volumeEnvelope": [],
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
            page.get_by_role("button", name="Proposer continuité").click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator(".semantic-proposal-card")).to_have_count(3)
            character_card = page.locator(".semantic-proposal-card").filter(
                has_text="character:malo"
            )
            expect(character_card).to_be_visible()
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

            assert errors == []
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
