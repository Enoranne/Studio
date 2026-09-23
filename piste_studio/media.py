from __future__ import annotations

from pathlib import Path
from hashlib import sha256

from .db import connect

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm"}
AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
SCAN_DIRS = ("rushes", "audio", "graphics")


def kind_for(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    if ext in IMAGE_EXT:
        return "image"
    return None


def quick_sha256(path: Path, max_bytes: int = 8 * 1024 * 1024) -> str:
    h = sha256()
    with path.open("rb") as f:
        h.update(f.read(max_bytes))
    h.update(str(path.stat().st_size).encode())
    return h.hexdigest()


def scan_media(root: Path) -> dict[str, int]:
    db_path = root / "media.sqlite"
    conn = connect(db_path)
    inserted = 0
    updated = 0
    ignored = 0

    try:
        for dirname in SCAN_DIRS:
            base = root / dirname
            if not base.exists():
                continue
            for path in sorted(base.rglob("*"), key=lambda p: p.as_posix().lower()):
                if not path.is_file():
                    continue
                kind = kind_for(path)
                if kind is None:
                    ignored += 1
                    continue
                rel = path.relative_to(root).as_posix()
                ext = path.suffix.lower()
                size = path.stat().st_size
                digest = quick_sha256(path)

                row = conn.execute(
                    "SELECT id, size_bytes, sha256 FROM media WHERE relative_path = ?",
                    (rel,),
                ).fetchone()
                if row is None:
                    conn.execute(
                        """
                        INSERT INTO media(relative_path, kind, extension, size_bytes, sha256)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (rel, kind, ext, size, digest),
                    )
                    inserted += 1
                elif row["size_bytes"] != size or row["sha256"] != digest:
                    conn.execute(
                        """
                        UPDATE media
                        SET kind=?, extension=?, size_bytes=?, sha256=?, updated_at=CURRENT_TIMESTAMP
                        WHERE relative_path=?
                        """,
                        (kind, ext, size, digest, rel),
                    )
                    updated += 1
        conn.commit()
        return {"inserted": inserted, "updated": updated, "ignored": ignored}
    finally:
        conn.close()
