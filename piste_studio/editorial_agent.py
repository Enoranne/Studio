from __future__ import annotations

from copy import deepcopy
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
import json
import re

from .audio_tracks import list_audio_tracks
from .db import connect
from .editorial import list_editorial_ranges
from .history import create_checkpoint
from .locks import check_operation
from .media_intelligence import get_media_analysis
from .metadata import fetch_media_with_metadata
from .semantic_vision import (
    list_semantic_profiles,
    list_targeted_semantic_references,
)
from .storyline import validate_locked_change
from .timeline import load_timeline, save_timeline, validate_timeline
from .transcript_engine import get_transcript

EDITORIAL_AGENT_VERSION = "0.26-editorial-agent-1"
FILLERS = {
    "euh", "heu", "hum", "hmm", "ben", "bah", "bon", "genre",
    "enfin", "voilà", "quoi",
    "um", "umm", "uh", "uhh", "erm", "hmm", "like",
}
_WORD_RE = re.compile(r"[\wÀ-ÖØ-öø-ÿ'’-]+", re.UNICODE)


class EditorialAgentError(ValueError):
    pass


def _timeline_hash(timeline: dict | None) -> str | None:
    if timeline is None:
        return None
    payload = {
        k: v for k, v in timeline.items()
        if k != "updated_at"
    }
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _normal_text(value: str) -> str:
    return " ".join(
        token.lower().strip("'’")
        for token in _WORD_RE.findall(value or "")
        if token.strip("'’")
    )


def _tokens(value: str) -> list[str]:
    return [
        token.lower().strip("'’")
        for token in _WORD_RE.findall(value or "")
        if token.strip("'’")
    ]


def _overlap(a0: float, a1: float, b0: float, b1: float) -> bool:
    return max(a0, b0) < min(a1, b1)


def _latest_transcript(root: Path, media_id: int) -> dict:
    transcript = get_transcript(root, media_id)
    if not transcript:
        raise EditorialAgentError(
            f"Transcript requis pour le média {media_id}."
        )
    return transcript


def transcript_candidates(root: Path, media_id: int) -> dict:
    transcript = _latest_transcript(root, media_id)
    phrases = transcript.get("phrases") or []
    words = transcript.get("words") or []

    silences = []
    previous = None
    for phrase in phrases:
        if previous is not None:
            gap = float(phrase["start"]) - float(previous["end"])
            if gap >= 0.15:
                silences.append({
                    "kind": "silence",
                    "start": round(float(previous["end"]), 4),
                    "end": round(float(phrase["start"]), 4),
                    "duration": round(gap, 4),
                    "strength": (
                        "clean"
                        if gap >= 0.4
                        else "review"
                    ),
                    "reason": (
                        "Pause >= 400 ms : candidat de coupe propre."
                        if gap >= 0.4
                        else "Pause courte : vérification visuelle recommandée."
                    ),
                })
        previous = phrase

    fillers = []
    for word in words:
        if word.get("type") != "word":
            continue
        token = _normal_text(str(word.get("text") or ""))
        if token in FILLERS and word.get("start") is not None:
            fillers.append({
                "kind": "filler",
                "text": str(word.get("text") or ""),
                "start": float(word["start"]),
                "end": float(word.get("end") or word["start"]),
                "speaker_id": word.get("speaker_id"),
                "reason": "Disfluence détectée ; jamais supprimée automatiquement.",
            })

    retakes = []
    for i, left in enumerate(phrases):
        left_text = _normal_text(str(left.get("text") or ""))
        if len(left_text) < 12:
            continue
        for right in phrases[i + 1:]:
            right_text = _normal_text(str(right.get("text") or ""))
            if len(right_text) < 12:
                continue
            ratio = SequenceMatcher(
                None,
                left_text,
                right_text,
            ).ratio()
            if ratio >= 0.78:
                retakes.append({
                    "kind": "retake",
                    "similarity": round(ratio, 4),
                    "first": {
                        "start": left["start"],
                        "end": left["end"],
                        "text": left.get("text"),
                    },
                    "second": {
                        "start": right["start"],
                        "end": right["end"],
                        "text": right.get("text"),
                    },
                    "reason": "Formulation proche : prises alternatives possibles.",
                })

    return {
        "media_id": int(media_id),
        "transcript_id": transcript.get("id"),
        "silence_candidates": silences,
        "filler_candidates": fillers,
        "retake_candidates": retakes,
        "policy": {
            "suggestions_only": True,
            "automatic_cut": False,
            "automatic_filler_removal": False,
        },
    }


