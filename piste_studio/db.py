from __future__ import annotations

from pathlib import Path
import sqlite3

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relative_path TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    extension TEXT,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT,
    status TEXT NOT NULL DEFAULT 'UNREVIEWED',
    spoiler_level INTEGER NOT NULL DEFAULT 0,
    canonical INTEGER NOT NULL DEFAULT 0,
    trailer_safe INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS media_metadata (
    media_id INTEGER PRIMARY KEY,
    title TEXT,
    description TEXT,
    duration_seconds REAL,
    rating INTEGER NOT NULL DEFAULT 0,
    tags_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(media_id) REFERENCES media(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS media_analysis (
    media_id INTEGER PRIMARY KEY,
    analyzer_version TEXT NOT NULL,
    status TEXT NOT NULL,
    technical_json TEXT NOT NULL DEFAULT '{}',
    visual_signature_json TEXT NOT NULL DEFAULT '[]',
    filmstrip_path TEXT,
    analyzed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(media_id) REFERENCES media(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS edit_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    edit_name TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    version_label TEXT NOT NULL,
    parent_version_label TEXT,
    kind TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    manifest_path TEXT NOT NULL,
    brief_path TEXT,
    patch_path TEXT,
    UNIQUE(edit_name, version_number)
);

CREATE TABLE IF NOT EXISTS editorial_ranges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('favorite','reject')),
    source_in REAL NOT NULL,
    source_out REAL NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(media_id, kind, source_in, source_out),
    FOREIGN KEY(media_id) REFERENCES media(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS editorial_markers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    edit_name TEXT NOT NULL,
    time_seconds REAL NOT NULL,
    kind TEXT NOT NULL DEFAULT 'note',
    label TEXT NOT NULL,
    note TEXT,
    media_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(media_id) REFERENCES media(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_editorial_ranges_media ON editorial_ranges(media_id);
CREATE INDEX IF NOT EXISTS idx_editorial_markers_edit ON editorial_markers(edit_name, time_seconds);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT NOT NULL,
    payload_json TEXT
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn
