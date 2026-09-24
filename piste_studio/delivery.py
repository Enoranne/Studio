from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re
import shutil
import subprocess

from .versioning import slugify
from .config import read_yaml, write_yaml


DELIVERY_VERSION = "0.23.5-delivery-2"


class DeliveryError(ValueError):
    pass


def delivery_targets() -> list[dict]:
    """
    Built-in reference targets for V0.23.4.

    These are technical starting points, not universal platform or festival
    specifications. A distributor/festival delivery sheet always wins.
    """
    return [
        {
            "id": "festival_prores_1080",
            "label": "Festival · ProRes 422 HQ · 1080p",
            "family": "festival",
            "width": 1920,
            "height": 1080,
            "aspect_ratio": "16:9",
            "fps": 24,
            "container": "mov",
            "video_codec": "prores_ks",
            "prores_profile": 3,
            "pixel_format": "yuv422p10le",
            "audio_codec": "pcm_s24le",
            "audio_sample_rate": 48000,
            "audio_channels": 2,
            "tesseract_resolution": "1080p",
            "tesseract_format": "prores",
            "framing_modes": ["native"],
            "default_framing": "native",
            "reference_only": True,
            "notes": [
                "Master de projection/interchange de haute qualité.",
                "Ce profil n'est pas un DCP.",
                "La fiche technique du festival reste prioritaire.",
            ],
        },
        {
            "id": "festival_h264_1080",
            "label": "Festival · H.264 haute qualité · 1080p",
            "family": "festival",
            "width": 1920,
            "height": 1080,
            "aspect_ratio": "16:9",
            "fps": 24,
            "container": "mp4",
            "video_codec": "libx264",
            "video_bitrate_mbps": 20,
            "pixel_format": "yuv420p",
            "audio_codec": "aac",
            "audio_bitrate_kbps": 320,
            "audio_sample_rate": 48000,
            "audio_channels": 2,
            "tesseract_resolution": "1080p",
            "tesseract_format": "mp4",
            "framing_modes": ["native"],
            "default_framing": "native",
            "reference_only": True,
            "notes": [
                "Fichier de visionnage/inscription haute qualité.",
                "Vérifier les exigences propres à chaque festival.",
            ],
        },
        {
            "id": "online_1080",
            "label": "Online · H.264 · 1080p",
            "family": "online",
            "width": 1920,
            "height": 1080,
            "aspect_ratio": "16:9",
            "fps": 24,
            "container": "mp4",
            "video_codec": "libx264",
            "video_bitrate_mbps": 8,
            "pixel_format": "yuv420p",
            "audio_codec": "aac",
            "audio_bitrate_kbps": 384,
            "audio_sample_rate": 48000,
            "audio_channels": 2,
            "tesseract_resolution": "1080p",
            "tesseract_format": "mp4",
            "framing_modes": ["native"],
            "default_framing": "native",
            "reference_only": True,
            "notes": [
                "Repère 1080p H.264 pour plateforme vidéo.",
                "Conserver le frame rate natif est préférable lorsque la chaîne le permet.",
            ],
        },
        {
            "id": "social_vertical_1080x1920",
            "label": "Social · Vertical · 9:16",
            "family": "social",
            "width": 1080,
            "height": 1920,
            "aspect_ratio": "9:16",
            "fps": 24,
            "container": "mp4",
            "video_codec": "libx264",
            "video_bitrate_mbps": 12,
            "pixel_format": "yuv420p",
            "audio_codec": "aac",
            "audio_bitrate_kbps": 256,
            "audio_sample_rate": 48000,
            "audio_channels": 2,
            "tesseract_resolution": "1080p",
            "tesseract_format": "mp4",
            "framing_modes": ["fit", "fill"],
            "default_framing": "fit",
            "reference_only": True,
            "notes": [
                "FIT conserve toute l'image avec padding.",
                "FILL recadre au centre et exige une autorisation explicite.",
            ],
        },
        {
            "id": "social_square_1080",
            "label": "Social · Carré · 1:1",
            "family": "social",
            "width": 1080,
            "height": 1080,
            "aspect_ratio": "1:1",
            "fps": 24,
            "container": "mp4",
            "video_codec": "libx264",
            "video_bitrate_mbps": 8,
            "pixel_format": "yuv420p",
            "audio_codec": "aac",
            "audio_bitrate_kbps": 256,
            "audio_sample_rate": 48000,
            "audio_channels": 2,
            "tesseract_resolution": "1080p",
            "tesseract_format": "mp4",
            "framing_modes": ["fit", "fill"],
            "default_framing": "fit",
            "reference_only": True,
            "notes": [
                "FIT conserve toute l'image avec padding.",
                "FILL recadre au centre et exige une autorisation explicite.",
            ],
        },
    ]


CUSTOM_PRESETS_SCHEMA_VERSION = 1
CUSTOM_PRESETS_FILENAME = "delivery-presets.yaml"
ALLOWED_DELIVERY_FPS = {24, 30, 60}
ALLOWED_FAMILIES = {"festival", "online", "social", "custom"}
ALLOWED_TESSERACT_RESOLUTIONS = {"720p", "1080p", "4k"}


def _preset_store_path(root: Path) -> Path:
    return root.expanduser().resolve() / CUSTOM_PRESETS_FILENAME


def _preset_store(root: Path) -> dict:
    path = _preset_store_path(root)
    if not path.exists():
        return {
            "schema_version": CUSTOM_PRESETS_SCHEMA_VERSION,
            "default_preset_id": "online_1080",
            "presets": [],
        }
    try:
        doc = read_yaml(path)
    except (OSError, ValueError) as exc:
        raise DeliveryError(f"Presets delivery illisibles : {exc}") from exc
    if int(doc.get("schema_version") or 0) != CUSTOM_PRESETS_SCHEMA_VERSION:
        raise DeliveryError("Version de fichier delivery-presets.yaml non supportée.")
    presets = doc.get("presets")
    if not isinstance(presets, list):
        raise DeliveryError("delivery-presets.yaml : 'presets' doit être une liste.")
    return {
        "schema_version": CUSTOM_PRESETS_SCHEMA_VERSION,
        "default_preset_id": str(
            doc.get("default_preset_id") or "online_1080"
        ),
        "presets": presets,
    }


def _write_preset_store(root: Path, doc: dict) -> None:
    write_yaml(
        _preset_store_path(root),
        {
            "schema_version": CUSTOM_PRESETS_SCHEMA_VERSION,
            "default_preset_id": str(
                doc.get("default_preset_id") or "online_1080"
            ),
            "presets": list(doc.get("presets") or []),
        },
    )


def _custom_preset_id(label: str, existing: set[str]) -> str:
    stem = slugify(str(label or "preset")).replace("-", "_")
    stem = re.sub(r"[^a-z0-9_]+", "_", stem).strip("_") or "preset"
    candidate = f"custom_{stem}"
    suffix = 2
    while candidate in existing:
        candidate = f"custom_{stem}_{suffix}"
        suffix += 1
    return candidate


def _derive_aspect_ratio(width: int, height: int) -> str:
    from math import gcd

    g = gcd(int(width), int(height))
    return f"{int(width) // g}:{int(height) // g}"


