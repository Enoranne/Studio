from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math
import os
import shutil
import subprocess
from typing import Protocol

from .db import connect
from .metadata import fetch_media_with_metadata, set_media_metadata
from .media_intelligence import get_media_analysis, probe_media

VISION_PROVIDER = "local_clip"
DEFAULT_MODEL_ID = os.environ.get(
    "PISTE_VISION_MODEL",
    "openai/clip-vit-base-patch32",
)

FACET_THRESHOLDS = {
    "character": 0.88,
    "prop": 0.86,
    "decor": 0.84,
    "look": 0.82,
}


class SemanticVisionError(ValueError):
    pass


@dataclass(frozen=True)
class VisionStatus:
    provider: str
    model_id: str
    dependencies_ready: bool
    model_cached: bool | None
    ffmpeg_ready: bool
    message: str

    @property
    def ready(self) -> bool:
        return (
            self.dependencies_ready
            and self.ffmpeg_ready
            and self.model_cached is not False
        )


class VisionProvider(Protocol):
    provider: str
    model_id: str

    def embed_images(
        self,
        image_paths: list[Path],
        *,
        allow_model_download: bool = False,
    ) -> list[float]:
        ...


def _dependency_status() -> tuple[bool, str]:
    missing = []
    for module in ("torch", "transformers", "PIL"):
        try:
            __import__(module)
        except Exception:
            missing.append(module)
    if missing:
        return False, "Dépendances vision manquantes : " + ", ".join(missing)
    return True, "Dépendances vision disponibles."


def detect_semantic_vision(
    *,
    model_id: str = DEFAULT_MODEL_ID,
) -> VisionStatus:
    deps, message = _dependency_status()
    ffmpeg = bool(shutil.which("ffmpeg"))
    if not deps:
        return VisionStatus(
            provider=VISION_PROVIDER,
            model_id=model_id,
            dependencies_ready=False,
            model_cached=None,
            ffmpeg_ready=ffmpeg,
            message=message,
        )

    cached: bool | None = None
    try:
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=model_id,
            local_files_only=True,
        )
        cached = True
    except Exception:
        cached = False

    if not ffmpeg:
        message = "ffmpeg est requis pour extraire les images de référence."
    elif cached is False:
        message = (
            "Le modèle local n’est pas encore présent dans le cache. "
            "Une installation/téléchargement explicite est nécessaire."
        )
    else:
        message = "Vision locale prête."
    return VisionStatus(
        provider=VISION_PROVIDER,
        model_id=model_id,
        dependencies_ready=True,
        model_cached=cached,
        ffmpeg_ready=ffmpeg,
        message=message,
    )


class LocalClipProvider:
    provider = VISION_PROVIDER

    def __init__(self, model_id: str = DEFAULT_MODEL_ID):
        self.model_id = model_id

    def embed_images(
        self,
        image_paths: list[Path],
        *,
        allow_model_download: bool = False,
    ) -> list[float]:
        if not image_paths:
            raise SemanticVisionError("Aucune image à analyser.")
        try:
            import torch
            from PIL import Image
            from transformers import AutoProcessor, CLIPModel
        except Exception as exc:
            raise SemanticVisionError(
                "Installe l’extra vision pour utiliser le modèle local."
            ) from exc

        try:
            processor = AutoProcessor.from_pretrained(
                self.model_id,
                local_files_only=not allow_model_download,
            )
            model = CLIPModel.from_pretrained(
                self.model_id,
                local_files_only=not allow_model_download,
            )
        except Exception as exc:
            if allow_model_download:
                raise SemanticVisionError(
                    f"Impossible de charger le modèle {self.model_id}."
                ) from exc
            raise SemanticVisionError(
                "Modèle vision absent du cache local. "
                "Autorise explicitement son téléchargement ou installe-le localement."
            ) from exc

        images = []
        try:
            for path in image_paths:
                with Image.open(path) as im:
                    images.append(im.convert("RGB").copy())
            inputs = processor(images=images, return_tensors="pt")
            with torch.no_grad():
                features = model.get_image_features(**inputs)
                features = features / features.norm(dim=-1, keepdim=True)
                mean = features.mean(dim=0)
                mean = mean / mean.norm()
            return [float(x) for x in mean.detach().cpu().tolist()]
        finally:
            for image in images:
                try:
                    image.close()
                except Exception:
                    pass