def build_ai_timeline_view(root: Path, media_id: int) -> dict:
    transcript = get_transcript(root, media_id)
    analysis = get_media_analysis(root, media_id) or {}
    semantic_profiles = list_semantic_profiles(root)
    semantic = semantic_profiles.get(int(media_id))
    references = list_targeted_semantic_references(
        root,
        media_id=int(media_id),
    )
    candidates = (
        transcript_candidates(root, media_id)
        if transcript
        else {
            "silence_candidates": [],
            "filler_candidates": [],
            "retake_candidates": [],
        }
    )
    return {
        "version": EDITORIAL_AGENT_VERSION,
        "media_id": int(media_id),
        "technical": analysis.get("technical") or {},
        "filmstrip_path": analysis.get("filmstrip_path"),
        "audio_tracks": list_audio_tracks(root, media_id),
        "transcript": (
            {
                "id": transcript.get("id"),
                "language_code": transcript.get("language_code"),
                "text": transcript.get("text_content"),
                "phrases": transcript.get("phrases") or [],
                "words": transcript.get("words") or [],
            }
            if transcript
            else None
        ),
        "semantic": (
            {
                "status": semantic.get("status"),
                "provider": semantic.get("provider"),
                "model_id": semantic.get("model_id"),
                "frame_count": semantic.get("frame_count"),
            }
            if semantic
            else None
        ),
        "targeted_references": [
            {
                "id": row.get("id"),
                "tag": row.get("tag"),
                "facet": row.get("facet"),
                "timestamp_seconds": row.get("timestamp_seconds"),
                "group_name": row.get("group_name"),
                "quality": row.get("quality"),
            }
            for row in references
        ],
        "cut_candidates": {
            "silence": candidates.get("silence_candidates") or [],
            "filler": candidates.get("filler_candidates") or [],
            "retake": candidates.get("retake_candidates") or [],
        },
        "policy": {
            "compact_machine_readable_view": True,
            "source_media_unchanged": True,
            "storyline_unchanged": True,
        },
    }


def compare_takes(
    root: Path,
    media_ids: list[int],
    *,
    threshold: float = 0.72,
    max_pairs: int = 40,
) -> dict:
    ids = [int(x) for x in dict.fromkeys(media_ids)]
    if len(ids) < 2:
        raise EditorialAgentError(
            "Comparer au moins deux médias."
        )
    transcripts = {
        media_id: _latest_transcript(root, media_id)
        for media_id in ids
    }
    matches = []
    for left_index, left_id in enumerate(ids):
        for right_id in ids[left_index + 1:]:
            left_phrases = transcripts[left_id].get("phrases") or []
            right_phrases = transcripts[right_id].get("phrases") or []
            for left in left_phrases:
                a = _normal_text(str(left.get("text") or ""))
                if len(a) < 10:
                    continue
                best = None
                for right in right_phrases:
                    b = _normal_text(str(right.get("text") or ""))
                    if len(b) < 10:
                        continue
                    ratio = SequenceMatcher(None, a, b).ratio()
                    if best is None or ratio > best[0]:
                        best = (ratio, right)
                if best and best[0] >= threshold:
                    matches.append({
                        "left_media_id": left_id,
                        "right_media_id": right_id,
                        "similarity": round(best[0], 4),
                        "left": {
                            "start": left.get("start"),
                            "end": left.get("end"),
                            "text": left.get("text"),
                            "speaker_id": left.get("speaker_id"),
                        },
                        "right": {
                            "start": best[1].get("start"),
                            "end": best[1].get("end"),
                            "text": best[1].get("text"),
                            "speaker_id": best[1].get("speaker_id"),
                        },
                    })
    matches.sort(key=lambda x: x["similarity"], reverse=True)
    return {
        "media_ids": ids,
        "threshold": float(threshold),
        "matches": matches[: max(1, int(max_pairs))],
        "policy": {
            "comparison_is_advisory": True,
            "best_take_not_selected_automatically": True,
        },
    }


def _media_map(root: Path) -> dict[int, dict]:
    return {
        int(item["id"]): item
        for item in fetch_media_with_metadata(root)
    }


def _phrase_overlaps_ranges(
    phrase: dict,
    ranges: list[dict],
    kind: str,
) -> bool:
    return any(
        row.get("kind") == kind
        and _overlap(
            float(phrase["start"]),
            float(phrase["end"]),
            float(row["source_in"]),
            float(row["source_out"]),
        )
        for row in ranges
    )