def _normalize_custom_preset(
    payload: dict,
    *,
    preset_id: str,
    created_at: str | None = None,
) -> dict:
    if not isinstance(payload, dict):
        raise DeliveryError("Preset delivery invalide.")

    label = str(payload.get("label") or "").strip()
    if not label or len(label) > 100:
        raise DeliveryError("Le nom du preset doit contenir 1 à 100 caractères.")

    family = str(payload.get("family") or "custom").lower()
    if family not in ALLOWED_FAMILIES:
        raise DeliveryError("Famille invalide : festival, online, social ou custom.")

    try:
        width = int(payload.get("width"))
        height = int(payload.get("height"))
    except (TypeError, ValueError) as exc:
        raise DeliveryError("Largeur et hauteur entières requises.") from exc
    if width < 320 or width > 7680 or height < 240 or height > 7680:
        raise DeliveryError("Dimensions autorisées : 320..7680 × 240..7680.")
    if width % 2 or height % 2:
        raise DeliveryError("Les dimensions de delivery doivent être paires.")

    try:
        fps = int(payload.get("fps"))
    except (TypeError, ValueError) as exc:
        raise DeliveryError("FPS invalide.") from exc
    if fps not in ALLOWED_DELIVERY_FPS:
        raise DeliveryError("FPS autorisés en V0.23.5 : 24, 30 ou 60.")

    codec = str(payload.get("video_codec") or "libx264").lower()
    if codec not in {"libx264", "prores_ks"}:
        raise DeliveryError("Codec vidéo invalide : H.264 ou ProRes attendu.")

    framing_modes = ["native"]
    default_framing = str(payload.get("default_framing") or "native").lower()
    if width != 1920 or height != 1080 or default_framing in {"fit", "fill"}:
        framing_modes = ["fit", "fill"]
        if default_framing not in framing_modes:
            default_framing = "fit"
    elif default_framing != "native":
        default_framing = "native"

    tesseract_resolution = str(
        payload.get("tesseract_resolution") or "1080p"
    ).lower()
    if tesseract_resolution not in ALLOWED_TESSERACT_RESOLUTIONS:
        raise DeliveryError("Résolution source Tesseract invalide.")

    now = datetime.now(timezone.utc).isoformat()
    common = {
        "id": preset_id,
        "label": label,
        "family": family,
        "width": width,
        "height": height,
        "aspect_ratio": _derive_aspect_ratio(width, height),
        "fps": fps,
        "tesseract_resolution": tesseract_resolution,
        "framing_modes": framing_modes,
        "default_framing": default_framing,
        "reference_only": False,
        "custom": True,
        "created_at": created_at or now,
        "updated_at": now,
        "notes": [str(x).strip() for x in (payload.get("notes") or []) if str(x).strip()][:8],
    }

    if codec == "prores_ks":
        return {
            **common,
            "container": "mov",
            "video_codec": "prores_ks",
            "prores_profile": 3,
            "pixel_format": "yuv422p10le",
            "audio_codec": "pcm_s24le",
            "audio_sample_rate": 48000,
            "audio_channels": 2,
            "tesseract_format": "prores",
        }

    try:
        video_bitrate = float(payload.get("video_bitrate_mbps") or 8)
        audio_bitrate = int(payload.get("audio_bitrate_kbps") or 256)
    except (TypeError, ValueError) as exc:
        raise DeliveryError("Débits vidéo/audio invalides.") from exc
    if video_bitrate < 1 or video_bitrate > 200:
        raise DeliveryError("Débit H.264 autorisé : 1 à 200 Mb/s.")
    if audio_bitrate < 96 or audio_bitrate > 512:
        raise DeliveryError("Débit AAC autorisé : 96 à 512 kb/s.")
    return {
        **common,
        "container": "mp4",
        "video_codec": "libx264",
        "video_bitrate_mbps": round(video_bitrate, 3),
        "pixel_format": "yuv420p",
        "audio_codec": "aac",
        "audio_bitrate_kbps": audio_bitrate,
        "audio_sample_rate": 48000,
        "audio_channels": 2,
        "tesseract_format": "mp4",
    }


def list_project_delivery_presets(root: Path) -> list[dict]:
    doc = _preset_store(root)
    result: list[dict] = []
    seen = {item["id"] for item in delivery_targets()}
    for raw in doc["presets"]:
        if not isinstance(raw, dict):
            continue
        preset_id = str(raw.get("id") or "")
        if not preset_id or preset_id in seen:
            continue
        try:
            clean = _normalize_custom_preset(
                raw,
                preset_id=preset_id,
                created_at=raw.get("created_at"),
            )
        except DeliveryError:
            continue
        clean["updated_at"] = str(raw.get("updated_at") or clean["updated_at"])
        result.append(clean)
        seen.add(preset_id)
    return result


def all_delivery_targets(root: Path | None = None) -> list[dict]:
    builtins = [dict(item, custom=False) for item in delivery_targets()]
    if root is None:
        return builtins
    return builtins + list_project_delivery_presets(root)


def get_default_delivery_preset_id(root: Path) -> str:
    doc = _preset_store(root)
    requested = str(doc.get("default_preset_id") or "online_1080")
    valid = {item["id"] for item in all_delivery_targets(root)}
    return requested if requested in valid else "online_1080"


def set_default_delivery_preset(root: Path, preset_id: str) -> str:
    resolved = resolve_delivery_target(preset_id, root=root)
    doc = _preset_store(root)
    doc["default_preset_id"] = resolved["id"]
    _write_preset_store(root, doc)
    return resolved["id"]


def create_project_delivery_preset(root: Path, payload: dict) -> dict:
    doc = _preset_store(root)
    existing = {item["id"] for item in all_delivery_targets(root)}
    preset_id = _custom_preset_id(str(payload.get("label") or "preset"), existing)
    clean = _normalize_custom_preset(payload, preset_id=preset_id)
    doc["presets"].append(clean)
    _write_preset_store(root, doc)
    return clean


def update_project_delivery_preset(
    root: Path,
    preset_id: str,
    payload: dict,
) -> dict:
    if preset_id in {item["id"] for item in delivery_targets()}:
        raise DeliveryError("Un preset intégré est immuable : dupliquez-le d'abord.")
    doc = _preset_store(root)
    for index, raw in enumerate(doc["presets"]):
        if isinstance(raw, dict) and str(raw.get("id")) == preset_id:
            merged = {**raw, **payload}
            clean = _normalize_custom_preset(
                merged,
                preset_id=preset_id,
                created_at=raw.get("created_at"),
            )
            doc["presets"][index] = clean
            _write_preset_store(root, doc)
            return clean
    raise DeliveryError("Preset delivery personnalisé introuvable.")


