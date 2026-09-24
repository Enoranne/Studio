from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import math
import re
import unicodedata

from .editorial import list_editorial_ranges
from .editorial_agent import create_virtual_edit_proposal
from .editorial_vision import EditorialVisionError, suggest_editorial_windows
from .metadata import fetch_media_with_metadata
from .semantic_vision import (
    LocalClipProvider,
    SemanticVisionError,
    cosine_similarity,
    list_semantic_profiles,
    list_targeted_semantic_references,
)
from .timeline import load_timeline, validate_timeline
from .transcript_engine import get_transcript


VOICE_VISUAL_VERSION = "0.27-voice-visual-1"
_TOKEN_RE = re.compile(r"[\wÀ-ÖØ-öø-ÿ'’-]+", re.UNICODE)
_STOPWORDS = {
    "a", "à", "au", "aux", "avec", "ce", "ces", "dans", "de", "des", "du",
    "elle", "en", "et", "eux", "il", "je", "la", "le", "les", "leur", "lui",
    "ma", "mais", "me", "mes", "moi", "mon", "ne", "nos", "notre", "nous",
    "on", "ou", "où", "par", "pas", "pour", "qu", "que", "qui", "sa", "se",
    "ses", "son", "sur", "ta", "te", "tes", "toi", "ton", "tu", "un", "une",
    "vos", "votre", "vous", "y", "d", "l", "c", "j", "m", "n", "s", "t",
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "this", "that", "it", "i", "you", "we", "they", "he", "she", "my",
    "your", "our", "their", "is", "are", "was", "were", "be", "been",
}
_FACETS = {"character", "prop", "decor", "look"}


class VoiceVisualError(ValueError):
    pass


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _tokens(value: str) -> list[str]:
    out = []
    for token in _TOKEN_RE.findall(_fold(value)):
        clean = token.strip("'’-_")
        if len(clean) < 2 or clean in _STOPWORDS:
            continue
        out.append(clean)
    return out


def _media_map(root: Path) -> dict[int, dict]:
    return {
        int(item["id"]): dict(item)
        for item in fetch_media_with_metadata(root)
    }


def _media_text(item: dict, refs: list[dict] | None = None) -> str:
    values = [
        str(item.get("title") or ""),
        str(item.get("description") or ""),
        Path(str(item.get("relative_path") or "")).stem.replace("_", " "),
    ]
    for tag in item.get("tags") or []:
        raw = str(tag)
        values.append(raw)
        if ":" in raw:
            values.append(raw.split(":", 1)[1])
    for ref in refs or []:
        values.append(str(ref.get("tag") or ""))
        if ":" in str(ref.get("tag") or ""):
            values.append(str(ref["tag"]).split(":", 1)[1])
        values.append(str(ref.get("group_name") or ""))
    return " ".join(v for v in values if v)


def _lexical_similarity(intent_text: str, media_text: str) -> float:
    left = set(_tokens(intent_text))
    right = set(_tokens(media_text))
    if not left or not right:
        return 0.0
    overlap = left & right
    if not overlap:
        return 0.0
    recall = len(overlap) / len(left)
    precision = len(overlap) / len(right)
    return min(1.0, 0.75 * recall + 0.25 * precision)


def _structured_tags(item: dict) -> set[str]:
    out = set()
    for raw in item.get("tags") or []:
        tag = str(raw).strip().lower()
        if ":" not in tag:
            continue
        facet, value = tag.split(":", 1)
        if facet in _FACETS and value.strip():
            out.add(f"{facet}:{value.strip()}")
    return out


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def _editorial_signal(
    ranges: list[dict],
    *,
    source_in: float,
    source_out: float,
) -> dict:
    duration = max(0.001, source_out - source_in)
    favorite = 0.0
    reject = 0.0
    for row in ranges:
        amount = _overlap(
            source_in,
            source_out,
            float(row["source_in"]),
            float(row["source_out"]),
        )
        if amount <= 0:
            continue
        if row.get("kind") == "favorite":
            favorite += amount
        elif row.get("kind") == "reject":
            reject += amount
    return {
        "favorite_ratio": min(1.0, favorite / duration),
        "reject_ratio": min(1.0, reject / duration),
    }


def _window_refs(refs: list[dict], source_in: float, source_out: float) -> list[dict]:
    return [
        ref for ref in refs
        if source_in - 1e-6
        <= float(ref.get("timestamp_seconds") or 0.0)
        <= source_out + 1e-6
    ]


def _weighted_mean(vectors: list[tuple[list[float], float]]) -> list[float] | None:
    valid = [
        (vector, max(0.01, float(weight)))
        for vector, weight in vectors
        if vector
    ]
    if not valid:
        return None
    size = len(valid[0][0])
    if any(len(vector) != size for vector, _weight in valid):
        return None
    total = sum(weight for _vector, weight in valid)
    mean = [
        sum(float(vector[i]) * weight for vector, weight in valid) / total
        for i in range(size)
    ]
    norm = math.sqrt(sum(value * value for value in mean))
    if norm <= 0:
        return None
    return [value / norm for value in mean]


def _reference_embedding(refs: list[dict]) -> list[float] | None:
    quality = {"primary": 1.5, "secondary": 1.0, "low": 0.5}
    return _weighted_mean([
        (
            [float(x) for x in (ref.get("embedding") or [])],
            quality.get(str(ref.get("quality") or "secondary").lower(), 1.0),
        )
        for ref in refs
    ])


def _embed_intents(
    texts: list[str],
    *,
    allow_model_download: bool,
) -> tuple[list[list[float]] | None, str | None]:
    if not texts:
        return [], None
    try:
        provider = LocalClipProvider()
        vectors = provider.embed_texts(
            texts,
            allow_model_download=allow_model_download,
        )
        return vectors, None
    except Exception as exc:
        return None, str(exc)


def _phrase_records(
    transcript: dict,
    *,
    phrase_indexes: list[int] | None = None,
    explicit_intents: dict[int, str] | None = None,
    max_phrases: int = 40,
) -> list[dict]:
    phrases = list(transcript.get("phrases") or [])
    if phrase_indexes is None:
        indexes = list(range(min(len(phrases), max(1, int(max_phrases)))))
    else:
        indexes = []
        for value in phrase_indexes:
            index = int(value)
            if index < 0 or index >= len(phrases):
                raise VoiceVisualError(f"Phrase VO introuvable : index={index}")
            if index not in indexes:
                indexes.append(index)

    explicit_intents = explicit_intents or {}
    out = []
    for index in indexes:
        phrase = phrases[index]
        text = str(phrase.get("text") or "").strip()
        if not text:
            continue
        intent = str(explicit_intents.get(index) or text).strip()
        out.append({
            "phrase_index": index,
            "start": float(phrase["start"]),
            "end": float(phrase["end"]),
            "duration": max(
                0.0,
                float(phrase["end"]) - float(phrase["start"]),
            ),
            "speaker_id": phrase.get("speaker_id"),
            "text": text,
            "intent_text": intent,
            "keywords": sorted(set(_tokens(intent))),
        })
    return out


def _preselect_visual_media(
    media: dict[int, dict],
    phrases: list[dict],
    *,
    visual_media_ids: list[int] | None,
    limit: int,
) -> list[dict]:
    allowed = (
        {int(x) for x in visual_media_ids}
        if visual_media_ids
        else None
    )
    videos = [
        item for item in media.values()
        if item.get("kind") == "video"
        and (allowed is None or int(item["id"]) in allowed)
    ]
    if visual_media_ids:
        missing = [
            int(x) for x in visual_media_ids
            if int(x) not in media
        ]
        if missing:
            raise VoiceVisualError(
                "Médias visuels introuvables : "
                + ", ".join(str(x) for x in missing)
            )

    combined_intent = " ".join(x["intent_text"] for x in phrases)
    ranked = []
    for item in videos:
        lexical = _lexical_similarity(combined_intent, _media_text(item))
        metadata_quality = (
            min(1.0, float(item.get("rating") or 0) / 5.0) * 0.6
            + (0.4 if item.get("canonical") else 0.0)
        )
        ranked.append((
            lexical * 0.8 + metadata_quality * 0.2,
            int(item["id"]),
            item,
        ))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    max_items = max(1, min(int(limit), 60))
    return [item for _score, _id, item in ranked[:max_items]]


