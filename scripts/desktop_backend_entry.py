from __future__ import annotations

import argparse
from pathlib import Path
import sys

from piste_studio.app import main as app_main
from piste_studio.project import ProjectError, init_project


def _init_project(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Créer un projet PISTE Studio")
    parser.add_argument("--root", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args(argv)
    try:
        paths = init_project(Path(args.root).expanduser(), args.name)
    except ProjectError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"CREATED {paths.root}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["--init-project"]:
        return _init_project(args[1:])
    return app_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