def delete_project_delivery_preset(root: Path, preset_id: str) -> None:
    if preset_id in {item["id"] for item in delivery_targets()}:
        raise DeliveryError("Un preset intégré ne peut pas être supprimé.")
    doc = _preset_store(root)
    before = len(doc["presets"])
    doc["presets"] = [
        raw
        for raw in doc["presets"]
        if not isinstance(raw, dict) or str(raw.get("id")) != preset_id
    ]
    if len(doc["presets"]) == before:
        raise DeliveryError("Preset delivery personnalisé introuvable.")
    if doc.get("default_preset_id") == preset_id:
        doc["default_preset_id"] = "online_1080"
    _write_preset_store(root, doc)


def duplicate_delivery_preset(
    root: Path,
    preset_id: str,
    *,
    label: str | None = None,
) -> dict:
    source = resolve_delivery_target(preset_id, root=root)
    payload = dict(source)
    payload["label"] = str(label or f"{source['label']} · copie")
    for key in ("id", "custom", "reference_only", "created_at", "updated_at"):
        payload.pop(key, None)
    return create_project_delivery_preset(root, payload)


def export_delivery_preset(root: Path, preset_id: str) -> dict:
    preset = resolve_delivery_target(preset_id, root=root)
    payload = {
        key: value
        for key, value in preset.items()
        if key not in {"id", "custom", "reference_only", "created_at", "updated_at"}
    }
    return {
        "schema_version": CUSTOM_PRESETS_SCHEMA_VERSION,
        "kind": "piste_studio_delivery_preset",
        "preset": payload,
    }


def import_delivery_preset(root: Path, document: dict) -> dict:
    if not isinstance(document, dict):
        raise DeliveryError("Document de preset invalide.")
    if document.get("kind") != "piste_studio_delivery_preset":
        raise DeliveryError("Type de document preset invalide.")
    if int(document.get("schema_version") or 0) != CUSTOM_PRESETS_SCHEMA_VERSION:
        raise DeliveryError("Version de document preset non supportée.")
    preset = document.get("preset")
    if not isinstance(preset, dict):
        raise DeliveryError("Preset importé absent ou invalide.")
    return create_project_delivery_preset(root, preset)


def resolve_delivery_target(
    target_id: str,
    *,
    root: Path | None = None,
) -> dict:
    targets = {
        item["id"]: item
        for item in all_delivery_targets(root)
    }
    try:
        return dict(targets[str(target_id)])
    except KeyError as exc:
        raise DeliveryError(f"Cible de delivery inconnue : {target_id}") from exc


def _safe_version(version: str) -> str:
    value = str(version or "").strip()
    if not re.fullmatch(r"V\d{3,}", value):
        raise DeliveryError("Version invalide : format V001 attendu.")
    return value


def _stable_payload(timeline: dict) -> dict:
    return {
        "duration_seconds": round(float(timeline.get("duration_seconds") or 0.0), 6),
        "storyline": timeline.get("storyline") or {},
        "tracks": timeline.get("tracks") or [],
        "clips": timeline.get("clips") or [],
    }


