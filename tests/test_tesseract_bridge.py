from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import unittest

from piste_studio.project import init_project
from piste_studio.media import scan_media
from piste_studio.db import connect
from piste_studio.decision_engine import build_teaser_brief
from piste_studio.versioning import create_brief_version
from piste_studio.tesseract_bridge import (
    save_tesseract_config,
    detect_tesseract,
    build_execution_plan,
    execute_bootstrap,
    execute_preview, execute_filmstrip, execute_export, execute_patch_actions,
    TesseractBridgeError,
)


FAKE_CLI = r'''#!/usr/bin/python3
import json, pathlib, sys
args=sys.argv[1:]
if args == ['--version']:
    print('Tesseract CLI v0.2.0')
    raise SystemExit(0)
if args[:2] == ['project','--help']:
    print('project create inspect schema import-video checkout commit apply')
    raise SystemExit(0)
if args and args[0] == 'export' and '--help' in args:
    print('export --project --output --resolution --fps --format')
    raise SystemExit(0)
if args[:2] == ['project','create']:
    p=pathlib.Path(args[args.index('--project')+1]); p.write_bytes(b'fake-tsrct')
    print('created')
    raise SystemExit(0)
if args[:2] == ['project','inspect']:
    print(json.dumps({'composition': {'id':'main'}, 'layers': []}))
    raise SystemExit(0)
if args[:2] == ['project','schema']:
    if '--document' in args:
        print(json.dumps({'title':'document-schema'}))
    else:
        print(json.dumps({'title':'action-schema'}))
    raise SystemExit(0)
if args[:2] == ['project','apply']:
    p=pathlib.Path(args[args.index('--project')+1]); a=pathlib.Path(args[args.index('--actions')+1])
    json.loads(a.read_text()); p.write_bytes(p.read_bytes()+b'-patched')
    print('applied'); raise SystemExit(0)
if args and args[0] in ['preview','filmstrip','export']:
    out=pathlib.Path(args[args.index('--output')+1]); out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(b'fake-output')
    print(str(out)); raise SystemExit(0)
print('unsupported', args, file=sys.stderr)
raise SystemExit(2)
'''


def make_project(base: Path) -> tuple[Path, str, str]:
    root = base / 'PISTE_0'
    init_project(root, 'PISTE 0')
    (root / 'rushes' / 'safe.mp4').write_bytes(b'video')
    scan_media(root)
    conn = connect(root / 'media.sqlite')
    try:
        row = conn.execute("SELECT id FROM media WHERE relative_path='rushes/safe.mp4'").fetchone()
        conn.execute("UPDATE media SET status='APPROVED', trailer_safe=1, spoiler_level=0 WHERE id=?", (row['id'],))
        conn.commit()
    finally:
        conn.close()
    brief, decisions = build_teaser_brief(root, duration_seconds=30, max_spoiler=0)
    rec = create_brief_version(root, 'teaser_30', brief, decisions)
    return root, rec.edit_name, rec.version_label


