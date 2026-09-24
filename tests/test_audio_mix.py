import math

import pytest

from piste_studio.media import scan_media
from piste_studio.metadata import fetch_media_with_metadata, set_media_metadata
from piste_studio.project import init_project
from piste_studio.timeline import TimelineError, validate_timeline


def make_root(tmp_path):
    root = tmp_path / "Audio"
    init_project(root, "Audio")
    (root / "audio" / "voice.wav").write_bytes(b"audio")
    scan_media(root)
    audio = next(x for x in fetch_media_with_metadata(root) if x["kind"] == "audio")
    set_media_metadata(root, audio["id"], title="Voice", duration_seconds=12.0)
    return root, audio["id"]


def base_payload(audio_id):
    return {
        "edit_name": "audio_mix",
        "duration_seconds": 30,
        "tracks": [
            {"id": "video", "name": "VIDEO", "kind": "video"},
            {"id": "vo", "name": "VO", "kind": "audio", "solo": True},
        ],
        "clips": [
            {
                "id": "a1",
                "track": "vo",
                "start": 3,
                "duration": 8,
                "sourceStart": 1,
                "audioDbId": audio_id,
                "gainDb": -6,
                "pan": -0.25,
                "audioRole": "vo",
                "fadeIn": 0.5,
                "fadeOut": 0.75,
                "volumeEnvelope": [
                    {"time": 2, "gainDb": -6},
                    {"time": 5, "gainDb": -12},
                ],
            }
        ],
    }


def test_audio_schema_v4_preserves_mix_state(tmp_path):
    root, audio_id = make_root(tmp_path)
    clean = validate_timeline(root, base_payload(audio_id))
    assert clean["schema_version"] == 5
    assert clean["tracks"][1]["solo"] is True
    clip = clean["clips"][0]
    assert clip["gainDb"] == -6
    assert clip["pan"] == -0.25
    assert clip["audioRole"] == "vo"
    assert clip["fadeIn"] == 0.5
    assert clip["fadeOut"] == 0.75
    assert clip["volumeEnvelope"] == [
        {"time": 2.0, "gainDb": -6.0},
        {"time": 5.0, "gainDb": -12.0},
    ]
    assert clip["gain"] == pytest.approx(10 ** (-6 / 20), rel=1e-5)


def test_legacy_linear_gain_migrates_to_db(tmp_path):
    root, audio_id = make_root(tmp_path)
    payload = base_payload(audio_id)
    clip = payload["clips"][0]
    clip.pop("gainDb")
    clip["gain"] = 0.5
    clean = validate_timeline(root, payload)
    assert clean["clips"][0]["gainDb"] == pytest.approx(
        20 * math.log10(0.5), abs=0.001
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("gainDb", 13, "Gain hors plage"),
        ("pan", 1.2, "Pan hors plage"),
        ("audioRole", "unknown", "Rôle audio invalide"),
    ],
)
def test_invalid_audio_mix_values_are_rejected(tmp_path, field, value, message):
    root, audio_id = make_root(tmp_path)
    payload = base_payload(audio_id)
    payload["clips"][0][field] = value
    with pytest.raises(TimelineError, match=message):
        validate_timeline(root, payload)


def test_invalid_automation_is_rejected(tmp_path):
    root, audio_id = make_root(tmp_path)
    payload = base_payload(audio_id)
    payload["clips"][0]["volumeEnvelope"] = [
        {"time": 9, "gainDb": -6}
    ]
    with pytest.raises(TimelineError, match="hors clip"):
        validate_timeline(root, payload)

    payload = base_payload(audio_id)
    payload["clips"][0]["volumeEnvelope"] = [
        {"time": 2, "gainDb": -6},
        {"time": 2, "gainDb": -12},
    ]
    with pytest.raises(TimelineError, match="même instant"):
        validate_timeline(root, payload)
