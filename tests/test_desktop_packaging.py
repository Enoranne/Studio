from __future__ import annotations

import importlib.util
from pathlib import Path

from piste_studio.project import load_project


_ENTRY = Path(__file__).parents[1] / "scripts" / "desktop_backend_entry.py"
_SPEC = importlib.util.spec_from_file_location("piste_desktop_backend_entry", _ENTRY)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
desktop_backend_main = _MODULE.main


def test_desktop_backend_entry_can_create_project(tmp_path):
    root = tmp_path / "Desktop Project"
    code = desktop_backend_main([
        "--init-project",
        "--root",
        str(root),
        "--name",
        "Desktop Project",
    ])
    assert code == 0
    _, project = load_project(root)
    assert project["project"]["name"] == "Desktop Project"
    assert (root / "project.yaml").is_file()
    assert (root / "rushes").is_dir()
    assert (root / "audio").is_dir()
    assert (root / "edits").is_dir()


def test_desktop_backend_entry_refuses_non_empty_destination(tmp_path):
    root = tmp_path / "Already Used"
    root.mkdir()
    (root / "keep.txt").write_text("keep", encoding="utf-8")
    code = desktop_backend_main([
        "--init-project",
        "--root",
        str(root),
        "--name",
        "Blocked",
    ])
    assert code == 1
    assert not (root / "project.yaml").exists()
