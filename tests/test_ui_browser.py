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
    scan_media(root)
    for row in fetch_media_with_metadata(root):
        set_media_metadata(
            root,
            row["id"],
            title=Path(row["relative_path"]).stem,
            duration_seconds=8.0,
            rating=4,
            tags=["malo", "enfance"],
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

            expect(page.locator(".editorial-inspector-section")).to_be_visible()
            page.get_by_role("button", name="Alternatives").click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            expect(page.locator(".suggestion-card")).to_have_count(1)
            expect(page.locator(".selector-policy")).to_contain_text("Validation humaine")
            page.get_by_role("button", name="Prévisualiser").click()
            expect(page.locator("#editorialDrawer")).to_be_visible()
            page.get_by_role("button", name="×").last.click()
            expect(page.locator("#editorialDrawer")).to_be_hidden()

            assert errors == []
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
