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

CREATE TABLE IF NOT EXISTS audio_loudness_analysis (
    media_id INTEGER PRIMARY KEY,
    analyzer_version TEXT NOT NULL,
    status TEXT NOT NULL,
    integrated_lufs REAL,
    true_peak_dbfs REAL,
    loudness_range_lu REAL,
    threshold_lufs REAL,
    silence_json TEXT NOT NULL DEFAULT '[]',
    raw_json TEXT NOT NULL DEFAULT '{}',
    analyzed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(media_id) REFERENCES media(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audio_track_analysis (
    media_id INTEGER NOT NULL,
    track_index INTEGER NOT NULL,
    stream_index INTEGER NOT NULL,
    analyzer_version TEXT NOT NULL,
    status TEXT NOT NULL,
    codec TEXT,
    channels INTEGER,
    channel_layout TEXT,
    sample_rate INTEGER,
    language TEXT,
    title TEXT,
    is_default INTEGER NOT NULL DEFAULT 0,
    mean_dbfs REAL,
    peak_dbfs REAL,
    silent INTEGER NOT NULL DEFAULT 0,
    detected_silence_seconds REAL NOT NULL DEFAULT 0,
    selected_for_transcription INTEGER NOT NULL DEFAULT 0,
    analyzed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(media_id, track_index),
    FOREIGN KEY(media_id) REFERENCES media(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_audio_track_selected
ON audio_track_analysis(media_id, selected_for_transcription);

CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL,
    audio_track_index INTEGER NOT NULL,
    provider TEXT NOT NULL,
    model_id TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    status TEXT NOT NULL,
    language_code TEXT,
    language_probability REAL,
    text_content TEXT NOT NULL DEFAULT '',
    words_json TEXT NOT NULL DEFAULT '[]',
    phrases_json TEXT NOT NULL DEFAULT '[]',
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(media_id, audio_track_index, provider, model_id, source_sha256),
    FOREIGN KEY(media_id) REFERENCES media(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_transcripts_media
ON transcripts(media_id, audio_track_index, status);

CREATE TABLE IF NOT EXISTS editorial_agent_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    edit_name TEXT NOT NULL,
    proposal_kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    brief TEXT,
    base_timeline_hash TEXT,
    proposal_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_editorial_agent_proposals_edit
ON editorial_agent_proposals(edit_name, status, created_at);

CREATE TABLE IF NOT EXISTS master_critic_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    edit_name TEXT NOT NULL,
    version_label TEXT,
    source_path TEXT NOT NULL,
    status TEXT NOT NULL,
    report_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_master_critic_edit
ON master_critic_reports(edit_name, created_at);

CREATE TABLE IF NOT EXISTS semantic_profiles (
    media_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    model_id TEXT NOT NULL,
    embedding_json TEXT NOT NULL DEFAULT '[]',
    frame_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    analyzed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(media_id, provider, model_id),
    FOREIGN KEY(media_id) REFERENCES media(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS semantic_tag_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    facet TEXT NOT NULL,
    confidence REAL NOT NULL,
    provider TEXT NOT NULL,
    model_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    evidence_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(media_id, tag, provider, model_id),
    FOREIGN KEY(media_id) REFERENCES media(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_semantic_proposals_media
ON semantic_tag_proposals(media_id, status);

CREATE TABLE IF NOT EXISTS semantic_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    facet TEXT NOT NULL,
    timestamp_seconds REAL NOT NULL,
    roi_json TEXT NOT NULL DEFAULT '{"x":0,"y":0,"width":1,"height":1}',
    provider TEXT NOT NULL,
    model_id TEXT NOT NULL,
    embedding_json TEXT NOT NULL DEFAULT '[]',
    image_path TEXT,
    group_name TEXT,
    quality TEXT NOT NULL DEFAULT 'secondary',
    status TEXT NOT NULL DEFAULT 'READY',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(media_id) REFERENCES media(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_semantic_references_tag
ON semantic_references(tag, facet, status);

CREATE INDEX IF NOT EXISTS idx_semantic_references_media
ON semantic_references(media_id, status);

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


def _migrate_semantic_references(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(semantic_references)").fetchall()
    }
    if "group_name" not in columns:
        conn.execute("ALTER TABLE semantic_references ADD COLUMN group_name TEXT")
    if "quality" not in columns:
        conn.execute(
            "ALTER TABLE semantic_references "
            "ADD COLUMN quality TEXT NOT NULL DEFAULT 'secondary'"
        )
    conn.execute(
        "UPDATE semantic_references SET quality='secondary' "
        "WHERE quality IS NULL OR TRIM(quality)=''"
    )
    conn.commit()


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate_semantic_references(conn)
    return conn