def _candidate_score(
    *,
    phrase: dict,
    item: dict,
    window: dict,
    intent_embedding: list[float] | None,
    profile_embedding: list[float] | None,
    window_refs: list[dict],
    editorial_ranges: list[dict],
) -> dict | None:
    source_in = float(window["source_in"])
    source_out = float(window["source_out"])
    duration = float(window["duration"])
    signal = _editorial_signal(
        editorial_ranges,
        source_in=source_in,
        source_out=source_out,
    )
    if signal["reject_ratio"] >= 0.5:
        return None

    refs = window_refs
    text_context = _media_text(item, refs)
    lexical = _lexical_similarity(phrase["intent_text"], text_context)

    semantic = None
    semantic_source = None
    if intent_embedding:
        ref_embedding = _reference_embedding(refs)
        candidate_embedding = ref_embedding or profile_embedding
        if candidate_embedding:
            try:
                semantic = max(
                    0.0,
                    min(
                        1.0,
                        float(cosine_similarity(
                            intent_embedding,
                            candidate_embedding,
                        )),
                    ),
                )
                semantic_source = (
                    "targeted_references"
                    if ref_embedding
                    else "media_profile"
                )
            except Exception:
                semantic = None

    phrase_duration = max(0.35, float(phrase["duration"]))
    duration_fit = min(1.0, duration / phrase_duration)
    rating = min(1.0, float(item.get("rating") or 0) / 5.0)
    canon = 1.0 if item.get("canonical") else 0.0
    favorite = signal["favorite_ratio"]

    components = [
        ("lexical", lexical, 0.35),
        ("favorite", favorite, 0.15),
        ("duration_fit", duration_fit, 0.15),
        ("rating", rating, 0.10),
        ("canon", canon, 0.05),
    ]
    if semantic is not None:
        components.append(("semantic", semantic, 0.40))

    total_weight = sum(weight for _name, _value, weight in components)
    score = sum(value * weight for _name, value, weight in components) / total_weight

    reasons = []
    if lexical > 0:
        reasons.append(f"mots/intention {lexical:.2f}")
    if semantic is not None:
        reasons.append(f"vision sémantique {semantic:.2f}")
    if favorite > 0:
        reasons.append(f"favori {favorite:.2f}")
    if canon:
        reasons.append("canon")
    if duration_fit < 0.99:
        reasons.append("fenêtre plus courte que la phrase")
    if not reasons:
        reasons.append("candidat visuel générique à vérifier")

    return {
        "media_id": int(item["id"]),
        "media_title": (
            item.get("title")
            or Path(str(item.get("relative_path") or "")).stem
        ),
        "relative_path": item.get("relative_path"),
        "source_in": round(source_in, 4),
        "source_out": round(source_out, 4),
        "duration": round(duration, 4),
        "score": round(score, 5),
        "score_components": {
            "lexical": round(lexical, 5),
            "semantic": (
                round(semantic, 5)
                if semantic is not None
                else None
            ),
            "semantic_source": semantic_source,
            "favorite_ratio": round(favorite, 5),
            "duration_fit": round(duration_fit, 5),
            "rating": round(rating, 5),
            "canonical": bool(item.get("canonical")),
        },
        "tags": sorted(_structured_tags(item)),
        "targeted_reference_ids": [
            int(ref["id"])
            for ref in refs
            if ref.get("id") is not None
        ],
        "reason": " · ".join(reasons),
        "window_reason": window.get("reason"),
    }


