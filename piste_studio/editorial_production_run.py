from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from .audio_tracks import list_audio_tracks, selected_audio_track
from .editorial_agent import list_proposals, transcript_candidates
from .master_critic import list_master_critic_reports
from .metadata import fetch_media_with_metadata
from .readiness import build_production_readiness
from .timeline import load_timeline
from .transcript_engine import get_transcript


EDITORIAL_PRODUCTION_RUN_VERSION = "0.26-piste0-recipe-1"


def _stage(stage_id: str, status: str, message: str, **details) -> dict:
    out = {
        "id": stage_id,
        "status": status,
        "message": message,
    }
    out.update(details)
    return out


def _timeline_media_ids(timeline: dict | None) -> list[int]:
    if not timeline:
        return []
    ids: list[int] = []
    for clip in timeline.get("clips") or []:
        if str(clip.get("track") or "").lower() != "video":
            continue
        value = clip.get("mediaDbId")
        if value is None:
            continue
        try:
            media_id = int(value)
        except (TypeError, ValueError):
            continue
        if media_id not in ids:
            ids.append(media_id)
    return ids


def _select_media(
    root: Path,
    timeline: dict | None,
    media_ids: list[int] | None,
) -> tuple[list[dict], list[int]]:
    catalog = [dict(x) for x in fetch_media_with_metadata(root)]
    by_id = {int(x["id"]): x for x in catalog}
    requested: list[int] = []
    if media_ids:
        for value in media_ids:
            media_id = int(value)
            if media_id not in requested:
                requested.append(media_id)
    else:
        requested = _timeline_media_ids(timeline)
        if not requested:
            requested = [
                int(x["id"])
                for x in catalog
                if str(x.get("kind") or "").lower() == "video"
            ]

    rows: list[dict] = []
    missing_ids: list[int] = []
    for media_id in requested:
        row = by_id.get(media_id)
        if row is None:
            missing_ids.append(media_id)
            continue
        rows.append(row)
    return rows, missing_ids


