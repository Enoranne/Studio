from __future__ import annotations

from copy import deepcopy

from .timebase import seconds_to_ticks, ticks_to_seconds


class StorylineError(ValueError):
    pass


def _clips(doc: dict) -> list[dict]:
    clips = doc.get("clips")
    if not isinstance(clips, list):
        raise StorylineError("clips doit être une liste.")
    return clips


def _ticks(value: object) -> int:
    return seconds_to_ticks(value or 0)


def _seconds(ticks: int) -> float:
    return ticks_to_seconds(ticks)


def _story(clips: list[dict]) -> list[dict]:
    return sorted(
        (c for c in clips if c.get("track") == "video"),
        key=lambda c: (_ticks(c.get("start", 0)), str(c.get("id", ""))),
    )


def attach_clip(
    payload: dict,
    child_id: str,
    parent_id: str,
    *,
    anchor_offset: float | None = None,
) -> dict:
    doc = deepcopy(payload)
    clips = _clips(doc)
    by_id = {str(c.get("id")): c for c in clips}
    child = by_id.get(child_id)
    parent = by_id.get(parent_id)
    if child is None or parent is None:
        raise StorylineError("Clip enfant ou parent introuvable.")
    if child.get("track") == "video":
        raise StorylineError("Un plan STORY ne peut pas être enfant.")
    if parent.get("track") != "video":
        raise StorylineError("Le parent doit appartenir à la STORYLINE.")
    parent_start = _ticks(parent.get("start", 0))
    parent_duration = _ticks(parent.get("duration", 0))
    offset = (
        _ticks(anchor_offset)
        if anchor_offset is not None
        else _ticks(child.get("start", 0)) - parent_start
    )
    child["parentClipId"] = parent_id
    child["anchorOffset"] = _seconds(offset)
    child["connectionPointOffset"] = _seconds(
        min(max(offset, 0), parent_duration)
    )
    child["connectionMode"] = "follow"
    child["start"] = _seconds(parent_start + offset)
    return doc


def detach_clip(payload: dict, child_id: str) -> dict:
    doc = deepcopy(payload)
    clips = _clips(doc)
    child = next((c for c in clips if str(c.get("id")) == child_id), None)
    if child is None:
        raise StorylineError("Clip enfant introuvable.")
    child.pop("parentClipId", None)
    child.pop("anchorOffset", None)
    child.pop("connectionPointOffset", None)
    child.pop("connectionMode", None)
    return doc


def move_connection_point(
    payload: dict,
    child_id: str,
    target_time: float,
) -> dict:
    doc = deepcopy(payload)
    clips = _clips(doc)
    child = next(
        (c for c in clips if str(c.get("id")) == str(child_id)),
        None,
    )
    if child is None:
        raise StorylineError("Clip enfant introuvable.")
    if child.get("track") == "video":
        raise StorylineError(
            "Un plan STORY ne possède pas de point de connexion enfant."
        )

    story = _story(clips)
    if not story:
        raise StorylineError("Aucun plan STORY disponible.")

    target_time = _ticks(target_time)
    story_start = _ticks(story[0].get("start", 0))
    story_end = _ticks(story[-1].get("start", 0)) + _ticks(
        story[-1].get("duration", 0)
    )
    if target_time < story_start or target_time > story_end:
        raise StorylineError(
            "Le point de connexion doit rester sur la STORYLINE."
        )

    parent = next(
        (
            clip
            for clip in story
            if target_time >= _ticks(clip.get("start", 0))
            and target_time
            < _ticks(clip.get("start", 0))
            + _ticks(clip.get("duration", 0))
        ),
        None,
    )
    if parent is None:
        parent = story[-1]

    parent_start = _ticks(parent.get("start", 0))
    parent_duration = _ticks(parent.get("duration", 0))
    point_offset = min(
        max(target_time - parent_start, 0),
        parent_duration,
    )

    child_start = _ticks(child.get("start", 0))
    child["parentClipId"] = str(parent.get("id"))
    child["anchorOffset"] = _seconds(child_start - parent_start)
    child["connectionPointOffset"] = _seconds(point_offset)
    child["connectionMode"] = "follow"
    return doc