def voice_visual_candidates(
    root: Path,
    *,
    voice_media_id: int,
    phrase_indexes: list[int] | None = None,
    explicit_intents: dict[int, str] | None = None,
    visual_media_ids: list[int] | None = None,
    per_phrase: int = 6,
    max_visual_media: int = 24,
    allow_model_download: bool = False,
) -> dict:
    root = root.expanduser().resolve()
    media = _media_map(root)
    voice = media.get(int(voice_media_id))
    if voice is None:
        raise VoiceVisualError(
            f"Média VO introuvable : id={voice_media_id}"
        )
    if voice.get("kind") not in {"audio", "video"}:
        raise VoiceVisualError(
            "La source VO doit être un média audio ou vidéo."
        )
    transcript = get_transcript(root, int(voice_media_id))
    if not transcript:
        raise VoiceVisualError(
            "Transcript requis sur la source VO avant recherche visuelle."
        )

    phrases = _phrase_records(
        transcript,
        phrase_indexes=phrase_indexes,
        explicit_intents=explicit_intents,
    )
    if not phrases:
        raise VoiceVisualError("Aucune phrase VO exploitable.")

    visual_media = _preselect_visual_media(
        media,
        phrases,
        visual_media_ids=visual_media_ids,
        limit=max_visual_media,
    )
    if not visual_media:
        raise VoiceVisualError("Aucun rush vidéo candidat.")

    text_embeddings, semantic_error = _embed_intents(
        [x["intent_text"] for x in phrases],
        allow_model_download=allow_model_download,
    )
    profiles = list_semantic_profiles(root)
    targeted = list_targeted_semantic_references(root)
    refs_by_media: dict[int, list[dict]] = {}
    for ref in targeted:
        refs_by_media.setdefault(int(ref["media_id"]), []).append(ref)
    ranges_by_media: dict[int, list[dict]] = {}
    for row in list_editorial_ranges(root):
        ranges_by_media.setdefault(int(row["media_id"]), []).append(row)

    # Scene detection is intentionally performed only for the preselected
    # visual catalogue, not for every video in a large project.
    windows_by_media: dict[int, list[dict]] = {}
    window_errors: list[dict] = []
    for item in visual_media:
        media_id = int(item["id"])
        try:
            result = suggest_editorial_windows(
                root,
                media_id,
                min_window_seconds=0.5,
                limit=20,
            )
            windows_by_media[media_id] = result.get("candidates") or []
        except Exception as exc:
            window_errors.append({
                "media_id": media_id,
                "error": str(exc),
            })
            duration = float(item.get("duration_seconds") or 0.0)
            if duration >= 0.5:
                windows_by_media[media_id] = [{
                    "source_in": 0.0,
                    "source_out": duration,
                    "duration": duration,
                    "reason": (
                        "Fenêtres visuelles indisponibles : "
                        "rush complet proposé en secours."
                    ),
                    "method": "metadata_duration_fallback",
                }]

    results = []
    max_candidates = max(1, min(int(per_phrase), 20))
    for phrase_pos, phrase in enumerate(phrases):
        intent_embedding = (
            text_embeddings[phrase_pos]
            if text_embeddings
            and phrase_pos < len(text_embeddings)
            else None
        )
        scored = []
        for item in visual_media:
            media_id = int(item["id"])
            profile = profiles.get(media_id) or {}
            profile_embedding = [
                float(x) for x in (profile.get("embedding") or [])
            ]
            refs = refs_by_media.get(media_id, [])
            ranges = ranges_by_media.get(media_id, [])
            for window in windows_by_media.get(media_id, []):
                win_refs = _window_refs(
                    refs,
                    float(window["source_in"]),
                    float(window["source_out"]),
                )
                candidate = _candidate_score(
                    phrase=phrase,
                    item=item,
                    window=window,
                    intent_embedding=intent_embedding,
                    profile_embedding=profile_embedding,
                    window_refs=win_refs,
                    editorial_ranges=ranges,
                )
                if candidate is not None:
                    scored.append(candidate)
        scored.sort(
            key=lambda x: (
                float(x["score"]),
                float(x["duration"]),
                -int(x["media_id"]),
            ),
            reverse=True,
        )
        results.append({
            **phrase,
            "candidates": scored[:max_candidates],
        })

    return {
        "version": VOICE_VISUAL_VERSION,
        "voice_media_id": int(voice_media_id),
        "voice_media_title": (
            voice.get("title")
            or Path(str(voice.get("relative_path") or "")).stem
        ),
        "transcript_id": transcript.get("id"),
        "phrases": results,
        "visual_media_considered": [int(x["id"]) for x in visual_media],
        "window_errors": window_errors,
        "semantic_text": {
            "available": text_embeddings is not None,
            "error": semantic_error,
            "model_download_allowed": bool(allow_model_download),
        },
        "policy": {
            "suggestions_only": True,
            "no_automatic_storyline_change": True,
            "human_validation_required": True,
            "local_semantic_text_only": True,
            "model_download_requires_explicit_opt_in": True,
        },
    }