def build_editorial_production_run_report(
    root: Path,
    *,
    edit_name: str = "teaser_30",
    media_ids: list[int] | None = None,
    version: str | None = None,
) -> dict:
    """Build a non-destructive V0.26 production recipe report.

    This function never analyzes tracks, sends media to a network provider,
    creates a proposal, applies a proposal, publishes a timeline, executes
    Tesseract, or edits the Storyline. It only reports persisted state and the
    next explicit action.
    """
    root = root.expanduser().resolve()
    timeline = load_timeline(root, edit_name)
    selected, unknown_ids = _select_media(root, timeline, media_ids)

    media_reports: list[dict] = []
    existing_count = 0
    tracks_ready_count = 0
    track_selected_count = 0
    transcript_count = 0
    ai_view_ready_count = 0
    candidate_totals = {
        "silence": 0,
        "filler": 0,
        "retake": 0,
    }

    for item in selected:
        media_id = int(item["id"])
        relative_path = str(item.get("relative_path") or "")
        path = (root / relative_path).resolve()
        exists = path.is_file()
        if exists:
            existing_count += 1

        tracks = list_audio_tracks(root, media_id)
        if tracks:
            tracks_ready_count += 1
        selected_track = selected_audio_track(root, media_id)
        if selected_track:
            track_selected_count += 1

        transcript = get_transcript(root, media_id)
        candidates = None
        if transcript:
            transcript_count += 1
            try:
                candidates = transcript_candidates(root, media_id)
            except Exception as exc:
                candidates = {"error": str(exc)}
        if candidates and not candidates.get("error"):
            candidate_totals["silence"] += len(
                candidates.get("silence_candidates") or []
            )
            candidate_totals["filler"] += len(
                candidates.get("filler_candidates") or []
            )
            candidate_totals["retake"] += len(
                candidates.get("retake_candidates") or []
            )

        ai_ready = bool(tracks and transcript)
        if ai_ready:
            ai_view_ready_count += 1

        media_reports.append({
            "media_id": media_id,
            "kind": item.get("kind"),
            "relative_path": relative_path,
            "exists": exists,
            "audio_tracks": len(tracks),
            "selected_track_index": (
                int(selected_track["track_index"])
                if selected_track
                else None
            ),
            "transcript_id": (
                int(transcript["id"])
                if transcript and transcript.get("id") is not None
                else None
            ),
            "transcript_phrase_count": len(
                (transcript or {}).get("phrases") or []
            ),
            "candidate_counts": {
                "silence": len(
                    (candidates or {}).get("silence_candidates") or []
                ),
                "filler": len(
                    (candidates or {}).get("filler_candidates") or []
                ),
                "retake": len(
                    (candidates or {}).get("retake_candidates") or []
                ),
            },
            "ai_timeline_view_ready": ai_ready,
        })

    proposals = list_proposals(root, edit_name=edit_name)
    strategies = [
        x for x in proposals
        if str(x.get("proposal_kind") or "").upper() == "STRATEGY"
    ]
    proposed_edits = [
        x for x in proposals
        if str(x.get("proposal_kind") or "").upper() == "PROPOSED_EDIT"
    ]
    latest_proposal = proposed_edits[0] if proposed_edits else None
    pending_proposal = next(
        (
            x for x in proposed_edits
            if str(x.get("status") or "").upper() == "PENDING"
        ),
        None,
    )
    applied_proposal = next(
        (
            x for x in proposed_edits
            if str(x.get("status") or "").upper() == "APPLIED"
        ),
        None,
    )

    readiness = build_production_readiness(
        root,
        edit_name=edit_name,
        version=version,
    )
    critics = list_master_critic_reports(root, edit_name=edit_name)
    latest_critic = critics[0] if critics else None

    selected_count = len(selected)
    stages: list[dict] = []

    media_ok = (
        selected_count > 0
        and not unknown_ids
        and existing_count == selected_count
    )
    stages.append(_stage(
        "rushes",
        "PASS" if media_ok else "MISSING",
        (
            f"{selected_count} rush(es) réel(s) sélectionné(s) et présent(s)."
            if media_ok
            else "Sélectionner des rushes réels présents dans le projet."
        ),
        selected_media_ids=[int(x["id"]) for x in selected],
        unknown_media_ids=unknown_ids,
        existing_count=existing_count,
    ))

    audio_ok = selected_count > 0 and tracks_ready_count == selected_count
    stages.append(_stage(
        "audio_tracks",
        "PASS" if audio_ok else "MISSING",
        (
            f"Pistes audio analysées sur {tracks_ready_count}/{selected_count} rush(es)."
        ),
        analyzed_media_count=tracks_ready_count,
        target_media_count=selected_count,
    ))

    selection_ok = (
        selected_count > 0
        and track_selected_count == selected_count
    )
    stages.append(_stage(
        "audio_track_selection",
        "PASS" if selection_ok else "MISSING",
        (
            f"Piste de transcription sélectionnée sur "
            f"{track_selected_count}/{selected_count} rush(es)."
        ),
        selected_count=track_selected_count,
        target_media_count=selected_count,
    ))

    transcript_ok = transcript_count > 0
    stages.append(_stage(
        "transcripts",
        "PASS" if transcript_ok else "MISSING",
        (
            f"{transcript_count} rush(es) disposent d'un transcript exploitable."
            if transcript_ok
            else "Aucun transcript exploitable sur la sélection."
        ),
        transcript_media_count=transcript_count,
        selected_media_count=selected_count,
    ))

    stages.append(_stage(
        "candidates",
        "PASS" if transcript_ok else "MISSING",
        (
            "Candidats transcript disponibles."
            if transcript_ok
            else "Les candidats nécessitent au moins un transcript."
        ),
        counts=candidate_totals,
    ))

    ai_ok = ai_view_ready_count > 0
    stages.append(_stage(
        "ai_timeline_view",
        "PASS" if ai_ok else "MISSING",
        (
            f"AI Timeline View prête sur {ai_view_ready_count} rush(es)."
            if ai_ok
            else "Aucun rush ne combine encore pistes audio + transcript."
        ),
        ready_media_count=ai_view_ready_count,
    ))

    stages.append(_stage(
        "editorial_strategy",
        "PASS" if strategies else "MISSING",
        (
            f"{len(strategies)} stratégie(s) éditoriale(s) enregistrée(s)."
            if strategies
            else "Aucune stratégie éditoriale V0.26 enregistrée."
        ),
        latest_strategy_id=(int(strategies[0]["id"]) if strategies else None),
    ))

    if applied_proposal:
        proposal_status = "PASS"
        proposal_message = (
            f"Proposition {int(applied_proposal['id'])} validée et appliquée."
        )
    elif pending_proposal:
        proposal_status = "WAITING_HUMAN_VALIDATION"
        proposal_message = (
            f"Proposition {int(pending_proposal['id'])} prête : "
            "validation humaine requise avant Storyline."
        )
    elif latest_proposal:
        proposal_status = "MISSING"
        proposal_message = (
            f"Dernière proposition {int(latest_proposal['id'])} au statut "
            f"{latest_proposal.get('status')} ; recalculer si nécessaire."
        )
    else:
        proposal_status = "MISSING"
        proposal_message = "Aucune EDL virtuelle proposée."

    stages.append(_stage(
        "proposed_edit",
        proposal_status,
        proposal_message,
        proposal_id=(
            int((applied_proposal or pending_proposal or latest_proposal)["id"])
            if (applied_proposal or pending_proposal or latest_proposal)
            else None
        ),
    ))

    timeline_clips = len((timeline or {}).get("clips") or [])
    storyline_ok = bool(applied_proposal and timeline and timeline_clips)
    stages.append(_stage(
        "storyline",
        "PASS" if storyline_ok else "MISSING",
        (
            f"Storyline transactionnelle active avec {timeline_clips} clip(s)."
            if storyline_ok
            else "La Storyline n'a pas encore reçu de proposition validée."
        ),
        clip_count=timeline_clips,
        applied_proposal_id=(
            int(applied_proposal["id"]) if applied_proposal else None
        ),
    ))

    capabilities = readiness.get("capabilities") or {}
    tess_ok = bool(capabilities.get("can_deliver"))
    stages.append(_stage(
        "tesseract_render",
        "PASS" if tess_ok else "MISSING",
        (
            "Rendu Tesseract détecté et prêt pour contrôle."
            if tess_ok
            else str(
                readiness.get("next_action")
                or "Poursuivre publication/bootstrap/authoring/rendu Tesseract."
            )
        ),
        pipeline_status=readiness.get("pipeline_status"),
        capabilities=capabilities,
        selection=readiness.get("selection"),
    ))

    critic_ok = latest_critic is not None
    critic_report = (
        (latest_critic.get("report") or {})
        if latest_critic
        else {}
    )
    stages.append(_stage(
        "master_critic",
        "PASS" if critic_ok else "MISSING",
        (
            f"Master Critic disponible : "
            f"{critic_report.get('status') or latest_critic.get('status') or 'UNKNOWN'}."
            if critic_ok
            else "Aucun Master Critic n'a encore analysé le rendu."
        ),
        report_id=(int(latest_critic["id"]) if latest_critic else None),
        critic_status=(
            critic_report.get("status")
            or (latest_critic or {}).get("status")
        ),
    ))

    if not media_ok:
        status = "BLOCKED"
        next_action = (
            "Scanner le vrai projet PISTE 0 puis sélectionner les rushes "
            "réels du passage de recette."
        )
    elif not audio_ok:
        status = "IN_PROGRESS"
        next_action = (
            "Analyser les pistes audio des rushes sélectionnés dans "
            "EDITORIAL AGENT → AUDIO TRACK INTELLIGENCE."
        )
    elif not selection_ok:
        status = "IN_PROGRESS"
        next_action = (
            "Choisir explicitement la piste de transcription non silencieuse "
            "pour chaque rush sélectionné."
        )
    elif not transcript_ok:
        status = "IN_PROGRESS"
        next_action = (
            "Transcrire au moins un rush parlant/VO intégré, ou importer un "
            "transcript. Aucun envoi réseau sans consentement explicite."
        )
    elif not ai_ok:
        status = "IN_PROGRESS"
        next_action = "Ouvrir l'AI Timeline View sur un rush transcrit."
    elif not strategies:
        status = "IN_PROGRESS"
        next_action = (
            "Créer la stratégie éditoriale du passage PISTE 0 "
            "(objectif 30–60 s)."
        )
    elif pending_proposal:
        status = "AWAITING_HUMAN_VALIDATION"
        next_action = (
            f"Examiner l'EDL virtuelle {int(pending_proposal['id'])} puis "
            "l'accepter ou la rejeter explicitement."
        )
    elif not applied_proposal:
        status = "IN_PROGRESS"
        next_action = "Créer une nouvelle Proposed Edit à partir de la stratégie."
    elif not tess_ok:
        status = "IN_PROGRESS"
        next_action = str(
            readiness.get("next_action")
            or "Publier la Storyline puis exécuter la chaîne Tesseract."
        )
    elif not critic_ok:
        status = "IN_PROGRESS"
        next_action = (
            "Lancer Rendered Master Critic sur le master produit par Tesseract."
        )
    else:
        status = "AWAITING_FINAL_REVIEW"
        next_action = (
            "Visionner le master, lire le Master Critic et exécuter ensuite "
            "la recette V0.24.1 delivery. Aucun PASS final automatique."
        )

    return {
        "version": EDITORIAL_PRODUCTION_RUN_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "edit_name": edit_name,
        "requested_version": version,
        "status": status,
        "human_validation_required": True,
        "media": media_reports,
        "stages": stages,
        "proposal_summary": {
            "strategy_count": len(strategies),
            "proposed_edit_count": len(proposed_edits),
            "pending_proposal_id": (
                int(pending_proposal["id"]) if pending_proposal else None
            ),
            "applied_proposal_id": (
                int(applied_proposal["id"]) if applied_proposal else None
            ),
        },
        "readiness": readiness,
        "latest_master_critic": (
            {
                "id": int(latest_critic["id"]),
                "status": (
                    critic_report.get("status")
                    or latest_critic.get("status")
                ),
                "source_path": latest_critic.get("source_path"),
            }
            if latest_critic
            else None
        ),
        "next_action": next_action,
        "policy": {
            "report_only": True,
            "no_network_call": True,
            "no_automatic_transcription": True,
            "no_automatic_proposal": True,
            "no_automatic_apply": True,
            "no_storyline_mutation": True,
            "never_auto_pass_human_review": True,
            "source_media_immutable": True,
            "master_immutable": True,
        },
    }


def save_editorial_production_run_report(
    root: Path,
    *,
    edit_name: str = "teaser_30",
    media_ids: list[int] | None = None,
    version: str | None = None,
) -> Path:
    root = root.expanduser().resolve()
    report = build_editorial_production_run_report(
        root,
        edit_name=edit_name,
        media_ids=media_ids,
        version=version,
    )
    folder = root / "reports" / "production"
    folder.mkdir(parents=True, exist_ok=True)
    version_label = (
        ((report.get("readiness") or {}).get("selection") or {}).get("version")
        or version
        or "WORKING"
    )
    path = folder / (
        f"{edit_name}_{version_label}_editorial-v026-production-run.json"
    )
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
