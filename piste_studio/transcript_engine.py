from __future__ import annotations

from pathlib import Path
import json
import os
import secrets
import subprocess
import urllib.error
import urllib.request

from .audio_tracks import (
    AudioTrackIntelligenceError,
    analyze_audio_tracks,
    list_audio_tracks,
    selected_audio_track,
)
from .db import connect
from .metadata import fetch_media_with_metadata

TRANSCRIPT_ENGINE_VERSION = "0.26-transcript-1"
DEFAULT_PROVIDER = "elevenlabs"
DEFAULT_MODEL_ID = "scribe_v2"
PHRASE_GAP_SECONDS = 0.5


class TranscriptEngineError(ValueError):
    pass


def _media_item(root: Path, media_id: int) -> dict:
    items = {int(x["id"]): x for x in fetch_media_with_metadata(root)}
    item = items.get(int(media_id))
    if item is None:
        raise TranscriptEngineError(f"Média introuvable : id={media_id}")
    if item.get("kind") not in {"video", "audio"}:
        raise TranscriptEngineError(
            "La transcription cible un média vidéo ou audio."
        )
    return item


def _media_path(root: Path, item: dict) -> Path:
    root = root.resolve()
    path = (root / item["relative_path"]).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise TranscriptEngineError("Chemin média hors projet.") from exc
    if not path.exists() or not path.is_file():
        raise TranscriptEngineError(
            f"Fichier média absent : {item['relative_path']}"
        )
    return path


def _resolve_track_index(
    root: Path,
    media_id: int,
    track_index: int | None,
) -> int:
    if track_index is not None:
        return int(track_index)

    selected = selected_audio_track(root, media_id)
    if selected is not None:
        return int(selected["track_index"])

    tracks = list_audio_tracks(root, media_id)
    if not tracks:
        try:
            tracks = analyze_audio_tracks(root, media_id).get("tracks") or []
        except AudioTrackIntelligenceError as exc:
            raise TranscriptEngineError(str(exc)) from exc

    usable = [x for x in tracks if not x.get("silent")]
    if len(usable) == 1:
        return int(usable[0]["track_index"])
    if not usable:
        raise TranscriptEngineError(
            "Aucune piste audio exploitable n’a été détectée."
        )
    raise TranscriptEngineError(
        "Plusieurs pistes audio exploitables sont présentes. "
        "Choisir explicitement la piste de transcription."
    )


def _track_info(root: Path, media_id: int, track_index: int) -> dict:
    tracks = list_audio_tracks(root, media_id)
    if not tracks:
        tracks = analyze_audio_tracks(root, media_id).get("tracks") or []
    track = next(
        (x for x in tracks if int(x["track_index"]) == int(track_index)),
        None,
    )
    if track is None:
        raise TranscriptEngineError(
            f"Piste audio introuvable : {track_index}"
        )
    if track.get("silent"):
        raise TranscriptEngineError(
            "La piste choisie est silencieuse ; transcription refusée."
        )
    return track


def extract_transcription_audio(
    root: Path,
    media_id: int,
    *,
    track_index: int,
    force: bool = False,
) -> Path:
    item = _media_item(root, media_id)
    source = _media_path(root, item)
    _track_info(root, media_id, track_index)

    cache = root / "cache" / "transcripts" / "audio"
    cache.mkdir(parents=True, exist_ok=True)
    digest = str(item.get("sha256") or "unknown")[:16]
    out = cache / (
        f"media_{int(media_id):06d}_track_{int(track_index):02d}_{digest}.wav"
    )
    if out.exists() and out.stat().st_size > 44 and not force:
        return out

    cmd = [
        "ffmpeg",
        "-hide_banner", "-loglevel", "error",
        "-y",
        "-i", str(source),
        "-map", f"0:a:{int(track_index)}",
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(out),
    ]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise TranscriptEngineError("ffmpeg n’est pas disponible.") from exc
    if proc.returncode != 0:
        out.unlink(missing_ok=True)
        raise TranscriptEngineError(
            proc.stderr.strip() or "Extraction audio de transcription en échec."
        )
    return out