def _continuity_bonus(left: dict | None, right: dict) -> tuple[float, list[str]]:
    if left is None:
        return 0.0, []
    a = set(left.get("tags") or [])
    b = set(right.get("tags") or [])
    shared = sorted(a & b)
    if not a or not b:
        return 0.0, shared
    facets_a = {tag.split(":", 1)[0] for tag in a if ":" in tag}
    facets_b = {tag.split(":", 1)[0] for tag in b if ":" in tag}
    conflicting_facets = 0
    for facet in facets_a & facets_b:
        av = {tag for tag in a if tag.startswith(facet + ":")}
        bv = {tag for tag in b if tag.startswith(facet + ":")}
        if av and bv and not (av & bv):
            conflicting_facets += 1
    bonus = min(0.12, 0.04 * len(shared)) - 0.06 * conflicting_facets
    return bonus, shared


def compare_visual_candidates(
    mapping: dict,
    *,
    phrase_index: int,
    limit: int = 6,
) -> dict:
    phrase = next(
        (
            item for item in mapping.get("phrases") or []
            if int(item["phrase_index"]) == int(phrase_index)
        ),
        None,
    )
    if phrase is None:
        raise VoiceVisualError(
            f"Phrase absente du mapping : {phrase_index}"
        )
    candidates = list(phrase.get("candidates") or [])[:max(1, int(limit))]
    if not candidates:
        return {
            "phrase_index": int(phrase_index),
            "text": phrase.get("text"),
            "candidates": [],
            "comparison": [],
        }

    comparison = []
    for candidate in candidates:
        row = {
            "media_id": candidate["media_id"],
            "source_in": candidate["source_in"],
            "source_out": candidate["source_out"],
            "score": candidate["score"],
            "against": [],
        }
        for other in candidates:
            if other is candidate:
                continue
            bonus, shared = _continuity_bonus(candidate, other)
            row["against"].append({
                "media_id": other["media_id"],
                "source_in": other["source_in"],
                "shared_tags": shared,
                "continuity_delta": round(bonus, 5),
            })
        comparison.append(row)
    return {
        "phrase_index": int(phrase_index),
        "text": phrase.get("text"),
        "candidates": candidates,
        "comparison": comparison,
        "policy": {
            "best_shot_not_selected_automatically": True,
        },
    }


def _voice_clip_mapping(
    timeline: dict,
    *,
    voice_media_id: int,
    first_source_time: float,
) -> dict | None:
    matches = []
    for clip in timeline.get("clips") or []:
        raw_id = clip.get("audioDbId")
        if raw_id is None and str(clip.get("track") or "").lower() != "video":
            raw_id = clip.get("mediaDbId")
        if raw_id is None:
            continue
        try:
            if int(raw_id) != int(voice_media_id):
                continue
        except (TypeError, ValueError):
            continue
        source_start = float(clip.get("sourceStart") or 0.0)
        source_end = source_start + float(clip.get("duration") or 0.0)
        if source_start - 1e-6 <= first_source_time <= source_end + 1e-6:
            matches.append(clip)
    if not matches:
        return None
    clip = sorted(matches, key=lambda x: float(x.get("start") or 0.0))[0]
    return {
        "clip_id": str(clip.get("id") or ""),
        "timeline_start": float(clip.get("start") or 0.0),
        "source_start": float(clip.get("sourceStart") or 0.0),
        "duration": float(clip.get("duration") or 0.0),
    }