def magnetic_reflow(
    payload: dict,
    *,
    story_start: float = 0.0,
    order: list[str] | None = None,
) -> dict:
    doc = deepcopy(payload)
    clips = _clips(doc)
    story = _story(clips)
    by_id = {str(c.get("id")): c for c in clips}
    old_parent_starts = {
        str(c.get("id")): _ticks(c.get("start", 0)) for c in story
    }

    if order is not None:
        current = {str(c.get("id")) for c in story}
        if len(order) != len(current) or set(order) != current:
            raise StorylineError(
                "L'ordre magnétique doit contenir exactement les plans STORY."
            )
        story = [by_id[cid] for cid in order]

    cursor = _ticks(story_start)
    for clip in story:
        clip["start"] = _seconds(cursor)
        cursor += _ticks(clip.get("duration", 0))
    if cursor > _ticks(doc.get("duration_seconds", 0)):
        raise StorylineError("La STORYLINE dépasse la durée du montage.")

    new_parent_starts = {
        str(c.get("id")): _ticks(c.get("start", 0)) for c in story
    }
    for child in clips:
        parent_id = child.get("parentClipId")
        if not parent_id:
            continue
        parent_id = str(parent_id)
        if parent_id not in new_parent_starts:
            raise StorylineError(
                f"Parent de connexion introuvable: {parent_id}"
            )
        if child.get("anchorOffset") is None:
            child["anchorOffset"] = _seconds(
                _ticks(child.get("start", 0))
                - old_parent_starts[parent_id]
            )
        child["connectionMode"] = "follow"
        parent = by_id[parent_id]
        parent_duration = _ticks(parent.get("duration", 0))
        if child.get("connectionPointOffset") is None:
            point_offset = min(
                max(_ticks(child["anchorOffset"]), 0),
                parent_duration,
            )
        else:
            point_offset = min(
                max(_ticks(child["connectionPointOffset"]), 0),
                parent_duration,
            )
        child["connectionPointOffset"] = _seconds(point_offset)
        child["start"] = _seconds(
            new_parent_starts[parent_id]
            + _ticks(child["anchorOffset"])
        )

    doc["storyline"] = {
        "mode": "magnetic",
        "start": _seconds(_ticks(story_start)),
    }
    return doc


def move_story_clip(
    payload: dict,
    clip_id: str,
    target_time: float,
    *,
    story_start: float = 0.0,
) -> dict:
    clips = _clips(payload)
    story = _story(clips)
    target = next((c for c in story if str(c.get("id")) == clip_id), None)
    if target is None:
        raise StorylineError("Plan STORY introuvable.")

    others = [c for c in story if str(c.get("id")) != clip_id]
    target_ticks = _ticks(target_time)
    index = sum(
        1
        for c in others
        if 2 * target_ticks
        >= 2 * _ticks(c.get("start", 0))
        + _ticks(c.get("duration", 0))
    )
    order = [str(c.get("id")) for c in others]
    order.insert(index, clip_id)
    return magnetic_reflow(
        payload,
        story_start=story_start,
        order=order,
    )


def trim_story_clip(
    payload: dict,
    clip_id: str,
    *,
    edge: str,
    delta: float,
    story_start: float = 0.0,
    min_duration: float = 0.2,
) -> dict:
    doc = deepcopy(payload)
    clips = _clips(doc)
    target = next(
        (
            c
            for c in clips
            if str(c.get("id")) == clip_id
            and c.get("track") == "video"
        ),
        None,
    )
    if target is None:
        raise StorylineError("Plan STORY introuvable.")

    duration = _ticks(target.get("duration", 0))
    source_start = _ticks(target.get("sourceStart", 0) or 0)
    delta = _ticks(delta)
    if edge == "left":
        new_duration = duration - delta
        new_source_start = source_start + delta
        if new_source_start < 0:
            raise StorylineError("Le trim IN dépasse le début de la source.")
        target["sourceStart"] = _seconds(new_source_start)
        target["duration"] = _seconds(new_duration)
    elif edge == "right":
        target["duration"] = _seconds(duration + delta)
    else:
        raise StorylineError("edge doit être left ou right.")

    if _ticks(target["duration"]) < _ticks(min_duration):
        raise StorylineError("Durée STORY trop courte.")

    return magnetic_reflow(doc, story_start=story_start)



