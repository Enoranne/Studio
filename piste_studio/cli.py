from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
import json
import sqlite3
import sys

from .authoring import execute_authoring, save_authoring_plan
from .decision_engine import build_teaser_brief
from .locks import add_lock, check_operation
from .media import scan_media
from .metadata import fetch_media_with_metadata, set_media_metadata
from .patches import create_validated_patch
from .project import ProjectError, init_project, load_project, verify_master
from .readiness import build_production_readiness
from .tesseract_bridge import (
    TesseractBridgeError, detect_tesseract, execute_bootstrap, execute_export,
    execute_filmstrip, execute_patch_actions, execute_preview, save_execution_plan,
    save_tesseract_config,
)
from .versioning import create_brief_version, list_versions


def root_of(value: str) -> Path:
    return Path(value).expanduser().resolve()


def cmd_init(a):
    p = init_project(root_of(a.root), a.name, Path(a.master) if a.master else None)
    print(f"CREATED {p.root}")
    return 0


def cmd_scan(a):
    root = root_of(a.root); load_project(root)
    print(json.dumps(scan_media(root), ensure_ascii=False))
    return 0


def cmd_master(a):
    ok, msg = verify_master(root_of(a.root)); print("MASTER OK" if ok else "MASTER DRIFT"); print(msg)
    return 0 if ok else 3


def cmd_lock_add(a):
    lock = add_lock(root_of(a.root), a.name, a.start, a.end, a.level, a.forbid)
    print(json.dumps(lock, ensure_ascii=False)); return 0


def cmd_check(a):
    d = check_operation(root_of(a.root), a.operation, a.start, a.end, a.target, a.explicit_soft_unlock)
    print(d.decision); print(d.reason); return 0 if d.allowed else 2


def cmd_media_list(a):
    for m in fetch_media_with_metadata(root_of(a.root)):
        print(f"{m['id']:>4} {m['kind']:<5} {m['status']:<10} spoiler={m['spoiler_level']} canon={m['canonical']} trailer_safe={m['trailer_safe']} rating={m['rating']} {m['relative_path']}")
    return 0


def cmd_media_annotate(a):
    set_media_metadata(root_of(a.root), a.id, title=a.title, description=a.description, duration_seconds=a.duration, rating=a.rating, tags=a.tags)
    print(f"MEDIA ANNOTATED — id={a.id}"); return 0


def cmd_brief(a):
    root = root_of(a.root)
    brief, decisions = build_teaser_brief(root, duration_seconds=a.duration, mood=a.mood, max_spoiler=a.max_spoiler, aspect_ratio=a.aspect_ratio)
    rec = create_brief_version(root, a.name, brief, decisions)
    print(f"BRIEF CREATED — {rec.edit_name}/{rec.version_label}"); return 0


def cmd_versions(a):
    for v in list_versions(root_of(a.root), a.name):
        print(f"{v['edit_name']} {v['version_label']} {v['kind']} parent={v['parent_version_label'] or '—'}")
    return 0


def cmd_patch(a):
    rec = create_validated_patch(root_of(a.root), edit_name=a.name, base_version=a.base, operation=a.operation, start=a.start, end=a.end, target=a.target, property_name=a.property, old_value=a.old, new_value=a.new, explicit_soft_unlock=a.explicit_soft_unlock)
    print(f"PATCH CREATED — {rec.edit_name}/{rec.version_label}"); return 0