def _phrase_slots(phrases: list[dict], *, max_shot_seconds: float) -> list[dict]:
    if not phrases:
        return []
    slots = []
    cap = max(0.75, min(float(max_shot_seconds), 8.0))
    for index, phrase in enumerate(phrases):
        source_start = float(phrase["start"])
        source_end = (
            float(phrases[index + 1]["start"])
            if index + 1 < len(phrases)
            else float(phrase["end"])
        )
        source_end = max(source_end, float(phrase["end"]))
        duration = max(0.0, source_end - source_start)
        if duration < 0.35:
            continue
        cursor = source_start
        beat = 0
        while cursor < source_end - 1e-6:
            beat_duration = min(cap, source_end - cursor)
            if beat_duration < 0.35 and slots:
                slots[-1]["source_end"] = source_end
                slots[-1]["duration"] = round(
                    float(slots[-1]["duration"]) + beat_duration,
                    6,
                )
                slots[-1]["pause_tail_seconds"] = round(
                    max(
                        0.0,
                        source_end - float(phrase["end"]),
                    ),
                    6,
                )
                break
            slots.append({
                "phrase_index": int(phrase["phrase_index"]),
                "beat_index": beat,
                "source_start": round(cursor, 6),
                "source_end": round(cursor + beat_duration, 6),
                "duration": round(beat_duration, 6),
                "text": phrase["text"],
                "intent_text": phrase["intent_text"],
                "pause_tail_seconds": round(
                    max(
                        0.0,
                        min(cursor + beat_duration, source_end)
                        - max(cursor, float(phrase["end"])),
                    ),
                    6,
                ),
            })
            cursor += beat_duration
            beat += 1
    return slots


def _candidate_for_slot(
    phrase: dict,
    *,
    duration: float,
    previous: dict | None,
    used: set[tuple[int, float, float]],
) -> dict | None:
    ranked = []
    for candidate in phrase.get("candidates") or []:
        if float(candidate["duration"]) + 1e-6 < duration:
            continue
        key = (
            int(candidate["media_id"]),
            float(candidate["source_in"]),
            float(candidate["source_out"]),
        )
        repeat_penalty = -0.08 if key in used else 0.0
        continuity, shared = _continuity_bonus(previous, candidate)
        sequence_score = float(candidate["score"]) + continuity + repeat_penalty
        ranked.append((
            sequence_score,
            candidate,
            continuity,
            shared,
            repeat_penalty,
        ))
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0], reverse=True)
    score, candidate, continuity, shared, repeat = ranked[0]
    return {
        **candidate,
        "sequence_score": round(score, 5),
        "continuity_bonus": round(continuity, 5),
        "continuity_shared_tags": shared,
        "repeat_penalty": round(repeat, 5),
    }


def _reanchor_children(candidate: dict, story: list[dict]) -> None:
    by_id = {
        str(clip.get("id")): clip
        for clip in candidate.get("clips") or []
    }
    story_ids = {str(clip["id"]) for clip in story}
    for child in candidate.get("clips") or []:
        if child.get("track") == "video":
            continue
        old_parent = child.get("parentClipId")
        if not old_parent:
            continue
        if str(old_parent) in story_ids:
            continue
        start = float(child.get("start") or 0.0)
        parent = next(
            (
                clip for clip in story
                if float(clip["start"]) - 1e-6
                <= start
                < float(clip["start"]) + float(clip["duration"]) - 1e-6
            ),
            None,
        )
        if parent is None and story:
            last = story[-1]
            if abs(
                start
                - (float(last["start"]) + float(last["duration"]))
            ) < 1e-6:
                parent = last
        if parent is None:
            raise VoiceVisualError(
                f"L'élément connecté {child.get('id')} tombe hors de la "
                "nouvelle Storyline ; proposition refusée."
            )
        child["parentClipId"] = parent["id"]
        offset = start - float(parent["start"])
        child["anchorOffset"] = round(offset, 6)
        child["connectionPointOffset"] = round(
            min(max(offset, 0.0), float(parent["duration"])),
            6,
        )
        child["connectionMode"] = "follow"