def insert_story_clip(
    payload: dict,
    clip: dict,
    *,
    target_time: float | None = None,
    story_start: float | None = None,
) -> dict:
    if not isinstance(clip, dict):
        raise StorylineError("clip doit être un objet.")
    if str(clip.get("track") or "") != "video":
        raise StorylineError("Seul un plan VIDEO peut être inséré dans la STORYLINE.")
    clip_id = str(clip.get("id") or "").strip()
    if not clip_id:
        raise StorylineError("Le plan à insérer doit avoir un identifiant.")

    doc = deepcopy(payload)
    clips = _clips(doc)
    if any(str(item.get("id")) == clip_id for item in clips):
        raise StorylineError(f"Identifiant de clip déjà utilisé : {clip_id}")

    current_story = _story(clips)
    clips.append(deepcopy(clip))
    start = (
        float(story_start)
        if story_start is not None
        else float((doc.get("storyline") or {}).get("start", 0) or 0)
    )

    if target_time is None:
        order = [str(item.get("id")) for item in current_story] + [clip_id]
    else:
        target_ticks = _ticks(target_time)
        index = sum(
            1
            for item in current_story
            if 2 * target_ticks
            >= 2 * _ticks(item.get("start", 0))
            + _ticks(item.get("duration", 0))
        )
        order = [str(item.get("id")) for item in current_story]
        order.insert(index, clip_id)

    return magnetic_reflow(doc, story_start=start, order=order)


def remove_story_clip(
    payload: dict,
    clip_id: str,
    *,
    story_start: float | None = None,
) -> dict:
    doc = deepcopy(payload)
    clips = _clips(doc)
    target = next(
        (
            clip
            for clip in clips
            if str(clip.get("id")) == str(clip_id)
            and clip.get("track") == "video"
        ),
        None,
    )
    if target is None:
        raise StorylineError("Plan STORY introuvable.")

    doc["clips"] = [
        clip for clip in clips if str(clip.get("id")) != str(clip_id)
    ]
    for child in doc["clips"]:
        if str(child.get("parentClipId") or "") == str(clip_id):
            child.pop("parentClipId", None)
            child.pop("anchorOffset", None)
            child.pop("connectionPointOffset", None)
            child.pop("connectionMode", None)

    start = (
        float(story_start)
        if story_start is not None
        else float((doc.get("storyline") or {}).get("start", 0) or 0)
    )
    return magnetic_reflow(doc, story_start=start)


def apply_storyline_operation(
    payload: dict,
    operation: str,
    args: dict | None = None,
) -> dict:
    """Applique une mutation magnétique via une seule surface canonique.

    L'UI, l'API et les futurs agents doivent appeler cette surface plutôt que
    réimplémenter reorder/ripple/connexion avec leurs propres règles.
    """

    params = args or {}
    if not isinstance(params, dict):
        raise StorylineError("args doit être un objet.")
    op = str(operation or "").strip().lower().replace("-", "_")
    story_start = float(
        params.get(
            "story_start",
            (payload.get("storyline") or {}).get("start", 0) or 0,
        )
    )

    try:
        if op == "move":
            return move_story_clip(
                payload,
                str(params["clip_id"]),
                float(params["target_time"]),
                story_start=story_start,
            )
        if op == "trim":
            return trim_story_clip(
                payload,
                str(params["clip_id"]),
                edge=str(params["edge"]),
                delta=float(params["delta"]),
                story_start=story_start,
                min_duration=float(params.get("min_duration", 0.2)),
            )
        if op in {"connection_point", "move_connection_point"}:
            return move_connection_point(
                payload,
                str(params["child_id"]),
                float(params["target_time"]),
            )
        if op == "attach":
            anchor = params.get("anchor_offset")
            return attach_clip(
                payload,
                str(params["child_id"]),
                str(params["parent_id"]),
                anchor_offset=float(anchor) if anchor is not None else None,
            )
        if op == "detach":
            return detach_clip(payload, str(params["child_id"]))
        if op == "insert":
            return insert_story_clip(
                payload,
                params["clip"],
                target_time=(
                    float(params["target_time"])
                    if params.get("target_time") is not None
                    else None
                ),
                story_start=story_start,
            )
        if op == "remove":
            return remove_story_clip(
                payload,
                str(params["clip_id"]),
                story_start=story_start,
            )
        if op == "reflow":
            order = params.get("order")
            if order is not None and not isinstance(order, list):
                raise StorylineError("order doit être une liste.")
            return magnetic_reflow(
                payload,
                story_start=story_start,
                order=[str(item) for item in order] if order is not None else None,
            )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, StorylineError):
            raise
        raise StorylineError(
            f"Arguments invalides pour l'opération {op or '<vide>'}."
        ) from exc

    raise StorylineError(f"Opération Storyline inconnue : {op or '<vide>'}.")


