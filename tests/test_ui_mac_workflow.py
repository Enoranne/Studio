"""Regression checks for new projects and embedded source audio.

The audio test measures a decoded synthetic signal inside Chromium. It is not
a listening test on the Mac speakers or a validation of GH5/WKWebView codecs.
"""
from contextlib import contextmanager
import math
import shutil
import socket
import struct
import subprocess
import threading
import time
import wave

import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright

from piste_studio.app import create_app
from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.project import init_project
from piste_studio.timeline import load_timeline, save_timeline


@contextmanager
def studio_page(root):
    # Reserve the actual listening socket, rather than racing for a free port.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(create_app(root), log_level="error"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.02)
            assert server.started, "Local test server did not start"
            with sync_playwright() as p:
                browser = p.chromium.launch()
                try:
                    page = browser.new_page(viewport={"width": 1440, "height": 900})
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(f"http://127.0.0.1:{sock.getsockname()[1]}/")
                    page.wait_for_function("backendConnected")
                    yield page
                    assert not errors, errors
                finally:
                    browser.close()
        finally:
            server.should_exit = True
            thread.join(timeout=10)


def test_new_project_starts_empty_and_stays_empty_after_save_reload(tmp_path):
    root = tmp_path / "Nouveau projet"
    init_project(root, "Nouveau projet")
    with studio_page(root) as page:
        expect(page.locator(".clip")).to_have_count(0)
        expect(page.locator("#inspector")).to_contain_text("Projet vide")
        assert page.evaluate("clips.length") == 0
        assert page.evaluate("tracks.map(t => t.id)") == ["video", "titles", "vo", "music", "sfx"]
        assert page.evaluate("saveBackendTimeline()") is True
        saved = load_timeline(root)
        assert saved["schema_version"] == 6
        assert saved["clips"] == []
        assert saved["storyline"] == {"mode": "magnetic", "start": 0}
        page.reload()
        page.wait_for_function("backendConnected")
        expect(page.locator(".clip")).to_have_count(0)
        expect(page.locator("#inspector")).to_contain_text("Projet vide")
        assert page.evaluate("clips.length") == 0


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg required for synthetic video with audio")
def test_source_audio_program_mute_and_saved_timeline(tmp_path):
    root = tmp_path / "Audio projet"
    init_project(root, "Audio projet")
    # VP8/Vorbis is supported by the CI Chromium build. Original media stays intact.
    sound = tmp_path / "tone.wav"
    with wave.open(str(sound), "wb") as wav:
        wav.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
        wav.writeframes(b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * 440 * i / 48000))) for i in range(48000 * 3)))
    video = root / "rushes" / "tone.webm"
    subprocess.run([
        shutil.which("ffmpeg"), "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=160x90:r=24:d=3",
        "-i", str(sound), "-c:v", "libvpx", "-c:a", "libvorbis", "-shortest", str(video),
    ], check=True, timeout=30)
    original = video.read_bytes()
    scan_media(root)
    media_id = fetch_media_with_metadata(root)[0]["id"]
    set_media_metadata(root, media_id, duration_seconds=3)
    save_timeline(root, {
        "edit_name": "teaser_30", "duration_seconds": 3,
        "storyline": {"mode": "magnetic", "start": 0},
        "tracks": [{"id": "video", "name": "VIDEO", "kind": "video", "muted": True}],
        "clips": [{"id": "saved-shot", "label": "Mon plan", "track": "video", "start": 0,
                   "duration": 3, "sourceStart": 0, "mediaDbId": media_id}],
    })
    with studio_page(root) as page:
        expect(page.locator(".clip")).to_have_count(1)
        assert page.evaluate("clips[0].id") == "saved-shot"
        assert page.locator("#video").evaluate("v => v.muted") is True
        page.locator(".media-row").first.click()
        assert page.locator("#video").evaluate("v => v.muted") is False
        page.locator("#playBtn").click()
        page.wait_for_function("document.querySelector('#video').currentTime > 0.1")
        # Verify actual decoded audio energy, not just the existence of a URL.
        energy = page.evaluate("""async () => {
            const ctx = new AudioContext();
            const source = ctx.createMediaElementSource(document.querySelector('#video'));
            const analyser = ctx.createAnalyser();
            source.connect(analyser); analyser.connect(ctx.destination);
            await ctx.resume();
            let peak = 0;
            for (let n = 0; n < 20; n++) {
                const samples = new Float32Array(analyser.fftSize);
                analyser.getFloatTimeDomainData(samples);
                for (const sample of samples) peak = Math.max(peak, Math.abs(sample));
                if (peak > 0.01) break;
                await new Promise(resolve => setTimeout(resolve, 25));
            }
            await ctx.close();
            return peak;
        }""")
        assert energy > 0.01
        page.locator('[data-monitor="program"]').click()
        assert page.locator("#video").evaluate("v => v.muted") is True
        page.locator(".storyline-track .track-controls button").first.click()
        assert page.locator("#video").evaluate("v => v.muted") is False
        assert page.evaluate("saveBackendTimeline()") is True
        page.reload()
        page.wait_for_function("backendConnected")
        assert page.evaluate("clips[0].id") == "saved-shot"
        assert page.locator("#video").evaluate("v => v.muted") is False
    assert video.read_bytes() == original