class TesseractBridgeTests(unittest.TestCase):
    def test_missing_cli_is_not_ready_but_plan_is_available(self):
        with TemporaryDirectory() as tmp:
            root, edit, version = make_project(Path(tmp))
            save_tesseract_config(root, cli_path=str(root/'missing-tsrct'), expected_version='0.2.0')
            status = detect_tesseract(root)
            self.assertFalse(status.ready)
            self.assertFalse(status.found)
            plan = build_execution_plan(root, edit, version)
            self.assertEqual(plan['edit_name'], edit)
            self.assertTrue(plan['policy']['dry_run_default'])
            self.assertIn('create', [c['name'] for c in plan['commands']])
            self.assertIn('import_video', [c['name'] for c in plan['commands']])

    def test_version_mismatch_blocks_execution(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, edit, version = make_project(base)
            cli = base / 'tsrct'
            cli.write_text(FAKE_CLI, encoding='utf-8')
            cli.chmod(0o755)
            save_tesseract_config(root, cli_path=str(cli), expected_version='9.9.9')
            status = detect_tesseract(root)
            self.assertTrue(status.found)
            self.assertFalse(status.ready)
            with self.assertRaises(TesseractBridgeError):
                execute_bootstrap(root, edit, version, dry_run=False)

    @unittest.skipIf(os.name == 'nt', 'POSIX executable fixture')
    def test_valid_fake_cli_bootstrap_captures_schema_without_touching_media(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, edit, version = make_project(base)
            source = root / 'rushes' / 'safe.mp4'
            before = source.read_bytes()
            cli = base / 'tsrct'
            cli.write_text(FAKE_CLI, encoding='utf-8')
            cli.chmod(0o755)
            save_tesseract_config(root, cli_path=str(cli), expected_version='0.2.0')
            status = detect_tesseract(root)
            self.assertTrue(status.ready)
            result = execute_bootstrap(root, edit, version, dry_run=False)
            self.assertFalse(result['dry_run'])
            version_dir = root / 'edits' / edit / version
            self.assertTrue((version_dir / f'{edit}_{version}.tsrct').exists())
            self.assertTrue((version_dir / '.tesseract-work' / 'project.json').exists())
            self.assertTrue((version_dir / '.tesseract-work' / 'project-action.schema.json').exists())
            self.assertTrue((version_dir / '.tesseract-work' / 'document.schema.json').exists())
            self.assertEqual(source.read_bytes(), before)

    def test_master_drift_blocks_plan(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            master = base / 'master.mp4'
            master.write_bytes(b'original')
            root = base / 'PISTE_0'
            init_project(root, 'PISTE 0', master)
            rec = create_brief_version(root, 'teaser_30', {'duration_seconds':30,'candidate_pool':[]}, {})
            save_tesseract_config(root, cli_path=str(base/'missing'), expected_version='0.2.0')
            master.write_bytes(b'changed')
            with self.assertRaises(TesseractBridgeError):
                build_execution_plan(root, rec.edit_name, rec.version_label)

    @unittest.skipIf(os.name == 'nt', 'POSIX executable fixture')
    def test_preview_filmstrip_and_export_after_bootstrap(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, edit, version = make_project(base)
            cli = base / 'tsrct'
            cli.write_text(FAKE_CLI, encoding='utf-8'); cli.chmod(0o755)
            save_tesseract_config(root, cli_path=str(cli), expected_version='0.2.0')
            execute_bootstrap(root, edit, version, dry_run=False)
            self.assertTrue(execute_preview(root, edit, version).exists())
            self.assertTrue(execute_filmstrip(root, edit, version).exists())
            self.assertTrue(execute_export(root, edit, version, fps=24).exists())

    @unittest.skipIf(os.name == 'nt', 'POSIX executable fixture')
    def test_patch_actions_copy_parent_and_apply_atomically(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            root, edit, version = make_project(base)
            cli = base / 'tsrct'
            cli.write_text(FAKE_CLI, encoding='utf-8'); cli.chmod(0o755)
            save_tesseract_config(root, cli_path=str(cli), expected_version='0.2.0')
            execute_bootstrap(root, edit, version, dry_run=False)
            from piste_studio.patches import create_validated_patch
            rec = create_validated_patch(root, edit_name=edit, base_version=version, operation='move_title', start=25, end=26, target='timeline', property_name='start', old_value='25', new_value='25.5')
            actions = base / 'actions.json'
            actions.write_text(json.dumps([{'type':'fakeAction','compositionId':'main'}]), encoding='utf-8')
            out = execute_patch_actions(root, edit, rec.version_label, actions)
            self.assertTrue(out.exists())
            self.assertIn(b'patched', out.read_bytes())
            patch = json.loads((rec.directory/'patch.json').read_text(encoding='utf-8'))
            self.assertEqual(patch['execution']['status'], 'APPLIED_TESSERACT')


if __name__ == '__main__':
    unittest.main()