def _media_row(root: Path, media_id: int) -> dict:
    rows = {int(x["id"]): x for x in fetch_media_with_metadata(root)}
    row = rows.get(int(media_id))
    if row is None:
        raise SemanticVisionError(f"Média introuvable : id={media_id}")
    if row.get("kind") != "video":
        raise SemanticVisionError("La vision sémantique cible les vidéos.")
    return row


def _media_path(root: Path, item: dict) -> Path:
    root = root.resolve()
    path = (root / item["relative_path"]).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SemanticVisionError("Chemin média hors projet.") from exc
    if not path.exists() or not path.is_file():
        raise SemanticVisionError(
            f"Fichier média absent : {item['relative_path']}"
        )
    return path


def _duration(root: Path, item: dict, path: Path) -> float:
    duration = float(item.get("duration_seconds") or 0)
    if duration > 0:
        return duration
    analysis = get_media_analysis(root, int(item["id"])) or {}
    duration = float(
        (analysis.get("technical") or {}).get("duration_seconds") or 0
    )
    if duration > 0:
        return duration
    duration = float(probe_media(path).get("duration_seconds") or 0)
    if duration <= 0:
        raise SemanticVisionError("Durée vidéo indéterminable.")
    return duration


def extract_reference_frames(
    root: Path,
    media_id: int,
    *,
    samples: int = 4,
    width: int = 448,
    force: bool = False,
) -> list[Path]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SemanticVisionError(
            "ffmpeg est requis pour extraire les images de vision."
        )

    item = _media_row(root, media_id)
    path = _media_path(root, item)
    duration = _duration(root, item, path)
    samples = max(2, min(int(samples), 8))
    width = max(224, min(int(width), 768))

    out_dir = root / "cache" / "vision" / f"media_{int(media_id):06d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(out_dir.glob("frame_*.jpg"))
    if len(existing) >= samples and not force:
        return existing[:samples]
    for old in existing:
        old.unlink(missing_ok=True)

    fps = samples / max(duration, 0.1)
    pattern = out_dir / "frame_%02d.jpg"
    proc = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(path),
            "-vf",
            f"fps={fps:.8f},scale={width}:-2:flags=lanczos",
            "-frames:v",
            str(samples),
            "-q:v",
            "3",
            str(pattern),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise SemanticVisionError(
            proc.stderr.decode("utf-8", "replace").strip()
            or "Extraction des images vision impossible."
        )
    frames = sorted(out_dir.glob("frame_*.jpg"))
    if not frames:
        raise SemanticVisionError("Aucune image de vision extraite.")
    return frames[:samples]


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(float(x) ** 2 for x in vector))
    if norm <= 0:
        raise SemanticVisionError("Embedding vision vide.")
    return [float(x) / norm for x in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        raise SemanticVisionError("Embeddings incompatibles.")
    an = _normalize(a)
    bn = _normalize(b)
    return sum(x * y for x, y in zip(an, bn))


def store_semantic_profile(
    root: Path,
    media_id: int,
    *,
    embedding: list[float],
    provider: str = VISION_PROVIDER,
    model_id: str = DEFAULT_MODEL_ID,
    frame_count: int = 0,
    status: str = "READY",
) -> dict:
    _media_row(root, media_id)
    clean = _normalize([float(x) for x in embedding])
    conn = connect(root / "media.sqlite")
    try:
        conn.execute(
            """
            INSERT INTO semantic_profiles(
              media_id, provider, model_id, embedding_json, frame_count, status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(media_id, provider, model_id) DO UPDATE SET
              embedding_json=excluded.embedding_json,
              frame_count=excluded.frame_count,
              status=excluded.status,
              updated_at=CURRENT_TIMESTAMP
            """,
            (
                int(media_id),
                provider,
                model_id,
                json.dumps(clean),
                int(frame_count),
                status,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return get_semantic_profile(
        root,
        media_id,
        provider=provider,
        model_id=model_id,
    ) or {}


def get_semantic_profile(
    root: Path,
    media_id: int,
    *,
    provider: str = VISION_PROVIDER,
    model_id: str = DEFAULT_MODEL_ID,
) -> dict | None:
    conn = connect(root / "media.sqlite")
    try:
        row = conn.execute(
            """
            SELECT * FROM semantic_profiles
            WHERE media_id=? AND provider=? AND model_id=?
            """,
            (int(media_id), provider, model_id),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    out = dict(row)
    try:
        out["embedding"] = json.loads(out.pop("embedding_json"))
    except Exception:
        out["embedding"] = []
    return out


def list_semantic_profiles(
    root: Path,
    *,
    provider: str = VISION_PROVIDER,
    model_id: str = DEFAULT_MODEL_ID,
) -> dict[int, dict]:
    conn = connect(root / "media.sqlite")
    try:
        rows = conn.execute(
            """
            SELECT * FROM semantic_profiles
            WHERE provider=? AND model_id=?
            ORDER BY media_id
            """,
            (provider, model_id),
        ).fetchall()
    finally:
        conn.close()
    out: dict[int, dict] = {}
    for row in rows:
        item = dict(row)
        try:
            item["embedding"] = json.loads(item.pop("embedding_json"))
        except Exception:
            item["embedding"] = []
        out[int(item["media_id"])] = item
    return out


def analyze_semantic_media(
    root: Path,
    media_id: int,
    *,
    provider: VisionProvider | None = None,
    allow_model_download: bool = False,
    force_frames: bool = False,
) -> dict:
    provider = provider or LocalClipProvider()
    frames = extract_reference_frames(
        root,
        media_id,
        force=force_frames,
    )
    embedding = provider.embed_images(
        frames,
        allow_model_download=allow_model_download,
    )
    return store_semantic_profile(
        root,
        media_id,
        embedding=embedding,
        provider=provider.provider,
        model_id=provider.model_id,
        frame_count=len(frames),
        status="READY",
    )


def analyze_semantic_catalog(
    root: Path,
    *,
    provider: VisionProvider | None = None,
    allow_model_download: bool = False,
) -> dict:
    provider = provider or LocalClipProvider()
    videos = [
        x
        for x in fetch_media_with_metadata(root)
        if x.get("kind") == "video"
    ]
    ready = 0
    failed: list[dict] = []
    for item in videos:
        try:
            analyze_semantic_media(
                root,
                int(item["id"]),
                provider=provider,
                allow_model_download=allow_model_download,
            )
            ready += 1
        except Exception as exc:
            failed.append(
                {"media_id": int(item["id"]), "error": str(exc)}
            )
    return {
        "total": len(videos),
        "ready": ready,
        "failed": failed,
        "provider": provider.provider,
        "model_id": provider.model_id,
    }


def _structured_tags(item: dict) -> list[tuple[str, str]]:
    out = []
    for raw in item.get("tags") or []:
        tag = str(raw).strip().lower()
        if ":" not in tag:
            continue
        facet, value = tag.split(":", 1)
        if facet in FACET_THRESHOLDS and value.strip():
            out.append((facet, f"{facet}:{value.strip()}"))
    return out


def _centroid(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        raise SemanticVisionError("Aucun vecteur de référence.")
    size = len(vectors[0])
    if any(len(v) != size for v in vectors):
        raise SemanticVisionError("Références d’embedding incompatibles.")
    mean = [
        sum(float(v[i]) for v in vectors) / len(vectors)
        for i in range(size)
    ]
    return _normalize(mean)


def propose_semantic_tags(
    root: Path,
    media_id: int,
    *,
    provider: str = VISION_PROVIDER,
    model_id: str = DEFAULT_MODEL_ID,
    thresholds: dict[str, float] | None = None,
    reset_rejected: bool = False,
) -> dict:
    thresholds = {
        **FACET_THRESHOLDS,
        **(thresholds or {}),
    }
    target = _media_row(root, media_id)
    target_profile = get_semantic_profile(
        root,
        media_id,
        provider=provider,
        model_id=model_id,
    )
    if not target_profile or target_profile.get("status") != "READY":
        raise SemanticVisionError(
            "Analyse sémantique du rush requise avant proposition."
        )
    target_embedding = target_profile.get("embedding") or []
    current_tags = {str(x).lower() for x in target.get("tags") or []}

    items = fetch_media_with_metadata(root)
    profiles = list_semantic_profiles(
        root,
        provider=provider,
        model_id=model_id,
    )
    references: dict[str, list[tuple[int, list[float]]]] = {}
    facets: dict[str, str] = {}
    for item in items:
        iid = int(item["id"])
        if iid == int(media_id):
            continue
        profile = profiles.get(iid)
        if not profile or profile.get("status") != "READY":
            continue
        embedding = profile.get("embedding") or []
        if not embedding:
            continue
        for facet, tag in _structured_tags(item):
            references.setdefault(tag, []).append((iid, embedding))
            facets[tag] = facet

    conn = connect(root / "media.sqlite")
    try:
        existing_rows = conn.execute(
            """
            SELECT * FROM semantic_tag_proposals
            WHERE media_id=? AND provider=? AND model_id=?
            """,
            (int(media_id), provider, model_id),
        ).fetchall()
        existing = {row["tag"]: dict(row) for row in existing_rows}

        proposed: list[dict] = []
        for tag, refs in references.items():
            if tag in current_tags:
                continue
            facet = facets[tag]
            threshold = float(thresholds[facet])
            centroid = _centroid([embedding for _, embedding in refs])
            similarity = cosine_similarity(target_embedding, centroid)
            best_id, best_similarity = max(
                (
                    (ref_id, cosine_similarity(target_embedding, emb))
                    for ref_id, emb in refs
                ),
                key=lambda x: x[1],
            )
            if similarity < threshold:
                continue

            old = existing.get(tag)
            if old and old.get("status") == "ACCEPTED":
                continue
            if (
                old
                and old.get("status") == "REJECTED"
                and not reset_rejected
            ):
                continue

            evidence = {
                "method": "reference_embedding_centroid",
                "reference_media_ids": [ref_id for ref_id, _ in refs],
                "reference_count": len(refs),
                "best_reference_media_id": best_id,
                "best_reference_similarity": round(best_similarity, 4),
                "threshold": threshold,
                "human_validation_required": True,
            }
            conn.execute(
                """
                INSERT INTO semantic_tag_proposals(
                  media_id, tag, facet, confidence, provider, model_id,
                  status, evidence_json
                )
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?)
                ON CONFLICT(media_id, tag, provider, model_id) DO UPDATE SET
                  facet=excluded.facet,
                  confidence=excluded.confidence,
                  status='PENDING',
                  evidence_json=excluded.evidence_json,
                  updated_at=CURRENT_TIMESTAMP
                """,
                (
                    int(media_id),
                    tag,
                    facet,
                    round(float(similarity), 6),
                    provider,
                    model_id,
                    json.dumps(evidence, ensure_ascii=False),
                ),
            )
        conn.commit()
    finally:
        conn.close()

    return {
        "media_id": int(media_id),
        "provider": provider,
        "model_id": model_id,
        "policy": {
            "human_validation_required": True,
            "automatic_tag_write": False,
            "automatic_storyline_change": False,
        },
        "proposals": list_semantic_proposals(
            root,
            media_id,
            provider=provider,
            model_id=model_id,
        ),
    }


def list_semantic_proposals(
    root: Path,
    media_id: int,
    *,
    provider: str = VISION_PROVIDER,
    model_id: str = DEFAULT_MODEL_ID,
) -> list[dict]:
    conn = connect(root / "media.sqlite")
    try:
        rows = conn.execute(
            """
            SELECT * FROM semantic_tag_proposals
            WHERE media_id=? AND provider=? AND model_id=?
            ORDER BY
              CASE status WHEN 'PENDING' THEN 0 WHEN 'ACCEPTED' THEN 1 ELSE 2 END,
              confidence DESC, id
            """,
            (int(media_id), provider, model_id),
        ).fetchall()
    finally:
        conn.close()
    out = []
    for row in rows:
        item = dict(row)
        try:
            item["evidence"] = json.loads(item.pop("evidence_json"))
        except Exception:
            item["evidence"] = {}
        out.append(item)
    return out


def resolve_semantic_proposal(
    root: Path,
    proposal_id: int,
    *,
    accept: bool,
) -> dict:
    conn = connect(root / "media.sqlite")
    try:
        row = conn.execute(
            "SELECT * FROM semantic_tag_proposals WHERE id=?",
            (int(proposal_id),),
        ).fetchone()
        if row is None:
            raise SemanticVisionError(
                f"Proposition introuvable : id={proposal_id}"
            )
        proposal = dict(row)
        new_status = "ACCEPTED" if accept else "REJECTED"
        conn.execute(
            """
            UPDATE semantic_tag_proposals
            SET status=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (new_status, int(proposal_id)),
        )
        conn.commit()
    finally:
        conn.close()

    if accept:
        media = _media_row(root, int(proposal["media_id"]))
        tags = list(media.get("tags") or [])
        normalized = {str(x).lower() for x in tags}
        if proposal["tag"].lower() not in normalized:
            tags.append(proposal["tag"])
            set_media_metadata(
                root,
                int(proposal["media_id"]),
                tags=tags,
            )

    rows = list_semantic_proposals(
        root,
        int(proposal["media_id"]),
        provider=proposal["provider"],
        model_id=proposal["model_id"],
    )
    resolved = next(x for x in rows if int(x["id"]) == int(proposal_id))
    return resolved
