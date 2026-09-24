from __future__ import annotations

from pathlib import Path

from .canon_conflicts import assess_semantic_tag_against_canon, normalize_semantic_tag
from .metadata import fetch_media_with_metadata
from .timeline import load_timeline


FACETS = ("character", "prop", "decor", "look")


class TimelineContinuityError(ValueError):
    pass


def _structured_tags(item: dict | None) -> dict[str, set[str]]:
    out = {facet: set() for facet in FACETS}
    if not item:
        return out
    for raw in item.get("tags") or []:
        try:
            facet, _value, tag = normalize_semantic_tag(str(raw))
        except Exception:
            continue
        out[facet].add(tag)
    return out


def _media_map(root: Path) -> dict[int, dict]:
    return {
        int(item["id"]): item
        for item in fetch_media_with_metadata(root)
    }


def _story_clips(timeline: dict) -> list[dict]:
    return sorted(
        (
            clip for clip in timeline.get("clips", [])
            if str(clip.get("track") or "") == "video"
        ),
        key=lambda clip: (
            float(clip.get("start") or 0.0),
            str(clip.get("id") or ""),
        ),
    )


def _clip_payload(clip: dict | None, media: dict | None) -> dict | None:
    if clip is None:
        return None
    return {
        "clip_id": str(clip.get("id") or ""),
        "media_id": (
            int(clip["mediaDbId"])
            if clip.get("mediaDbId") is not None
            else None
        ),
        "label": (
            (media or {}).get("title")
            or clip.get("label")
            or (media or {}).get("relative_path")
            or str(clip.get("id") or "")
        ),
        "start": float(clip.get("start") or 0.0),
        "duration": float(clip.get("duration") or 0.0),
        "source_start": float(clip.get("sourceStart") or 0.0),
        "tags": sorted(
            tag
            for values in _structured_tags(media).values()
            for tag in values
        ),
    }


def _compare_side(
    *,
    side: str,
    neighbor: dict | None,
    target: dict,
    neighbor_media: dict | None,
    target_media: dict,
) -> list[dict]:
    if neighbor is None:
        return []
    findings: list[dict] = []
    neighbor_tags = _structured_tags(neighbor_media)
    target_tags = _structured_tags(target_media)

    for facet in FACETS:
        left = neighbor_tags[facet]
        right = target_tags[facet]
        shared = sorted(left & right)
        if left and right and not shared:
            findings.append({
                "kind": "FACET_RUPTURE",
                "severity": "WARNING",
                "side": side,
                "facet": facet,
                "message": (
                    f"{side} : le facet {facet} change sans tag commun "
                    f"({', '.join(sorted(left))} → {', '.join(sorted(right))})."
                ),
                "neighbor_tags": sorted(left),
                "target_tags": sorted(right),
            })
        elif shared:
            findings.append({
                "kind": "FACET_CONTINUITY",
                "severity": "INFO",
                "side": side,
                "facet": facet,
                "message": (
                    f"{side} : continuité {facet} via "
                    f"{', '.join(shared)}."
                ),
                "shared_tags": shared,
            })
        elif left and not right:
            findings.append({
                "kind": "TARGET_EVIDENCE_MISSING",
                "severity": "REVIEW",
                "side": side,
                "facet": facet,
                "message": (
                    f"{side} : le voisin porte {', '.join(sorted(left))}, "
                    "mais le plan évalué n'a pas de tag structuré pour ce facet."
                ),
                "neighbor_tags": sorted(left),
            })
        elif right and not left:
            findings.append({
                "kind": "NEIGHBOR_EVIDENCE_MISSING",
                "severity": "INFO",
                "side": side,
                "facet": facet,
                "message": (
                    f"{side} : le plan évalué porte {', '.join(sorted(right))}, "
                    "mais le voisin n'a pas de tag structuré pour ce facet."
                ),
                "target_tags": sorted(right),
            })
    return findings