def propose_voice_visual_edit(
    root: Path,
    *,
    edit_name: str,
    voice_media_id: int,
    phrase_indexes: list[int] | None = None,
    explicit_intents: dict[int, str] | None = None,
    visual_media_ids: list[int] | None = None,
    brief: str = "",
    per_phrase: int = 8,
    max_visual_media: int = 24,
    max_shot_seconds: float = 4.5,
    allow_model_download: bool = False,
) -> dict:
    mapping = voice_visual_candidates(
        root,
        voice_media_id=voice_media_id,
        phrase_indexes=phrase_indexes,
        explicit_intents=explicit_intents,
        visual_media_ids=visual_media_ids,
        per_phrase=per_phrase,
        max_visual_media=max_visual_media,
        allow_model_download=allow_model_download,
    )
    phrases = list(mapping["phrases"])
    slots = _phrase_slots(
        phrases,
        max_shot_seconds=max_shot_seconds,
    )
    if not slots:
        raise VoiceVisualError("Aucun segment VO exploitable.")

    phrase_by_index = {
        int(item["phrase_index"]): item
        for item in phrases
    }
    base = load_timeline(root, edit_name)
    if base is None:
        raise VoiceVisualError(
            "Une timeline de travail est requise avant la proposition VO→image."
        )

    voice_mapping = _voice_clip_mapping(
        base,
        voice_media_id=int(voice_media_id),
        first_source_time=float(slots[0]["source_start"]),
    )
    if voice_mapping:
        timeline_origin = (
            float(voice_mapping["timeline_start"])
            + float(slots[0]["source_start"])
            - float(voice_mapping["source_start"])
        )
        mapping_mode = "existing_voice_clip"
    else:
        timeline_origin = float(
            (base.get("storyline") or {}).get("start", 0.0)
        )
        mapping_mode = "relative_to_storyline_start"

    story = []
    cursor = timeline_origin
    previous = None
    used: set[tuple[int, float, float]] = set()
    decisions = []
    for index, slot in enumerate(slots):
        phrase = phrase_by_index[int(slot["phrase_index"])]
        selected = _candidate_for_slot(
            phrase,
            duration=float(slot["duration"]),
            previous=previous,
            used=used,
        )
        if selected is None:
            raise VoiceVisualError(
                "Aucune fenêtre visuelle assez longue pour le segment VO "
                f"{slot['phrase_index']}.{slot['beat_index']} "
                f"({float(slot['duration']):.2f}s)."
            )
        key = (
            int(selected["media_id"]),
            float(selected["source_in"]),
            float(selected["source_out"]),
        )
        used.add(key)
        duration = float(slot["duration"])
        clip = {
            "id": f"vo-visual-{index + 1:03d}",
            "track": "video",
            "mediaDbId": int(selected["media_id"]),
            "start": round(cursor, 6),
            "duration": round(duration, 6),
            "sourceStart": round(float(selected["source_in"]), 6),
            "label": selected["media_title"],
            "agentProposal": True,
            "agentMode": "VOICE_VISUAL",
            "agentReason": (
                f"VO phrase {slot['phrase_index']} · "
                f"score={float(selected['score']):.3f} · "
                f"{selected['reason']}"
            ),
        }
        story.append(clip)
        decisions.append({
            "slot": slot,
            "selected": selected,
            "timeline_start": round(cursor, 6),
            "timeline_end": round(cursor + duration, 6),
        })
        cursor += duration
        previous = selected

    candidate = deepcopy(base)
    preserved = [
        clip for clip in candidate.get("clips") or []
        if str(clip.get("track") or "") != "video"
    ]
    candidate["clips"] = preserved + story
    candidate["storyline"] = {
        "mode": "magnetic",
        "start": round(timeline_origin, 6),
    }
    candidate["duration_seconds"] = max(
        float(candidate.get("duration_seconds") or 0.0),
        cursor,
    )
    _reanchor_children(candidate, story)
    clean = validate_timeline(root, candidate)

    proposal_details = {
        "version": VOICE_VISUAL_VERSION,
        "mode": "VOICE_VISUAL",
        "voice_media_id": int(voice_media_id),
        "voice_transcript_id": mapping.get("transcript_id"),
        "brief": brief,
        "mapping_mode": mapping_mode,
        "voice_clip_mapping": voice_mapping,
        "phrase_count": len(phrases),
        "slot_count": len(slots),
        "visual_media_considered": mapping["visual_media_considered"],
        "semantic_text": mapping["semantic_text"],
        "decisions": decisions,
        "candidate_timeline": clean,
        "policy": {
            "virtual_edl": True,
            "storyline_unchanged": True,
            "voice_audio_preserved": True,
            "human_validation_required": True,
            "lock_check_on_apply": True,
            "checkpoint_before_apply": True,
            "silences_preserved_in_phrase_slots": True,
        },
    }
    record = create_virtual_edit_proposal(
        root,
        edit_name=edit_name,
        brief=brief,
        proposal=proposal_details,
    )
    proposal_details["proposal_id"] = int(record["id"])
    return proposal_details
