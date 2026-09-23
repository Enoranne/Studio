from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone

from .config import write_yaml, read_yaml
from .db import connect

PROJECT_DIRS = ["master", "rushes", "audio", "graphics", "proxies", "thumbnails", "edits", "logs"]


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    @property
    def project_yaml(self) -> Path: return self.root / "project.yaml"
    @property
    def canon_yaml(self) -> Path: return self.root / "canon.yaml"
    @property
    def locks_yaml(self) -> Path: return self.root / "locks.yaml"
    @property
    def db(self) -> Path: return self.root / "media.sqlite"


class ProjectError(RuntimeError):
    pass


def init_project(root: Path, name: str, master: Path | None = None) -> ProjectPaths:
    root = root.resolve()
    if root.exists() and any(root.iterdir()):
        raise ProjectError(f"Le dossier existe déjà et n'est pas vide : {root}")
    root.mkdir(parents=True, exist_ok=True)
    for d in PROJECT_DIRS: (root / d).mkdir(parents=True, exist_ok=True)
    master_info = None
    if master is not None:
        master = master.expanduser().resolve()
        if not master.exists() or not master.is_file(): raise ProjectError(f"Master introuvable : {master}")
        master_info = {"path": str(master), "filename": master.name, "size_bytes": master.stat().st_size, "sha256": sha256_file(master), "protected": True, "read_only_reference": True}
    now = datetime.now(timezone.utc).isoformat()
    write_yaml(root / "project.yaml", {"schema_version":1,"project":{"name":name,"created_at":now,"master_protected":True,"master":master_info}})
    write_yaml(root / "canon.yaml", {"schema_version":1,"project":{"title":name,"subtitle":""},"visual":{"aspect_ratio":"16:9","look":[],"avoid":[]},"editing":{"principles":[],"avoid":[]},"sound":{"motifs":[],"ending_sequence":[]},"characters":{},"props":{}})
    write_yaml(root / "locks.yaml", {"schema_version":1,"locks":[]})
    connect(root / "media.sqlite").close()
    return ProjectPaths(root)


def load_project(root: Path) -> tuple[ProjectPaths, dict]:
    paths = ProjectPaths(root.expanduser().resolve())
    if not paths.project_yaml.exists(): raise ProjectError(f"Projet PISTE Studio introuvable : {paths.root}")
    return paths, read_yaml(paths.project_yaml)


def verify_master(root: Path) -> tuple[bool, str]:
    _, doc = load_project(root)
    master = doc.get("project", {}).get("master")
    if not master: return False, "Aucun master n'est enregistré dans ce projet."
    path = Path(master["path"])
    if not path.exists(): return False, f"Master introuvable à son emplacement enregistré : {path}"
    if path.stat().st_size != int(master["size_bytes"]): return False, "Le master a changé : taille différente de la référence enregistrée."
    if sha256_file(path) != master["sha256"]: return False, "Le master a changé : empreinte SHA-256 différente."
    return True, "Master intact : taille et SHA-256 correspondent à la référence protégée."
