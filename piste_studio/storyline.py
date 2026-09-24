from __future__ import annotations

from copy import deepcopy


class StorylineError(ValueError):
    pass


def _clips(doc: dict) -> list[dict]:
    clips = doc.get("clips")
    if not isinstance(clips, list):
        raise StorylineError("clips doit être une liste.")
    return clips


def _story(clips: list[dict]) -> list[dict]:
    return sorted(
        (c for c in clips if c.get("track") == "video"),
        key=lambda c: (float(c.get("start", 0)), str(c.get("id", ""))),
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
    offset = (
        float(anchor_offset)
        if anchor_offset is not None
        else float(child.get("start", 0)) - float(parent.get("start", 0))
    )
    child["parentClipId"] = parent_id
    child["anchorOffset"] = round(offset, 6)
    child["connectionPointOffset"] = round(
        min(
            max(offset, 0.0),
            float(parent.get("duration", 0)),
        ),
        6,
    )
    child["connectionMode"] = "follow"
    child["start"] = round(float(parent.get("start", 0)) + offset, 6)
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

    target_time = float(target_time)
    story_start = float(story[0].get("start", 0))
    story_end = float(story[-1].get("start", 0)) + float(
        story[-1].get("duration", 0)
    )
    if target_time < story_start - 1e-6 or target_time > story_end + 1e-6:
        raise StorylineError(
            "Le point de connexion doit rester sur la STORYLINE."
        )

    parent = next(
        (
            clip
            for clip in story
            if target_time >= float(clip.get("start", 0)) - 1e-6
            and target_time
            < float(clip.get("start", 0))
            + float(clip.get("duration", 0))
            - 1e-6
        ),
        None,
    )
    if parent is None:
        parent = story[-1]

    parent_start = float(parent.get("start", 0))
    parent_duration = float(parent.get("duration", 0))
    point_offset = min(
        max(target_time - parent_start, 0.0),
        parent_duration,
    )

    child_start = float(child.get("start", 0))
    child["parentClipId"] = str(parent.get("id"))
    child["anchorOffset"] = round(child_start - parent_start, 6)
    child["connectionPointOffset"] = round(point_offset, 6)
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
        str(c.get("id")): float(c.get("start", 0)) for c in story
    }

    if order is not None:
        current = {str(c.get("id")) for c in story}
        if len(order) != len(current) or set(order) != current:
            raise StorylineError(
                "L'ordre magnétique doit contenir exactement les plans STORY."
            )
        story = [by_id[cid] for cid in order]

    cursor = float(story_start)
    for clip in story:
        clip["start"] = round(cursor, 6)
        cursor += float(clip.get("duration", 0))
    if cursor > float(doc.get("duration_seconds", 0)) + 1e-6:
        raise StorylineError("La STORYLINE dépasse la durée du montage.")

    new_parent_starts = {
        str(c.get("id")): float(c.get("start", 0)) for c in story
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
            child["anchorOffset"] = round(
                float(child.get("start", 0))
                - old_parent_starts[parent_id],
                6,
            )
        child["connectionMode"] = "follow"
        parent = by_id[parent_id]
        if child.get("connectionPointOffset") is None:
            child["connectionPointOffset"] = round(
                min(
                    max(float(child["anchorOffset"]), 0.0),
                    float(parent.get("duration", 0)),
                ),
                6,
            )
        else:
            child["connectionPointOffset"] = round(
                min(
                    max(float(child["connectionPointOffset"]), 0.0),
                    float(parent.get("duration", 0)),
                ),
                6,
            )
        child["start"] = round(
            new_parent_starts[parent_id]
            + float(child["anchorOffset"]),
            6,
        )

    doc["storyline"] = {
        "mode": "magnetic",
        "start": round(float(story_start), 6),
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
    index = sum(
        1
        for c in others
        if float(target_time)
        >= float(c.get("start", 0))
        + float(c.get("duration", 0)) / 2
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

    duration = float(target.get("duration", 0))
    source_start = float(target.get("sourceStart", 0) or 0)
    delta = float(delta)
    if edge == "left":
        new_duration = duration - delta
        new_source_start = source_start + delta
        if new_source_start < 0:
            raise StorylineError("Le trim IN dépasse le début de la source.")
        target["sourceStart"] = round(new_source_start, 6)
        target["duration"] = round(new_duration, 6)
    elif edge == "right":
        target["duration"] = round(duration + delta, 6)
    else:
        raise StorylineError("edge doit être left ou right.")

    if float(target["duration"]) < min_duration:
        raise StorylineError("Durée STORY trop courte.")

    return magnetic_reflow(doc, story_start=story_start)


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