def _phrase_score(
    phrase: dict,
    media: dict,
    ranges: list[dict],
) -> float:
    duration = max(
        0.1,
        float(phrase["end"]) - float(phrase["start"]),
    )
    tokens = _tokens(str(phrase.get("text") or ""))
    density = min(5.0, len(tokens) / duration)
    filler_ratio = (
        sum(1 for token in tokens if token in FILLERS)
        / max(1, len(tokens))
    )
    score = density
    score += float(media.get("rating") or 0) * 0.6
    score += 1.5 if media.get("canonical") else 0.0
    score += 2.5 if _phrase_overlaps_ranges(
        phrase,
        ranges,
        "favorite",
    ) else 0.0
    score -= filler_ratio * 4.0
    return score


def _strategy_text(
    *,
    brief: str,
    target_seconds: float,
    media_count: int,
    transcript_count: int,
    candidate_count: int,
) -> str:
    direction = brief.strip() or (
        "Construire un montage resserré à partir des meilleures plages "
        "documentées, en préservant la continuité et les respirations utiles."
    )
    return (
        f"Objectif : environ {target_seconds:.0f} s. "
        f"{direction} "
        f"La proposition s’appuie sur {transcript_count}/{media_count} "
        f"médias transcrits et {candidate_count} plages verbales candidates. "
        "Les coupes privilégient les limites de mots et les pauses propres ; "
        "les favoris éditoriaux sont favorisés et les rejets exclus. "
        "Aucune décision n’est appliquée à la Storyline avant validation humaine."
    )


def draft_editorial_strategy(
    root: Path,
    *,
    edit_name: str,
    media_ids: list[int],
    target_seconds: float,
    brief: str = "",
    max_spoiler: int | None = None,
) -> dict:
    media = _media_map(root)
    ids = [int(x) for x in dict.fromkeys(media_ids)]
    eligible = []
    transcript_count = 0
    candidate_count = 0
    for media_id in ids:
        item = media.get(media_id)
        if not item or item.get("kind") != "video":
            continue
        if max_spoiler is not None and int(
            item.get("spoiler_level") or 0
        ) > int(max_spoiler):
            continue
        transcript = get_transcript(root, media_id)
        if transcript:
            transcript_count += 1
            candidate_count += len(transcript.get("phrases") or [])
        eligible.append(media_id)

    strategy = {
        "version": EDITORIAL_AGENT_VERSION,
        "edit_name": edit_name,
        "brief": brief,
        "target_seconds": float(target_seconds),
        "eligible_media_ids": eligible,
        "strategy_text": _strategy_text(
            brief=brief,
            target_seconds=float(target_seconds),
            media_count=len(eligible),
            transcript_count=transcript_count,
            candidate_count=candidate_count,
        ),
        "principles": [
            "human_validation_required",
            "word_boundaries",
            "preserve_useful_pauses",
            "respect_editorial_rejects",
            "prefer_editorial_favorites",
            "no_silent_storyline_mutation",
        ],
    }
    record = _create_proposal_record(
        root,
        edit_name=edit_name,
        proposal_kind="STRATEGY",
        brief=brief,
        base_timeline=load_timeline(root, edit_name),
        proposal=strategy,
    )
    strategy["proposal_id"] = record["id"]
    return strategy


def _select_segments(
    root: Path,
    media_ids: list[int],
    *,
    target_seconds: float,
    max_spoiler: int | None,
) -> list[dict]:
    media = _media_map(root)
    ranges_by_media: dict[int, list[dict]] = {}
    for row in list_editorial_ranges(root):
        ranges_by_media.setdefault(int(row["media_id"]), []).append(row)

    pool = []
    order_map = {
        int(media_id): index
        for index, media_id in enumerate(media_ids)
    }
    for media_id in media_ids:
        media_id = int(media_id)
        item = media.get(media_id)
        if not item or item.get("kind") != "video":
            continue
        if max_spoiler is not None and int(
            item.get("spoiler_level") or 0
        ) > int(max_spoiler):
            continue
        transcript = get_transcript(root, media_id)
        if not transcript:
            continue
        ranges = ranges_by_media.get(media_id, [])
        for phrase in transcript.get("phrases") or []:
            if _phrase_overlaps_ranges(phrase, ranges, "reject"):
                continue
            duration = float(phrase["end"]) - float(phrase["start"])
            if duration < 0.35:
                continue
            pool.append({
                "media_id": media_id,
                "source_start": float(phrase["start"]),
                "source_end": float(phrase["end"]),
                "duration": duration,
                "quote": phrase.get("text"),
                "speaker_id": phrase.get("speaker_id"),
                "score": _phrase_score(phrase, item, ranges),
                "order": order_map[media_id],
                "media_title": (
                    item.get("title")
                    or Path(item["relative_path"]).stem
                ),
            })

    pool.sort(key=lambda x: x["score"], reverse=True)
    chosen = []
    total = 0.0
    for item in pool:
        if total >= target_seconds:
            break
        remaining = target_seconds - total
        if remaining < 0.35:
            break
        if item["duration"] > remaining + 0.4:
            continue
        chosen.append(item)
        total += item["duration"]

    chosen.sort(
        key=lambda x: (
            x["order"],
            x["source_start"],
        )
    )
    return chosen


