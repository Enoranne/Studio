from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re
import shutil
import subprocess

from .versioning import slugify


DELIVERY_VERSION = "0.23.4-delivery-1"


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


def resolve_delivery_target(target_id: str) -> dict:
    targets = {item["id"]: item for item in delivery_targets()}
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


def _published_timeline_status(
    root: Path,
    timeline: dict,
    edit_name: str,
    version: str,
) -> dict:
    path = _version_dir(root, edit_name, version) / "timeline.json"
    published = _read_json(path)
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
    titles = [
        clip for clip in timeline.get("clips", [])
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
    target = resolve_delivery_target(target_id)
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


def delivery_output_path(
    root: Path,
    *,
    edit_name: str,
    version: str,
    target_id: str,
) -> Path:
    target = resolve_delivery_target(target_id)
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
    target = resolve_delivery_target(target_id)
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
    return {
        "path": output,
        "relative_path": output.relative_to(root.resolve()).as_posix(),
        "target": target,
        "framing_mode": framing,
        "probe": inspect_delivery(output),
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