def validate_locked_change(
    root,
    before: dict,
    after: dict,
) -> None:
    from .locks import check_operation

    before_by_id = {
        str(c.get("id")): c for c in before.get("clips", [])
    }
    after_by_id = {
        str(c.get("id")): c for c in after.get("clips", [])
    }

    def connection_time(by_id: dict[str, dict], clip: dict) -> float | None:
        parent_id = clip.get("parentClipId")
        if not parent_id:
            return None
        parent = by_id.get(str(parent_id))
        if parent is None:
            return None
        point = clip.get("connectionPointOffset")
        if point is None:
            point = min(
                max(float(clip.get("anchorOffset", 0) or 0), 0.0),
                float(parent.get("duration", 0)),
            )
        return float(parent.get("start", 0)) + float(point)

    for new in after.get("clips", []):
        cid = str(new.get("id"))
        old = before_by_id.get(cid)
        if old is None:
            continue

        changed_start = abs(
            float(old.get("start", 0)) - float(new.get("start", 0))
        ) > 1e-6
        changed_duration = abs(
            float(old.get("duration", 0)) - float(new.get("duration", 0))
        ) > 1e-6
        changed_source = abs(
            float(old.get("sourceStart", 0) or 0)
            - float(new.get("sourceStart", 0) or 0)
        ) > 1e-6
        old_point = connection_time(before_by_id, old)
        new_point = connection_time(after_by_id, new)
        changed_connection = (
            str(old.get("parentClipId") or "")
            != str(new.get("parentClipId") or "")
            or (
                old_point is None
                and new_point is not None
            )
            or (
                old_point is not None
                and new_point is None
            )
            or (
                old_point is not None
                and new_point is not None
                and abs(old_point - new_point) > 1e-6
            )
        )

        track = str(new.get("track") or old.get("track") or "")
        if changed_connection:
            points = [
                point for point in (old_point, new_point)
                if point is not None
            ]
            if points:
                point_start = max(0.0, min(points) - 0.001)
                point_end = max(points) + 0.001
                operations = ["connection_point"]
                operations.append(
                    "graphics" if track == "titles" else "audio_change"
                )
                for operation in operations:
                    decision = check_operation(
                        root,
                        operation=operation,
                        start=point_start,
                        end=point_end,
                        target="timeline",
                    )
                    if not decision.allowed:
                        raise StorylineError(
                            f"{cid}: {decision.reason}"
                        )

        if not (
            changed_start
            or changed_duration
            or changed_source
        ):
            continue

        if track == "video":
            operation = (
                "trim"
                if changed_duration or changed_source
                else "reorder"
            )
        elif track == "titles":
            operation = "graphics"
        else:
            operation = "audio_change"

        old_start = float(old.get("start", 0))
        old_end = old_start + float(old.get("duration", 0))
        new_start = float(new.get("start", 0))
        new_end = new_start + float(new.get("duration", 0))
        start = min(old_start, new_start)
        end = max(old_end, new_end)
        if end <= start:
            continue

        decision = check_operation(
            root,
            operation=operation,
            start=start,
            end=end,
            target="timeline",
        )
        if not decision.allowed:
            raise StorylineError(
                f"{cid}: {decision.reason}"
            )