def timeline_delivery_fingerprint(timeline: dict) -> str:
    raw = json.dumps(
        _stable_payload(timeline),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _version_dir(root: Path, edit_name: str, version: str) -> Path:
    base = root.expanduser().resolve()
    path = (base / "edits" / slugify(edit_name) / _safe_version(version)).resolve()
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise DeliveryError("Version hors projet.") from exc
    return path


def _read_json(path: Path) -> dict | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def load_published_timeline(
    root: Path,
    edit_name: str,
    version: str,
) -> dict | None:
    return _read_json(
        _version_dir(root, edit_name, version) / "timeline.json"
    )


def _published_timeline_status(
    root: Path,
    timeline: dict,
    edit_name: str,
    version: str,
) -> dict:
    published = load_published_timeline(root, edit_name, version)
    if published is None:
        return {
            "status": "MISSING",
            "message": "Snapshot timeline de la version publiée introuvable.",
            "published_fingerprint": None,
            "current_fingerprint": timeline_delivery_fingerprint(timeline),
        }
    current = timeline_delivery_fingerprint(timeline)
    published_fp = timeline_delivery_fingerprint(published)
    return {
        "status": "PASS" if current == published_fp else "STALE",
        "message": (
            "La version publiée correspond au montage de travail."
            if current == published_fp
            else "Le montage de travail a changé depuis cette version publiée."
        ),
        "published_fingerprint": published_fp,
        "current_fingerprint": current,
    }


def _title_status(
    root: Path,
    timeline: dict,
    edit_name: str,
    version: str,
) -> dict:
    published = load_published_timeline(root, edit_name, version)
    source_timeline = published if isinstance(published, dict) else timeline
    titles = [
        clip for clip in source_timeline.get("clips", [])
        if str(clip.get("track") or "") == "titles"
    ]
    if not titles:
        return {
            "status": "PASS",
            "message": "Aucun titre/overlay à matérialiser.",
            "timeline_title_count": 0,
            "materialized_count": 0,
            "unmaterialized_count": 0,
        }

    manifest = _read_json(
        _version_dir(root, edit_name, version) / "authoring-manifest.json"
    )
    if manifest is None:
        return {
            "status": "MISSING",
            "message": (
                "Authoring manifest absent : la matérialisation des titres "
                "ne peut pas être confirmée."
            ),
            "timeline_title_count": len(titles),
            "materialized_count": 0,
            "unmaterialized_count": len(titles),
        }

    materialized = list(manifest.get("title_layers") or [])
    unmaterialized = list(manifest.get("unmaterialized_titles") or [])
    status = "PASS"
    message = "Tous les titres déclarés sont matérialisés."
    if unmaterialized or len(materialized) < len(titles):
        status = "WARN"
        message = (
            "Des titres/overlays restent non matérialisés dans le projet "
            "Tesseract : le rendu peut ne pas les contenir."
        )
    return {
        "status": status,
        "message": message,
        "timeline_title_count": len(titles),
        "materialized_count": len(materialized),
        "unmaterialized_count": len(unmaterialized),
    }


def _canvas_aspect(
    root: Path,
    edit_name: str,
    version: str,
) -> tuple[float | None, str | None]:
    version_dir = _version_dir(root, edit_name, version)
    for name in ("authoring-manifest.json", "authoring-plan.json"):
        doc = _read_json(version_dir / name)
        if not doc:
            continue
        canvas = doc.get("canvas")
        if not isinstance(canvas, dict):
            canvas = (doc.get("deliverable") or {}).get("canvas")
        if not isinstance(canvas, dict):
            continue
        try:
            width = float(canvas["width"])
            height = float(canvas["height"])
        except (KeyError, TypeError, ValueError):
            continue
        if width > 0 and height > 0:
            return width / height, name
    return None, None


def estimate_fill_crop(
    source_aspect: float | None,
    target_width: int,
    target_height: int,
) -> dict:
    target_aspect = float(target_width) / float(target_height)
    if not source_aspect or source_aspect <= 0:
        return {
            "known": False,
            "axis": None,
            "fraction": None,
            "percent": None,
        }
    source_aspect = float(source_aspect)
    if abs(source_aspect - target_aspect) < 1e-6:
        fraction = 0.0
        axis = "none"
    elif source_aspect > target_aspect:
        fraction = 1.0 - target_aspect / source_aspect
        axis = "width"
    else:
        fraction = 1.0 - source_aspect / target_aspect
        axis = "height"
    return {
        "known": True,
        "axis": axis,
        "fraction": round(max(0.0, fraction), 6),
        "percent": round(max(0.0, fraction) * 100.0, 1),
    }


def preflight_delivery(
    root: Path,
    timeline: dict,
    *,
    edit_name: str,
    version: str,
    target_id: str,
    framing_mode: str | None = None,
    allow_crop: bool = False,
    audio_status: dict | None = None,
) -> dict:
    target = resolve_delivery_target(target_id, root=root)
    framing = str(framing_mode or target["default_framing"]).lower()
    if framing not in target["framing_modes"]:
        raise DeliveryError(
            f"Cadrage invalide pour {target_id}: "
            + ", ".join(target["framing_modes"])
        )

    version_state = _published_timeline_status(
        root,
        timeline,
        edit_name,
        version,
    )
    titles = _title_status(root, timeline, edit_name, version)
    audio = dict(audio_status or {
        "status": "MISSING",
        "message": "Master Check audio non fourni au préflight.",
        "reasons": ["Contrôle audio master absent."],
    })

    source_aspect, aspect_source = _canvas_aspect(root, edit_name, version)
    crop = estimate_fill_crop(
        source_aspect,
        int(target["width"]),
        int(target["height"]),
    )
    framing_status = "PASS"
    framing_message = "Aucun recadrage destructif demandé."
    can_export = True
    if framing == "fit":
        framing_message = (
            "FIT : toute l'image est conservée ; du padding peut apparaître "
            "pour respecter le canvas cible."
        )
    elif framing == "fill":
        if not allow_crop:
            can_export = False
            framing_status = "BLOCKED"
            framing_message = (
                "FILL/CROP exige une autorisation explicite : il peut retirer "
                "une partie de l'image."
            )
        else:
            framing_status = "WARN" if (crop.get("fraction") or 0) > 0 else "PASS"
            if crop.get("known") and crop.get("percent") is not None:
                axis = "largeur" if crop.get("axis") == "width" else "hauteur"
                framing_message = (
                    f"FILL/CROP autorisé : environ {crop['percent']:.1f}% "
                    f"de la {axis} du cadre source sera hors image."
                )
            else:
                framing_message = (
                    "FILL/CROP explicitement autorisé ; perte de cadre exacte "
                    "non calculable avant rendu."
                )

    checks = {
        "published_version": version_state,
        "audio": audio,
        "titles": titles,
        "framing": {
            "status": framing_status,
            "message": framing_message,
            "mode": framing,
            "crop_estimate": crop,
            "source_aspect": source_aspect,
            "source_aspect_evidence": aspect_source,
        },
    }

    warning_states = {"WARN", "STALE", "MISSING"}
    warnings = []
    for key, value in checks.items():
        status = str(value.get("status") or "MISSING").upper()
        if status in warning_states:
            warnings.append({
                "check": key,
                "status": status,
                "message": str(value.get("message") or ""),
            })
        if status == "BLOCKED":
            can_export = False

    return {
        "version": DELIVERY_VERSION,
        "edit_name": str(edit_name),
        "published_version": _safe_version(version),
        "target": target,
        "framing_mode": framing,
        "allow_crop": bool(allow_crop),
        "checks": checks,
        "warnings": warnings,
        "can_export": bool(can_export),
        "requires_confirmation": bool(warnings),
        "policy": {
            "festival_sheet_overrides_builtin_target": True,
            "no_silent_crop": True,
            "fill_crop_requires_explicit_permission": True,
            "no_automatic_editorial_reframe": True,
            "audio_warning_does_not_silently_block": True,
            "unmaterialized_titles_are_reported": True,
            "published_version_freshness_is_reported": True,
        },
    }


def _video_filter(target: dict, framing_mode: str) -> str | None:
    if framing_mode == "native":
        return None
    width = int(target["width"])
    height = int(target["height"])
    if framing_mode == "fit":
        return (
            f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease:"
            "flags=lanczos,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
        )
    if framing_mode == "fill":
        return (
            f"scale=w={width}:h={height}:force_original_aspect_ratio=increase:"
            "flags=lanczos,"
            f"crop={width}:{height},setsar=1"
        )
    raise DeliveryError(f"Mode de cadrage invalide : {framing_mode}")


def build_delivery_ffmpeg_args(
    ffmpeg: str,
    source: Path,
    output: Path,
    target: dict,
    *,
    framing_mode: str,
    allow_crop: bool = False,
) -> list[str]:
    if framing_mode == "fill" and not allow_crop:
        raise DeliveryError(
            "Le recadrage FILL/CROP nécessite une autorisation explicite."
        )
    if framing_mode not in target["framing_modes"]:
        raise DeliveryError("Mode de cadrage incompatible avec la cible.")

    args = [
        ffmpeg,
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
    ]
    vf = _video_filter(target, framing_mode)
    if vf:
        args.extend(["-vf", vf])
    args.extend(["-r", str(int(target["fps"]))])

    if target["video_codec"] == "prores_ks":
        args.extend([
            "-c:v",
            "prores_ks",
            "-profile:v",
            str(int(target.get("prores_profile", 3))),
            "-pix_fmt",
            str(target.get("pixel_format") or "yuv422p10le"),
            "-c:a",
            str(target.get("audio_codec") or "pcm_s24le"),
            "-ar",
            str(int(target.get("audio_sample_rate") or 48000)),
            "-ac",
            str(int(target.get("audio_channels") or 2)),
        ])
    else:
        bitrate = float(target.get("video_bitrate_mbps") or 8)
        bitrate_text = f"{bitrate:g}M"
        gop = max(1, int(round(float(target["fps"]) / 2.0)))
        args.extend([
            "-c:v",
            "libx264",
            "-profile:v",
            "high",
            "-pix_fmt",
            str(target.get("pixel_format") or "yuv420p"),
            "-preset",
            "medium",
            "-b:v",
            bitrate_text,
            "-maxrate",
            bitrate_text,
            "-bufsize",
            f"{bitrate * 2:g}M",
            "-g",
            str(gop),
            "-keyint_min",
            str(gop),
            "-sc_threshold",
            "0",
            "-c:a",
            str(target.get("audio_codec") or "aac"),
            "-b:a",
            f"{int(target.get('audio_bitrate_kbps') or 256)}k",
            "-ar",
            str(int(target.get("audio_sample_rate") or 48000)),
            "-ac",
            str(int(target.get("audio_channels") or 2)),
            "-movflags",
            "+faststart",
        ])
    args.append(str(output))
    return args


def _run(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DeliveryError("ffmpeg/ffprobe indisponible.") from exc


def inspect_delivery(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise DeliveryError("ffprobe n'est pas disponible.")
    proc = _run([
        ffprobe,
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ])
    if proc.returncode != 0:
        raise DeliveryError(proc.stderr.strip() or "ffprobe en échec.")
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise DeliveryError("Réponse ffprobe invalide.") from exc
    streams = list(doc.get("streams") or [])
    video = next(
        (s for s in streams if s.get("codec_type") == "video"),
        {},
    )
    audio = next(
        (s for s in streams if s.get("codec_type") == "audio"),
        {},
    )
    fps = None
    rate = str(video.get("avg_frame_rate") or video.get("r_frame_rate") or "")
    if "/" in rate:
        try:
            num, den = rate.split("/", 1)
            if float(den):
                fps = float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            fps = None
    elif rate:
        try:
            fps = float(rate)
        except ValueError:
            fps = None
    duration = (doc.get("format") or {}).get("duration")
    try:
        duration = float(duration)
    except (TypeError, ValueError):
        duration = None
    return {
        "video_codec": video.get("codec_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "pixel_format": video.get("pix_fmt"),
        "fps": None if fps is None else round(fps, 3),
        "color_space": video.get("color_space"),
        "color_transfer": video.get("color_transfer"),
        "color_primaries": video.get("color_primaries"),
        "audio_codec": audio.get("codec_name"),
        "audio_sample_rate": (
            int(audio["sample_rate"])
            if str(audio.get("sample_rate") or "").isdigit()
            else None
        ),
        "audio_channels": audio.get("channels"),
        "duration_seconds": (
            None if duration is None else round(duration, 3)
        ),
        "size_bytes": path.stat().st_size if path.exists() else None,
    }


def evaluate_delivery_probe(target: dict, probe: dict) -> dict:
    reasons: list[str] = []

    expected_video = (
        "prores"
        if target.get("video_codec") == "prores_ks"
        else "h264"
    )
    actual_video = str(probe.get("video_codec") or "")
    if actual_video != expected_video:
        reasons.append(
            f"Codec vidéo {actual_video or 'indisponible'} au lieu de "
            f"{expected_video}."
        )

    for field in ("width", "height"):
        expected = int(target[field])
        actual = probe.get(field)
        if actual is None or int(actual) != expected:
            reasons.append(
                f"{field}={actual if actual is not None else '—'} "
                f"au lieu de {expected}."
            )

    expected_pixel_format = str(target.get("pixel_format") or "")
    actual_pixel_format = str(probe.get("pixel_format") or "")
    if (
        expected_pixel_format
        and actual_pixel_format != expected_pixel_format
    ):
        reasons.append(
            f"Pixel format {actual_pixel_format or 'indisponible'} "
            f"au lieu de {expected_pixel_format}."
        )

    expected_fps = float(target["fps"])
    actual_fps = probe.get("fps")
    if actual_fps is None or abs(float(actual_fps) - expected_fps) > 0.05:
        reasons.append(
            f"fps={actual_fps if actual_fps is not None else '—'} "
            f"au lieu de {expected_fps:g}."
        )

    expected_audio = str(target.get("audio_codec") or "")
    actual_audio = str(probe.get("audio_codec") or "")
    if expected_audio and not actual_audio:
        reasons.append("Piste audio attendue mais absente du livrable.")
    elif actual_audio and expected_audio and actual_audio != expected_audio:
        reasons.append(
            f"Codec audio {actual_audio} au lieu de {expected_audio}."
        )

    expected_rate = int(target.get("audio_sample_rate") or 0)
    actual_rate = probe.get("audio_sample_rate")
    if actual_audio and expected_rate and (
        actual_rate is None or int(actual_rate) != expected_rate
    ):
        reasons.append(
            f"Sample rate {actual_rate if actual_rate is not None else '—'} "
            f"Hz au lieu de {expected_rate} Hz."
        )

    expected_channels = int(target.get("audio_channels") or 0)
    actual_channels = probe.get("audio_channels")
    if actual_audio and expected_channels and (
        actual_channels is None or int(actual_channels) != expected_channels
    ):
        reasons.append(
            f"Audio {actual_channels if actual_channels is not None else '—'} "
            f"canaux au lieu de {expected_channels}."
        )

    return {
        "status": "PASS" if not reasons else "WARN",
        "reasons": reasons,
    }


def delivery_output_path(
    root: Path,
    *,
    edit_name: str,
    version: str,
    target_id: str,
) -> Path:
    target = resolve_delivery_target(target_id, root=root)
    base = root.expanduser().resolve()
    folder = (
        base / "exports" / slugify(edit_name) / _safe_version(version)
    ).resolve()
    try:
        folder.relative_to(base)
    except ValueError as exc:
        raise DeliveryError("Dossier d'export hors projet.") from exc
    folder.mkdir(parents=True, exist_ok=True)
    name = (
        f"{slugify(edit_name)}_{_safe_version(version)}_"
        f"{target['id']}.{target['container']}"
    )
    return folder / name


def render_delivery_variant(
    root: Path,
    source_path: Path,
    *,
    edit_name: str,
    version: str,
    target_id: str,
    framing_mode: str | None = None,
    allow_crop: bool = False,
) -> dict:
    target = resolve_delivery_target(target_id, root=root)
    framing = str(framing_mode or target["default_framing"]).lower()
    source = source_path.expanduser().resolve()
    if not source.exists() or not source.is_file():
        raise DeliveryError("Rendu source Tesseract introuvable.")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise DeliveryError("ffmpeg n'est pas disponible.")

    output = delivery_output_path(
        root,
        edit_name=edit_name,
        version=version,
        target_id=target_id,
    )
    args = build_delivery_ffmpeg_args(
        ffmpeg,
        source,
        output,
        target,
        framing_mode=framing,
        allow_crop=allow_crop,
    )
    proc = _run(args)
    if proc.returncode != 0:
        raise DeliveryError(
            proc.stderr.strip() or "Transcodage delivery ffmpeg en échec."
        )
    if not output.exists() or not output.is_file():
        raise DeliveryError("Le livrable attendu n'a pas été produit.")
    probe = inspect_delivery(output)
    return {
        "path": output,
        "relative_path": output.relative_to(root.resolve()).as_posix(),
        "target": target,
        "framing_mode": framing,
        "probe": probe,
        "conformance": evaluate_delivery_probe(target, probe),
        "ffmpeg_args": args,
    }


def _safe_report_name(value: str) -> str:
    name = Path(str(value)).name
    if name != value or not re.fullmatch(r"[A-Za-z0-9_.-]+\.json", name):
        raise DeliveryError("Nom de rapport delivery invalide.")
    return name


def write_delivery_report(
    root: Path,
    *,
    edit_name: str,
    version: str,
    preflight: dict,
    render: dict,
    source_relative_path: str,
) -> dict:
    report_dir = root.resolve() / "reports" / "delivery"
    report_dir.mkdir(parents=True, exist_ok=True)
    target_id = str(render["target"]["id"])
    name = (
        f"{slugify(edit_name)}_{_safe_version(version)}_"
        f"{target_id}.json"
    )
    path = report_dir / name
    report = {
        "version": DELIVERY_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "edit_name": str(edit_name),
        "published_version": _safe_version(version),
        "target": render["target"],
        "framing_mode": render["framing_mode"],
        "source_relative_path": source_relative_path,
        "output_relative_path": render["relative_path"],
        "probe": render["probe"],
        "conformance": render.get("conformance") or {},
        "preflight": preflight,
        "policy": {
            "source_media_immutable": True,
            "master_is_never_modified": True,
            "no_silent_crop": True,
            "no_automatic_editorial_reframe": True,
            "delivery_report_is_auditable": True,
        },
    }
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report["report_name"] = name
    report["report_relative_path"] = path.relative_to(root.resolve()).as_posix()
    return report


def delivery_report_path(root: Path, report_name: str) -> Path:
    name = _safe_report_name(report_name)
    base = (root.resolve() / "reports" / "delivery").resolve()
    path = (base / name).resolve()
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise DeliveryError("Rapport delivery hors projet.") from exc
    if not path.exists() or not path.is_file():
        raise DeliveryError("Rapport delivery introuvable.")
    return path


def delivery_file_path(
    root: Path,
    edit_name: str,
    version: str,
    filename: str,
) -> Path:
    if Path(filename).name != filename:
        raise DeliveryError("Nom de livrable invalide.")
    base = (
        root.resolve()
        / "exports"
        / slugify(edit_name)
        / _safe_version(version)
    ).resolve()
    path = (base / filename).resolve()
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise DeliveryError("Livrable hors projet.") from exc
    if not path.exists() or not path.is_file():
        raise DeliveryError("Livrable introuvable.")
    return path