def cmd_readiness(a):
    report = build_production_readiness(
        root_of(a.root),
        edit_name=a.name,
        version=a.version,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pipeline_status"] != "BLOCKED" else 5


def cmd_tess_config(a):
    print(save_tesseract_config(root_of(a.root), cli_path=a.cli, expected_version=a.expected_version, telemetry=a.telemetry)); return 0


def cmd_tess_status(a):
    s = detect_tesseract(root_of(a.root)); print(json.dumps(asdict(s), ensure_ascii=False, indent=2)); return 0 if s.ready else 4


def cmd_tess_plan(a):
    print(save_execution_plan(root_of(a.root), a.name, a.version)); return 0


def cmd_tess_bootstrap(a):
    r = execute_bootstrap(root_of(a.root), a.name, a.version, dry_run=not a.execute); print(json.dumps(r, ensure_ascii=False, indent=2)); return 0


def cmd_tess_author_plan(a):
    print(save_authoring_plan(root_of(a.root), a.name, a.version)); return 0


def cmd_tess_author(a):
    r = execute_authoring(root_of(a.root), a.name, a.version, dry_run=not a.execute); print(json.dumps(r, ensure_ascii=False, indent=2)); return 0


def cmd_tess_preview(a):
    print(execute_preview(root_of(a.root), a.name, a.version, time_seconds=a.time, output_name=a.output)); return 0


def cmd_tess_filmstrip(a):
    print(execute_filmstrip(root_of(a.root), a.name, a.version, start_ms=a.start_ms, duration_ms=a.duration_ms, interval_ms=a.interval_ms, output_name=a.output)); return 0


def cmd_tess_export(a):
    print(execute_export(root_of(a.root), a.name, a.version, output_name=a.output, resolution=a.resolution, fps=a.fps, format_name=a.format)); return 0


def cmd_tess_patch(a):
    print(execute_patch_actions(root_of(a.root), a.name, a.version, Path(a.actions))); return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="piste-studio", description="PISTE Studio local filmmaking workspace")
    sp = p.add_subparsers(dest="command", required=True)

    q = sp.add_parser("init"); q.add_argument("--root", required=True); q.add_argument("--name", required=True); q.add_argument("--master"); q.set_defaults(func=cmd_init)
    q = sp.add_parser("scan"); q.add_argument("--root", required=True); q.set_defaults(func=cmd_scan)
    q = sp.add_parser("master-verify"); q.add_argument("--root", required=True); q.set_defaults(func=cmd_master)

    q = sp.add_parser("lock-add"); q.add_argument("--root", required=True); q.add_argument("--name", required=True); q.add_argument("--start", type=float, required=True); q.add_argument("--end", type=float, required=True); q.add_argument("--level", choices=["HARD","SOFT","OPEN"], required=True); q.add_argument("--forbid", nargs="*", default=[]); q.set_defaults(func=cmd_lock_add)
    q = sp.add_parser("check"); q.add_argument("--root", required=True); q.add_argument("--operation", required=True); q.add_argument("--start", type=float); q.add_argument("--end", type=float); q.add_argument("--target", choices=["timeline","master"], default="timeline"); q.add_argument("--explicit-soft-unlock", action="store_true"); q.set_defaults(func=cmd_check)

    q = sp.add_parser("media-list"); q.add_argument("--root", required=True); q.set_defaults(func=cmd_media_list)
    q = sp.add_parser("media-annotate"); q.add_argument("--root", required=True); q.add_argument("--id", type=int, required=True); q.add_argument("--title"); q.add_argument("--description"); q.add_argument("--duration", type=float); q.add_argument("--rating", type=int); q.add_argument("--tags", nargs="*"); q.set_defaults(func=cmd_media_annotate)

    q = sp.add_parser("brief-teaser"); q.add_argument("--root", required=True); q.add_argument("--name", default="teaser_30"); q.add_argument("--duration", type=float, required=True); q.add_argument("--mood", nargs="*"); q.add_argument("--max-spoiler", type=int, default=0); q.add_argument("--aspect-ratio"); q.set_defaults(func=cmd_brief)
    q = sp.add_parser("versions"); q.add_argument("--root", required=True); q.add_argument("--name"); q.set_defaults(func=cmd_versions)
    q = sp.add_parser("patch-create"); q.add_argument("--root", required=True); q.add_argument("--name", required=True); q.add_argument("--base", required=True); q.add_argument("--operation", required=True); q.add_argument("--start", type=float); q.add_argument("--end", type=float); q.add_argument("--target", default="timeline", choices=["timeline","master"]); q.add_argument("--property"); q.add_argument("--old"); q.add_argument("--new"); q.add_argument("--explicit-soft-unlock", action="store_true"); q.set_defaults(func=cmd_patch)
    q = sp.add_parser("readiness"); q.add_argument("--root", required=True); q.add_argument("--name"); q.add_argument("--version"); q.set_defaults(func=cmd_readiness)

    t = sp.add_parser("tesseract").add_subparsers(dest="tesseract_command", required=True)
    q=t.add_parser("configure"); q.add_argument("--root", required=True); q.add_argument("--cli"); q.add_argument("--expected-version", default="0.2.0"); q.add_argument("--telemetry", action="store_true"); q.set_defaults(func=cmd_tess_config)
    q=t.add_parser("status"); q.add_argument("--root", required=True); q.set_defaults(func=cmd_tess_status)
    for name, func in [("plan",cmd_tess_plan),("author-plan",cmd_tess_author_plan)]:
        q=t.add_parser(name); q.add_argument("--root", required=True); q.add_argument("--name", required=True); q.add_argument("--version", required=True); q.set_defaults(func=func)
    for name, func in [("bootstrap",cmd_tess_bootstrap),("author",cmd_tess_author)]:
        q=t.add_parser(name); q.add_argument("--root", required=True); q.add_argument("--name", required=True); q.add_argument("--version", required=True); q.add_argument("--execute", action="store_true"); q.set_defaults(func=func)
    q=t.add_parser("preview"); q.add_argument("--root", required=True); q.add_argument("--name", required=True); q.add_argument("--version", required=True); q.add_argument("--time", type=float, default=1); q.add_argument("--output", default="Preview.png"); q.set_defaults(func=cmd_tess_preview)
    q=t.add_parser("filmstrip"); q.add_argument("--root", required=True); q.add_argument("--name", required=True); q.add_argument("--version", required=True); q.add_argument("--start-ms", type=int, default=0); q.add_argument("--duration-ms", type=int, default=3000); q.add_argument("--interval-ms", type=int, default=250); q.add_argument("--output", default="Filmstrip.png"); q.set_defaults(func=cmd_tess_filmstrip)
    q=t.add_parser("export"); q.add_argument("--root", required=True); q.add_argument("--name", required=True); q.add_argument("--version", required=True); q.add_argument("--output"); q.add_argument("--resolution", choices=["720p","1080p","4k"], default="1080p"); q.add_argument("--fps", type=int, choices=[24,30,60], default=24); q.add_argument("--format", choices=["mp4","prores"], default="mp4"); q.set_defaults(func=cmd_tess_export)
    q=t.add_parser("apply-patch"); q.add_argument("--root", required=True); q.add_argument("--name", required=True); q.add_argument("--version", required=True); q.add_argument("--actions", required=True); q.set_defaults(func=cmd_tess_patch)
    return p


def main() -> None:
    args = build_parser().parse_args()
    try:
        code = args.func(args)
    except (ProjectError, TesseractBridgeError, ValueError, sqlite3.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); code = 1
    raise SystemExit(code)


if __name__ == "__main__":
    main()