def _candidate_timeline(
    root: Path,
    base: dict,
    segments: list[dict],
) -> dict:
    doc = deepcopy(base)
    connected = [
        clip for clip in doc.get("clips", [])
        if clip.get("track") != "video"
        and clip.get("parentClipId")
    ]
    if connected:
        names = ", ".join(
            str(x.get("id"))
            for x in connected[:5]
        )
        raise EditorialAgentError(
            "La proposition automatique ne remplace pas une Storyline "
            "qui possède déjà des éléments connectés. "
            f"Éléments concernés : {names}."
        )

    start = float(
        (doc.get("storyline") or {}).get("start", 0.0)
    )
    available = float(doc["duration_seconds"]) - start
    total = sum(float(x["duration"]) for x in segments)
    if total > available + 1e-6:
        raise EditorialAgentError(
            "La proposition dépasse la durée disponible de la timeline."
        )

    preserved = [
        clip for clip in doc.get("clips", [])
        if clip.get("track") != "video"
    ]
    story = []
    cursor = start
    for index, segment in enumerate(segments, start=1):
        duration = round(float(segment["duration"]), 6)
        story.append({
            "id": (
                f"agent_v{index:03d}_m{int(segment['media_id'])}"
            ),
            "track": "video",
            "label": str(segment.get("media_title") or "Plan proposé"),
            "start": round(cursor, 6),
            "duration": duration,
            "sourceStart": round(float(segment["source_start"]), 6),
            "mediaDbId": int(segment["media_id"]),
            "agentProposal": True,
            "agentReason": (
                f"score={float(segment['score']):.2f}; "
                f"quote={str(segment.get('quote') or '')[:180]}"
            ),
        })
        cursor += duration

    doc["clips"] = preserved + story
    doc["storyline"] = {
        "mode": "magnetic",
        "start": round(start, 6),
    }
    return validate_timeline(root, doc)


def propose_edit(
    root: Path,
    *,
    edit_name: str,
    media_ids: list[int],
    target_seconds: float,
    brief: str = "",
    max_spoiler: int | None = None,
) -> dict:
    if target_seconds <= 0:
        raise EditorialAgentError("target_seconds doit être > 0.")
    base = load_timeline(root, edit_name)
    if base is None:
        raise EditorialAgentError(
            "Une timeline de travail est requise avant de créer "
            "une proposition virtuelle."
        )
    segments = _select_segments(
        root,
        [int(x) for x in media_ids],
        target_seconds=float(target_seconds),
        max_spoiler=max_spoiler,
    )
    if not segments:
        raise EditorialAgentError(
            "Aucune plage transcript exploitable pour cette proposition."
        )
    candidate = _candidate_timeline(root, base, segments)
    proposal = {
        "version": EDITORIAL_AGENT_VERSION,
        "edit_name": edit_name,
        "brief": brief,
        "target_seconds": float(target_seconds),
        "actual_seconds": round(
            sum(float(x["duration"]) for x in segments),
            4,
        ),
        "segments": segments,
        "candidate_timeline": candidate,
        "policy": {
            "virtual_edl": True,
            "storyline_unchanged": True,
            "human_validation_required": True,
            "lock_check_on_apply": True,
            "checkpoint_before_apply": True,
        },
    }
    record = _create_proposal_record(
        root,
        edit_name=edit_name,
        proposal_kind="PROPOSED_EDIT",
        brief=brief,
        base_timeline=base,
        proposal=proposal,
    )
    proposal["proposal_id"] = record["id"]
    return proposal


def _create_proposal_record(
    root: Path,
    *,
    edit_name: str,
    proposal_kind: str,
    brief: str,
    base_timeline: dict | None,
    proposal: dict,
) -> dict:
    conn = connect(root / "media.sqlite")
    try:
        cur = conn.execute(
            """
            INSERT INTO editorial_agent_proposals(
              edit_name, proposal_kind, status, brief,
              base_timeline_hash, proposal_json
            )
            VALUES (?, ?, 'PENDING', ?, ?, ?)
            """,
            (
                str(edit_name),
                str(proposal_kind),
                brief or None,
                _timeline_hash(base_timeline),
                json.dumps(proposal, ensure_ascii=False),
            ),
        )
        proposal_id = int(cur.lastrowid)
        conn.commit()
    finally:
        conn.close()
    return get_proposal(root, proposal_id)


