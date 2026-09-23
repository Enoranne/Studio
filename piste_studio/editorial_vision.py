from __future__ import annotations

from pathlib import Path
import re
import subprocess

from .media_intelligence import detect_media_tools, probe_media
from .metadata import fetch_media_with_metadata


EDITORIAL_VISION_VERSION = "0.22-scenes-1"
DEFAULT_SCENE_THRESHOLD = 0.32
DEFAULT_MIN_WINDOW_SECONDS = 0.75
DEFAULT_LIMIT = 12

_SHOWINFO_TIME_RE = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")


class EditorialVisionError(ValueError):
    pass


def _media_row(root: Path, media_id: int) -> dict:
    rows = {int(x["id"]): x for x in fetch_media_with_metadata(root)}
    row = rows.get(int(media_id))
    if row is None:
        raise EditorialVisionError(f"Média introuvable : id={media_id}")
    if row.get("kind") != "video":
        raise EditorialVisionError("Les fenêtres éditoriales ciblent les vidéos.")
    return row


def _media_path(root: Path, row: dict) -> Path:
    base = root.resolve()
    path = (base / str(row["relative_path"])).resolve()
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise EditorialVisionError("Chemin média hors projet.") from exc
    if not path.exists() or not path.is_file():
        raise EditorialVisionError(
            f"Fichier vidéo absent : {row['relative_path']}"
        )
    return path


def parse_scene_change_times(log_text: str) -> list[float]:
    """Extract selected-frame times from ffmpeg showinfo output."""
    values: list[float] = []
    for match in _SHOWINFO_TIME_RE.finditer(log_text or ""):
        try:
            value = float(match.group(1))
        except (TypeError, ValueError):
            continue
        if value < 0:
            continue
        if not values or abs(value - values[-1]) > 0.04:
            values.append(value)
    return values


def detect_scene_changes(
    path: Path,
    *,
    threshold: float = DEFAULT_SCENE_THRESHOLD,
) -> list[float]:
    tools = detect_media_tools()
    if not tools.ffmpeg:
        raise EditorialVisionError("ffmpeg n’est pas disponible.")

    threshold = max(0.05, min(0.95, float(threshold)))
    vf = f"select='gt(scene,{threshold:.4f})',showinfo"
    try:
        proc = subprocess.run(
            [
                tools.ffmpeg,
                "-hide_banner",
                "-nostats",
                "-i", str(path),
                "-vf", vf,
                "-an",
                "-f", "null",
                "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise EditorialVisionError("ffmpeg n’est pas disponible.") from exc

    if proc.returncode != 0:
        raise EditorialVisionError(
            proc.stderr.strip() or "Détection de ruptures visuelles en échec."
        )
    return parse_scene_change_times(proc.stderr)


def _duration(root: Path, row: dict, path: Path) -> float:
    duration = float(row.get("duration_seconds") or 0.0)
    if duration > 0:
        return duration
    try:
        duration = float(probe_media(path).get("duration_seconds") or 0.0)
    except Exception as exc:
        raise EditorialVisionError(
            "Durée du rush indéterminable."
        ) from exc
    if duration <= 0:
        raise EditorialVisionError("Durée du rush indéterminable.")
    return duration


def build_candidate_windows(
    *,
    duration_seconds: float,
    scene_changes: list[float],
    min_window_seconds: float = DEFAULT_MIN_WINDOW_SECONDS,
    limit: int = DEFAULT_LIMIT,
    threshold: float = DEFAULT_SCENE_THRESHOLD,
) -> list[dict]:
    duration = max(0.0, float(duration_seconds))
    if duration <= 0:
        return []

    min_window = max(0.2, float(min_window_seconds))
    max_items = max(1, min(int(limit), 40))
    changes = sorted(
        {
            round(max(0.0, min(duration, float(value))), 6)
            for value in scene_changes
            if 0.05 < float(value) < duration - 0.05
        }
    )
    boundaries = [0.0, *changes, duration]

    windows: list[dict] = []
    for index in range(len(boundaries) - 1):
        source_in = boundaries[index]
        source_out = boundaries[index + 1]
        window_duration = source_out - source_in
        if window_duration + 1e-9 < min_window:
            continue
        before = changes[index - 1] if index > 0 and index - 1 < len(changes) else None
        after = changes[index] if index < len(changes) else None
        if before is None and after is None:
            reason = "Aucune rupture forte détectée : rush traité comme plan continu."
        elif before is None:
            reason = f"Début du rush → rupture visuelle à {after:.2f} s."
        elif after is None:
            reason = f"Rupture visuelle à {before:.2f} s → fin du rush."
        else:
            reason = (
                f"Segment entre ruptures visuelles à {before:.2f} s "
                f"et {after:.2f} s."
            )
        windows.append({
            "rank": len(windows) + 1,
            "source_in": round(source_in, 3),
            "source_out": round(source_out, 3),
            "duration": round(window_duration, 3),
            "boundary_before": None if before is None else round(before, 3),
            "boundary_after": None if after is None else round(after, 3),
            "reason": reason,
            "method": "ffmpeg_scene_change",
            "scene_threshold": round(float(threshold), 3),
        })
        if len(windows) >= max_items:
            break

    if windows:
        return windows

    # If every detected interval is too short, keep a single human-reviewable
    # fallback instead of pretending there is no usable source.
    return [{
        "rank": 1,
        "source_in": 0.0,
        "source_out": round(duration, 3),
        "duration": round(duration, 3),
        "boundary_before": None,
        "boundary_after": None,
        "reason": (
            "Aucun segment ne dépasse la durée minimale : "
            "rush complet proposé pour validation humaine."
        ),
        "method": "ffmpeg_scene_change_fallback",
        "scene_threshold": round(float(threshold), 3),
    }]


def suggest_editorial_windows(
    root: Path,
    media_id: int,
    *,
    threshold: float = DEFAULT_SCENE_THRESHOLD,
    min_window_seconds: float = DEFAULT_MIN_WINDOW_SECONDS,
    limit: int = DEFAULT_LIMIT,
) -> dict:
    row = _media_row(root, media_id)
    path = _media_path(root, row)
    duration = _duration(root, row, path)
    threshold = max(0.05, min(0.95, float(threshold)))
    scene_changes = detect_scene_changes(path, threshold=threshold)
    windows = build_candidate_windows(
        duration_seconds=duration,
        scene_changes=scene_changes,
        min_window_seconds=min_window_seconds,
        limit=limit,
        threshold=threshold,
    )
    return {
        "version": EDITORIAL_VISION_VERSION,
        "media_id": int(media_id),
        "relative_path": str(row["relative_path"]),
        "duration_seconds": round(duration, 3),
        "scene_threshold": round(threshold, 3),
        "scene_changes": [round(x, 3) for x in scene_changes],
        "candidates": windows,
        "policy": {
            "suggestion_only": True,
            "automatic_storyline_edit": False,
            "human_validation_required": True,
            "local_processing": True,
        },
    }