def _multipart_body(
    fields: dict[str, str],
    *,
    file_field: str,
    file_path: Path,
) -> tuple[bytes, str]:
    boundary = "----piste-studio-" + secrets.token_hex(12)
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            ).encode(),
            str(value).encode("utf-8"),
            b"\r\n",
        ])
    chunks.extend([
        f"--{boundary}\r\n".encode(),
        (
            f'Content-Disposition: form-data; name="{file_field}"; '
            f'filename="{file_path.name}"\r\n'
        ).encode(),
        b"Content-Type: audio/wav\r\n\r\n",
        file_path.read_bytes(),
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    return b"".join(chunks), boundary


def _elevenlabs_transcribe(
    audio_path: Path,
    *,
    model_id: str,
    api_key: str,
    language_code: str | None = None,
    num_speakers: int | None = None,
) -> dict:
    fields = {
        "model_id": model_id,
        "diarize": "true",
        "tag_audio_events": "true",
        "timestamps_granularity": "word",
        "no_verbatim": "false",
    }
    if language_code:
        fields["language_code"] = language_code
    if num_speakers is not None:
        n = max(1, min(32, int(num_speakers)))
        fields["num_speakers"] = str(n)

    body, boundary = _multipart_body(
        fields,
        file_field="file",
        file_path=audio_path,
    )
    request = urllib.request.Request(
        "https://api.elevenlabs.io/v1/speech-to-text",
        data=body,
        method="POST",
        headers={
            "xi-api-key": api_key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise TranscriptEngineError(
            f"ElevenLabs Scribe HTTP {exc.code}: {detail[:500]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise TranscriptEngineError(
            f"ElevenLabs Scribe inaccessible : {exc.reason}"
        ) from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise TranscriptEngineError(
            "Réponse Scribe non JSON."
        ) from exc


def normalize_words(raw: dict) -> list[dict]:
    result = []
    for item in raw.get("words") or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("type") or "word")
        text = str(item.get("text") or "")
        try:
            start = (
                float(item["start"])
                if item.get("start") is not None
                else None
            )
            end = (
                float(item["end"])
                if item.get("end") is not None
                else None
            )
        except (TypeError, ValueError):
            start = end = None
        result.append({
            "text": text,
            "type": kind,
            "start": start,
            "end": end,
            "speaker_id": item.get("speaker_id"),
            "logprob": item.get("logprob"),
        })
    return result


def build_phrases(
    words: list[dict],
    *,
    gap_seconds: float = PHRASE_GAP_SECONDS,
) -> list[dict]:
    phrases: list[dict] = []
    current: list[dict] = []
    current_speaker = None
    previous_end = None

    def flush() -> None:
        nonlocal current, current_speaker, previous_end
        timed = [
            x for x in current
            if x.get("start") is not None and x.get("end") is not None
        ]
        if not timed:
            current = []
            current_speaker = None
            previous_end = None
            return
        text = "".join(
            x.get("text", "")
            if x.get("type") == "spacing"
            else (
                x.get("text", "")
                if not current[:i]
                or current[i - 1].get("type") == "spacing"
                or str(x.get("text", "")).startswith(("'", "’", ",", ".", "!", "?", ";", ":"))
                else " " + x.get("text", "")
            )
            for i, x in enumerate(current)
        ).strip()
        phrases.append({
            "index": len(phrases),
            "start": round(float(timed[0]["start"]), 4),
            "end": round(float(timed[-1]["end"]), 4),
            "duration": round(
                float(timed[-1]["end"]) - float(timed[0]["start"]), 4
            ),
            "speaker_id": current_speaker,
            "text": text,
            "word_count": sum(
                1 for x in current if x.get("type") == "word"
            ),
            "events": [
                x.get("text")
                for x in current
                if x.get("type") not in {"word", "spacing"}
                and x.get("text")
            ],
        })
        current = []
        current_speaker = None
        previous_end = None

    for word in words:
        if word.get("type") == "spacing":
            if current:
                current.append(word)
            continue
        if word.get("start") is None or word.get("end") is None:
            continue
        speaker = word.get("speaker_id")
        gap = (
            float(word["start"]) - float(previous_end)
            if previous_end is not None
            else 0.0
        )
        speaker_changed = (
            current
            and speaker is not None
            and current_speaker is not None
            and speaker != current_speaker
        )
        if current and (gap >= gap_seconds or speaker_changed):
            flush()
        if not current:
            current_speaker = speaker
        current.append(word)
        previous_end = float(word["end"])
    flush()
    return phrases


def _store_transcript(
    root: Path,
    media_id: int,
    track_index: int,
    *,
    provider: str,
    model_id: str,
    source_sha256: str,
    raw: dict,
) -> dict:
    words = normalize_words(raw)
    phrases = build_phrases(words)
    text_content = str(raw.get("text") or "").strip()
    if not text_content:
        text_content = " ".join(
            p["text"] for p in phrases if p.get("text")
        ).strip()

    conn = connect(root / "media.sqlite")
    try:
        conn.execute(
            """
            INSERT INTO transcripts(
              media_id, audio_track_index, provider, model_id, source_sha256,
              status, language_code, language_probability, text_content,
              words_json, phrases_json, raw_json
            )
            VALUES (?, ?, ?, ?, ?, 'READY', ?, ?, ?, ?, ?, ?)
            ON CONFLICT(
              media_id, audio_track_index, provider, model_id, source_sha256
            ) DO UPDATE SET
              status='READY',
              language_code=excluded.language_code,
              language_probability=excluded.language_probability,
              text_content=excluded.text_content,
              words_json=excluded.words_json,
              phrases_json=excluded.phrases_json,
              raw_json=excluded.raw_json,
              updated_at=CURRENT_TIMESTAMP
            """,
            (
                int(media_id),
                int(track_index),
                provider,
                model_id,
                source_sha256,
                raw.get("language_code"),
                raw.get("language_probability"),
                text_content,
                json.dumps(words, ensure_ascii=False),
                json.dumps(phrases, ensure_ascii=False),
                json.dumps(raw, ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return get_transcript(
        root,
        media_id,
        track_index=track_index,
        provider=provider,
        model_id=model_id,
    ) or {}


def _decode_transcript_row(row) -> dict:
    out = dict(row)
    for field, target, fallback in (
        ("words_json", "words", []),
        ("phrases_json", "phrases", []),
        ("raw_json", "raw", {}),
    ):
        try:
            out[target] = json.loads(out.pop(field))
        except Exception:
            out[target] = fallback
    return out


def get_transcript(
    root: Path,
    media_id: int,
    *,
    track_index: int | None = None,
    provider: str | None = None,
    model_id: str | None = None,
) -> dict | None:
    clauses = ["media_id=?", "status='READY'"]
    params: list[object] = [int(media_id)]
    if track_index is not None:
        clauses.append("audio_track_index=?")
        params.append(int(track_index))
    if provider:
        clauses.append("provider=?")
        params.append(provider)
    if model_id:
        clauses.append("model_id=?")
        params.append(model_id)
    conn = connect(root / "media.sqlite")
    try:
        row = conn.execute(
            "SELECT * FROM transcripts WHERE "
            + " AND ".join(clauses)
            + " ORDER BY updated_at DESC, id DESC LIMIT 1",
            tuple(params),
        ).fetchone()
    finally:
        conn.close()
    return _decode_transcript_row(row) if row else None


def list_transcripts(root: Path, media_id: int | None = None) -> list[dict]:
    conn = connect(root / "media.sqlite")
    try:
        if media_id is None:
            rows = conn.execute(
                "SELECT * FROM transcripts ORDER BY media_id, id DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM transcripts WHERE media_id=? "
                "ORDER BY id DESC",
                (int(media_id),),
            ).fetchall()
    finally:
        conn.close()
    return [_decode_transcript_row(row) for row in rows]


def import_transcript_payload(
    root: Path,
    media_id: int,
    payload: dict,
    *,
    track_index: int | None = None,
    provider: str = "import",
    model_id: str = "external",
) -> dict:
    item = _media_item(root, media_id)
    resolved_track = _resolve_track_index(root, media_id, track_index)
    _track_info(root, media_id, resolved_track)
    return _store_transcript(
        root,
        media_id,
        resolved_track,
        provider=provider,
        model_id=model_id,
        source_sha256=str(item.get("sha256") or "unknown"),
        raw=payload,
    )


def transcribe_media(
    root: Path,
    media_id: int,
    *,
    track_index: int | None = None,
    provider: str = DEFAULT_PROVIDER,
    model_id: str = DEFAULT_MODEL_ID,
    language_code: str | None = None,
    num_speakers: int | None = None,
    force: bool = False,
    allow_network: bool = False,
) -> dict:
    item = _media_item(root, media_id)
    resolved_track = _resolve_track_index(root, media_id, track_index)
    _track_info(root, media_id, resolved_track)
    source_sha = str(item.get("sha256") or "unknown")

    existing = get_transcript(
        root,
        media_id,
        track_index=resolved_track,
        provider=provider,
        model_id=model_id,
    )
    if (
        existing
        and existing.get("source_sha256") == source_sha
        and not force
    ):
        existing["cached"] = True
        return existing

    if provider != "elevenlabs":
        raise TranscriptEngineError(
            f"Provider de transcription non pris en charge : {provider}"
        )
    if not allow_network:
        raise TranscriptEngineError(
            "La transcription externe exige allow_network=true. "
            "Aucun média n’est envoyé sans consentement explicite."
        )

    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise TranscriptEngineError(
            "ELEVENLABS_API_KEY est absent de l’environnement."
        )

    audio_path = extract_transcription_audio(
        root,
        media_id,
        track_index=resolved_track,
        force=force,
    )
    raw = _elevenlabs_transcribe(
        audio_path,
        model_id=model_id,
        api_key=api_key,
        language_code=language_code,
        num_speakers=num_speakers,
    )
    result = _store_transcript(
        root,
        media_id,
        resolved_track,
        provider=provider,
        model_id=model_id,
        source_sha256=source_sha,
        raw=raw,
    )
    result["cached"] = False
    result["engine_version"] = TRANSCRIPT_ENGINE_VERSION
    result["policy"] = {
        "network_requires_explicit_consent": True,
        "verbatim_fillers_preserved": True,
        "word_timestamps": True,
        "speaker_diarization": True,
        "source_media_unchanged": True,
    }
    return result