def _decode_proposal(row) -> dict:
    out = dict(row)
    try:
        out["proposal"] = json.loads(out.pop("proposal_json"))
    except Exception:
        out["proposal"] = {}
    return out


def get_proposal(root: Path, proposal_id: int) -> dict:
    conn = connect(root / "media.sqlite")
    try:
        row = conn.execute(
            "SELECT * FROM editorial_agent_proposals WHERE id=?",
            (int(proposal_id),),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise EditorialAgentError(
            f"Proposition introuvable : {proposal_id}"
        )
    return _decode_proposal(row)


def list_proposals(
    root: Path,
    *,
    edit_name: str | None = None,
    status: str | None = None,
) -> list[dict]:
    clauses = []
    params: list[object] = []
    if edit_name:
        clauses.append("edit_name=?")
        params.append(edit_name)
    if status:
        clauses.append("status=?")
        params.append(status.upper())
    query = "SELECT * FROM editorial_agent_proposals"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id DESC"
    conn = connect(root / "media.sqlite")
    try:
        rows = conn.execute(query, tuple(params)).fetchall()
    finally:
        conn.close()
    return [_decode_proposal(row) for row in rows]


def reject_proposal(root: Path, proposal_id: int) -> dict:
    current = get_proposal(root, proposal_id)
    if current["status"] == "APPLIED":
        raise EditorialAgentError(
            "Une proposition déjà appliquée ne peut pas être rejetée."
        )
    conn = connect(root / "media.sqlite")
    try:
        conn.execute(
            "UPDATE editorial_agent_proposals "
            "SET status='REJECTED', updated_at=CURRENT_TIMESTAMP "
            "WHERE id=?",
            (int(proposal_id),),
        )
        conn.commit()
    finally:
        conn.close()
    return get_proposal(root, proposal_id)


def apply_proposal(
    root: Path,
    proposal_id: int,
    *,
    confirm: bool,
    explicit_soft_unlock: bool = False,
) -> dict:
    if not confirm:
        raise EditorialAgentError(
            "Confirmation humaine explicite requise."
        )
    record = get_proposal(root, proposal_id)
    if record["proposal_kind"] != "PROPOSED_EDIT":
        raise EditorialAgentError(
            "Seule une PROPOSED_EDIT peut être appliquée."
        )
    if record["status"] != "PENDING":
        raise EditorialAgentError(
            f"Statut non applicable : {record['status']}."
        )
    proposal = record.get("proposal") or {}
    candidate = proposal.get("candidate_timeline")
    if not isinstance(candidate, dict):
        raise EditorialAgentError(
            "La proposition ne contient pas de timeline candidate."
        )

    current = load_timeline(root, record["edit_name"])
    if current is None:
        raise EditorialAgentError("Timeline de travail introuvable.")
    if _timeline_hash(current) != record.get("base_timeline_hash"):
        raise EditorialAgentError(
            "La Storyline a changé depuis la proposition ; "
            "recalcul requis."
        )

    clean = validate_timeline(root, candidate)
    validate_locked_change(root, current, clean)

    story = [
        clip for clip in clean.get("clips", [])
        if clip.get("track") == "video"
    ]
    if story:
        start = min(float(x["start"]) for x in story)
        end = max(
            float(x["start"]) + float(x["duration"])
            for x in story
        )
        decision = check_operation(
            root,
            operation="edit",
            start=start,
            end=end,
            target="timeline",
            explicit_soft_unlock=explicit_soft_unlock,
        )
        if not decision.allowed:
            raise EditorialAgentError(decision.reason)

    create_checkpoint(
        root,
        current,
        edit_name=record["edit_name"],
        reason=f"Editorial Agent · proposition {proposal_id}",
    )
    save_timeline(root, clean)

    conn = connect(root / "media.sqlite")
    try:
        conn.execute(
            "UPDATE editorial_agent_proposals "
            "SET status='APPLIED', updated_at=CURRENT_TIMESTAMP "
            "WHERE id=?",
            (int(proposal_id),),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "ok": True,
        "proposal": get_proposal(root, proposal_id),
        "timeline": load_timeline(root, record["edit_name"]),
        "policy": {
            "explicit_human_confirmation": True,
            "checkpoint_created": True,
            "locks_checked": True,
        },
    }