def analyze_timeline_continuity(
    root: Path,
    *,
    edit_name: str = "teaser_30",
    clip_id: str,
    candidate_media_id: int | None = None,
) -> dict:
    timeline = load_timeline(root, edit_name)
    if timeline is None:
        raise TimelineContinuityError(
            f"Timeline introuvable pour l'edit {edit_name}."
        )
    story = _story_clips(timeline)
    index = next(
        (i for i, clip in enumerate(story) if str(clip.get("id")) == str(clip_id)),
        None,
    )
    if index is None:
        raise TimelineContinuityError(
            f"Plan STORY introuvable : {clip_id}"
        )

    media_by_id = _media_map(root)
    target_clip = story[index]
    original_media_id = target_clip.get("mediaDbId")
    if original_media_id is None:
        raise TimelineContinuityError(
            "Le plan STORY sélectionné n'est pas relié à un média catalogue."
        )
    target_media_id = (
        int(candidate_media_id)
        if candidate_media_id is not None
        else int(original_media_id)
    )
    if target_media_id not in media_by_id:
        raise TimelineContinuityError(
            f"Média candidat introuvable : id={target_media_id}"
        )
    target_media = media_by_id[target_media_id]
    if str(target_media.get("kind") or "") not in {"video", "image"}:
        raise TimelineContinuityError(
            "Le candidat de continuité doit être un média visuel."
        )

    previous_clip = story[index - 1] if index > 0 else None
    next_clip = story[index + 1] if index + 1 < len(story) else None
    previous_media = (
        media_by_id.get(int(previous_clip["mediaDbId"]))
        if previous_clip and previous_clip.get("mediaDbId") is not None
        else None
    )
    next_media = (
        media_by_id.get(int(next_clip["mediaDbId"]))
        if next_clip and next_clip.get("mediaDbId") is not None
        else None
    )

    findings = []
    findings.extend(
        _compare_side(
            side="PRÉCÉDENT",
            neighbor=previous_clip,
            target=target_clip,
            neighbor_media=previous_media,
            target_media=target_media,
        )
    )
    findings.extend(
        _compare_side(
            side="SUIVANT",
            neighbor=next_clip,
            target=target_clip,
            neighbor_media=next_media,
            target_media=target_media,
        )
    )

    previous_tags = _structured_tags(previous_media)
    next_tags = _structured_tags(next_media)
    target_tags = _structured_tags(target_media)
    for facet in FACETS:
        bridge = previous_tags[facet] & next_tags[facet]
        if not bridge:
            continue
        missing = bridge - target_tags[facet]
        if missing:
            findings.append({
                "kind": "BRIDGE_EVIDENCE_GAP",
                "severity": "REVIEW",
                "side": "PRÉCÉDENT↔SUIVANT",
                "facet": facet,
                "message": (
                    f"Les deux voisins partagent {', '.join(sorted(bridge))} "
                    f"pour {facet}, mais le plan évalué ne porte pas cette preuve."
                ),
                "neighbor_shared_tags": sorted(bridge),
                "target_tags": sorted(target_tags[facet]),
            })
        else:
            findings.append({
                "kind": "BRIDGE_CONTINUITY",
                "severity": "INFO",
                "side": "PRÉCÉDENT↔SUIVANT",
                "facet": facet,
                "message": (
                    f"Le plan préserve le pont {facet} "
                    f"{', '.join(sorted(bridge))} entre ses deux voisins."
                ),
                "shared_tags": sorted(bridge),
            })

    canon_assessments = [
        assess_semantic_tag_against_canon(
            root,
            media_id=target_media_id,
            tag=tag,
            edit_name=edit_name,
            context_clip_id=str(clip_id),
        )
        for tag in sorted(
            tag
            for values in target_tags.values()
            for tag in values
        )
    ]

    warnings = [
        finding for finding in findings
        if finding.get("severity") == "WARNING"
    ]
    reviews = [
        finding for finding in findings
        if finding.get("severity") == "REVIEW"
    ]
    continuity = [
        finding for finding in findings
        if finding.get("kind") in {
            "FACET_CONTINUITY",
            "BRIDGE_CONTINUITY",
        }
    ]
    structured_count = sum(len(values) for values in target_tags.values())
    if warnings:
        status = "RUPTURE"
    elif reviews:
        status = "REVIEW"
    elif continuity:
        status = "CONTINUOUS"
    elif structured_count == 0:
        status = "INSUFFICIENT"
    else:
        status = "NO_SIGNAL"

    return {
        "version": "0.22-context-1",
        "edit_name": str(edit_name),
        "clip_id": str(clip_id),
        "mode": "CANDIDATE" if candidate_media_id is not None else "MOUNTED",
        "original_media_id": int(original_media_id),
        "candidate_media_id": (
            int(candidate_media_id)
            if candidate_media_id is not None
            else None
        ),
        "status": status,
        "previous": _clip_payload(previous_clip, previous_media),
        "target": {
            **(_clip_payload(target_clip, target_media) or {}),
            "media_id": target_media_id,
            "original_media_id": int(original_media_id),
            "candidate": candidate_media_id is not None,
        },
        "next": _clip_payload(next_clip, next_media),
        "findings": findings,
        "canon_assessments": canon_assessments,
        "summary": {
            "warning_count": len(warnings),
            "review_count": len(reviews),
            "continuity_count": len(continuity),
            "structured_target_tag_count": structured_count,
            "neighbor_count": int(previous_clip is not None) + int(next_clip is not None),
        },
        "policy": {
            "analysis_only": True,
            "automatic_edit": False,
            "automatic_candidate_rejection": False,
            "absence_of_tag_is_not_visual_proof_of_absence": True,
            "timeline_context_used": True,
        },
    }
