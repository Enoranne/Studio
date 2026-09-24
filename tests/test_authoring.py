from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import unittest

from piste_studio.project import init_project
from piste_studio.media import scan_media
from piste_studio.db import connect
from piste_studio.decision_engine import build_teaser_brief
from piste_studio.versioning import create_brief_version, create_timeline_version
from piste_studio.tesseract_bridge import save_tesseract_config, execute_bootstrap, TesseractBridgeError
from piste_studio.authoring import build_authoring_plan, execute_authoring
from piste_studio.timeline import save_timeline
from piste_studio.metadata import set_media_metadata, fetch_media_with_metadata


FAKE_AUTHOR_CLI = r'''#!/usr/bin/python3
import json, pathlib, sys
args=sys.argv[1:]

def arg(name):
    return args[args.index(name)+1]

if args == ['--version']:
    print('Tesseract CLI v0.2.0'); raise SystemExit(0)
if args[:2] == ['project','--help']:
    print('project create inspect schema import-video import-asset checkout commit apply'); raise SystemExit(0)
if args and args[0] == 'export' and '--help' in args:
    print('export --project --output --resolution --fps --format'); raise SystemExit(0)
if args[:2] == ['project','create']:
    p=pathlib.Path(arg('--project'))
    doc={'duration':3.0,'width':1080,'height':1920,'composition':{'id':'main','layers':[]},'resources':[]}
    p.write_text(json.dumps(doc))
    print('created'); raise SystemExit(0)
if args[:2] == ['project','inspect']:
    p=pathlib.Path(arg('--project')); print(json.dumps(json.loads(p.read_text()), indent=2)); raise SystemExit(0)
if args[:2] == ['project','schema']:
    if '--document' in args:
        print(json.dumps({'title':'document-schema','definitions':{'layer':{'typeValues':['Video','Audio'],'fields':['activeRange','sourceRange','sourceIntrinsicDuration','volume','source','transform']}}}))
    else:
        print(json.dumps({'title':'action-schema'}))
    raise SystemExit(0)
if args[:2] == ['project','import-video']:
    p=pathlib.Path(arg('--project')); f=pathlib.Path(arg('--file')); aid=arg('--asset-id')
    if 'fail' in f.name:
        print('decoder failed', file=sys.stderr); raise SystemExit(5)
    doc=json.loads(p.read_text())
    if any(r.get('assetId') == aid for r in doc.get('resources', [])):
        print('duplicate asset id', file=sys.stderr); raise SystemExit(6)
    meta={'assetId':aid,'durationMs':10000,'width':1920,'height':1080}
    doc.setdefault('resources',[]).append(meta); p.write_text(json.dumps(doc))
    print(json.dumps(meta)); raise SystemExit(0)

if args[:2] == ['project','import-asset']:
    p=pathlib.Path(arg('--project')); f=pathlib.Path(arg('--file')); aid=arg('--asset-id'); kind=arg('--kind')
    if kind != 'audio': print('unsupported asset kind', file=sys.stderr); raise SystemExit(9)
    doc=json.loads(p.read_text())
    if any(r.get('assetId') == aid for r in doc.get('resources', [])):
        print('duplicate asset id', file=sys.stderr); raise SystemExit(6)
    doc.setdefault('resources',[]).append({'assetId':aid,'kind':'audio'}); p.write_text(json.dumps(doc))
    print(json.dumps({'assetId':aid,'kind':'audio'})); raise SystemExit(0)
if args[:2] == ['project','checkout']:
    p=pathlib.Path(arg('--project')); out=pathlib.Path(arg('--output')); out.write_text(p.read_text()); print(str(out)); raise SystemExit(0)
if args[:2] == ['project','commit']:
    p=pathlib.Path(arg('--project')); f=pathlib.Path(arg('--file')); doc=json.loads(f.read_text())
    if doc.get('duration',0) <= 0: print('bad duration', file=sys.stderr); raise SystemExit(7)
    for layer in doc.get('composition',{}).get('layers',[]):
        if layer.get('type') == 'Video':
            for k in ['activeRange','sourceRange','sourceIntrinsicDuration','source','transform']:
                if k not in layer: print('bad video layer', file=sys.stderr); raise SystemExit(8)
        if layer.get('type') == 'Audio':
            for k in ['activeRange','sourceRange','sourceIntrinsicDuration','source','volume']:
                if k not in layer: print('bad audio layer', file=sys.stderr); raise SystemExit(10)
    p.write_text(json.dumps(doc)); print('committed'); raise SystemExit(0)
if args[:2] == ['project','apply']:
    print('applied'); raise SystemExit(0)
if args and args[0] in ['preview','filmstrip','export']:
    out=pathlib.Path(arg('--output')); out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(b'fake-output'); print(str(out)); raise SystemExit(0)
print('unsupported', args, file=sys.stderr); raise SystemExit(2)
'''


def make_project(base: Path, filename: str = 'safe.mp4'):
    root=base/'PISTE_0'; init_project(root,'PISTE 0')
    (root/'rushes'/filename).write_bytes(b'video')
    scan_media(root)
    conn=connect(root/'media.sqlite')
    try:
        row=conn.execute('SELECT id FROM media').fetchone()
        conn.execute("UPDATE media SET status='CANONICAL', canonical=1, trailer_safe=1, spoiler_level=0 WHERE id=?", (row['id'],))
        conn.execute("INSERT INTO media_metadata(media_id,title,duration_seconds,rating,tags_json) VALUES (?,?,?,?,?)", (row['id'],'Safe shot',10.0,5,'[]'))
        conn.commit()
    finally: conn.close()
    brief, decisions=build_teaser_brief(root,duration_seconds=30,max_spoiler=0,aspect_ratio='16:9')
    rec=create_brief_version(root,'teaser_30',brief,decisions)
    return root, rec.edit_name, rec.version_label


def install_fake(base: Path, root: Path):
    cli=base/'tsrct'; cli.write_text(FAKE_AUTHOR_CLI); cli.chmod(0o755)
    save_tesseract_config(root,cli_path=str(cli),expected_version='0.2.0')
    return cli


class AuthoringTests(unittest.TestCase):
    def test_authoring_plan_is_auditable_without_cli(self):
        with TemporaryDirectory() as tmp:
            root, edit, version=make_project(Path(tmp))
            plan=build_authoring_plan(root,edit,version)
            self.assertEqual(plan['deliverable']['canvas'], {'width':1920,'height':1080})
            self.assertEqual(len(plan['cuts']),5)
            self.assertEqual(len(plan['media']),1)
            self.assertTrue(plan['policy']['work_on_copy_then_atomic_replace'])

    def test_dry_run_never_creates_tesseract_project(self):
        with TemporaryDirectory() as tmp:
            root, edit, version=make_project(Path(tmp))
            result=execute_authoring(root,edit,version,dry_run=True)
            self.assertTrue(result['dry_run'])
            version_dir=root/'edits'/edit/version
            self.assertFalse((version_dir/f'{edit}_{version}.tsrct').exists())
            self.assertTrue((version_dir/'authoring-plan.json').exists())

    @unittest.skipIf(os.name == 'nt','POSIX executable fixture')
    def test_real_authoring_materializes_video_layers(self):
        with TemporaryDirectory() as tmp:
            base=Path(tmp); root, edit, version=make_project(base); install_fake(base,root)
            execute_bootstrap(root,edit,version,dry_run=False)
            result=execute_authoring(root,edit,version,dry_run=False)
            self.assertFalse(result['dry_run'])
            self.assertEqual(len(result['manifest']['layers']),5)
            project=root/'edits'/edit/version/f'{edit}_{version}.tsrct'
            doc=json.loads(project.read_text())
            self.assertEqual(doc['duration'],30.0)
            self.assertEqual((doc['width'],doc['height']),(1920,1080))
            layers=doc['composition']['layers']
            self.assertEqual([l['id'] for l in layers],[1,2,3,4,5])
            self.assertTrue(all(l['type']=='Video' for l in layers))
            self.assertEqual(layers[0]['activeRange'], {'start':0,'duration':3600})
            self.assertEqual(layers[0]['sourceRange'], {'start':0,'duration':3600})
            self.assertEqual(layers[0]['volume'],1.0)
            self.assertTrue((root/'edits'/edit/version/'authoring-manifest.json').exists())

    @unittest.skipIf(os.name == 'nt','POSIX executable fixture')
    def test_existing_overlay_stays_front_and_ids_are_preserved(self):
        with TemporaryDirectory() as tmp:
            base=Path(tmp); root, edit, version=make_project(base); install_fake(base,root)
            execute_bootstrap(root,edit,version,dry_run=False)
            project=root/'edits'/edit/version/f'{edit}_{version}.tsrct'
            doc=json.loads(project.read_text())
            doc['composition']['layers'].append({'type':'FxRect','id':7,'name':'Existing overlay'})
            project.write_text(json.dumps(doc))
            execute_authoring(root,edit,version,dry_run=False)
            after=json.loads(project.read_text())
            self.assertEqual(after['composition']['layers'][0]['id'],7)
            self.assertEqual(after['composition']['layers'][1]['id'],8)

    @unittest.skipIf(os.name == 'nt','POSIX executable fixture')
    def test_failed_import_leaves_original_tsrct_untouched(self):
        with TemporaryDirectory() as tmp:
            base=Path(tmp); root, edit, version=make_project(base,'fail.mp4'); install_fake(base,root)
            execute_bootstrap(root,edit,version,dry_run=False)
            project=root/'edits'/edit/version/f'{edit}_{version}.tsrct'
            before=project.read_bytes()
            with self.assertRaises(TesseractBridgeError):
                execute_authoring(root,edit,version,dry_run=False)
            self.assertEqual(project.read_bytes(),before)
            self.assertFalse((root/'edits'/edit/version/'authoring-manifest.json').exists())

    @unittest.skipIf(os.name == 'nt','POSIX executable fixture')
    def test_timeline_version_authors_video_and_audio(self):
        with TemporaryDirectory() as tmp:
            base=Path(tmp); root, _, _=make_project(base)
            (root/'audio'/'voice.wav').write_bytes(b'audio')
            scan_media(root)
            rows=fetch_media_with_metadata(root)
            video=next(x for x in rows if x['kind']=='video')
            audio=next(x for x in rows if x['kind']=='audio')
            set_media_metadata(root,audio['id'],title='Voice',duration_seconds=10.0)
            timeline={
                'edit_name':'teaser_ui','duration_seconds':12,
                'tracks':[
                    {'id':'video','name':'VIDEO','kind':'video','muted':False,'locked':False},
                    {'id':'vo','name':'VO','kind':'audio','muted':False,'locked':False},
                    {'id':'titles','name':'TITLES','kind':'title','muted':False,'locked':False},
                ],
                'clips':[
                    {'id':'v1','track':'video','label':'Shot','start':3,'duration':4,'sourceStart':1,'mediaDbId':video['id']},
                    {'id':'a1','track':'vo','label':'Voice','start':3,'duration':5,'sourceStart':.5,'audioDbId':audio['id'],'gainDb':-6,'pan':-.25,'audioRole':'vo','fadeIn':.2,'fadeOut':.3,'volumeEnvelope':[{'time':1,'gainDb':-6},{'time':3,'gainDb':-12}]},
                    {'id':'t1','track':'titles','label':'PISTE 0','text':'PISTE 0','start':8,'duration':2,'titlePreset':'lower_third','fontFamily':'sans','fontSize':72,'fontWeight':700,'textAlign':'center','positionX':.5,'positionY':.82,'boxWidth':.8,'color':'#FFFFFF','backgroundColor':'#000000','backgroundOpacity':.25,'opacity':1,'padding':.02,'cornerRadius':.01},
                ],
            }
            save_timeline(root,timeline)
            rec=create_timeline_version(root,timeline)
            plan=build_authoring_plan(root,rec.edit_name,rec.version_label)
            self.assertEqual(plan['source'],'timeline.json')
            self.assertEqual(len(plan['cuts']),1)
            self.assertEqual(len(plan['audio_cuts']),1)
            self.assertEqual(len(plan['title_cuts']),1)
            title_cut=plan['title_cuts'][0]
            self.assertEqual(title_cut['text'],'PISTE 0')
            self.assertEqual(title_cut['preset'],'lower_third')
            self.assertEqual(title_cut['font_size'],72.0)
            self.assertEqual(title_cut['background_opacity'],.25)
            audio_cut=plan['audio_cuts'][0]
            self.assertAlmostEqual(audio_cut['volume'],10**(-6/20),places=6)
            self.assertEqual(audio_cut['gain_db'],-6)
            self.assertEqual(audio_cut['pan'],-.25)
            self.assertEqual(audio_cut['role'],'vo')
            self.assertEqual(audio_cut['volume_envelope'],[
                {'time_ms':1000,'gain_db':-6.0},
                {'time_ms':3000,'gain_db':-12.0},
            ])
            install_fake(base,root)
            execute_bootstrap(root,rec.edit_name,rec.version_label,dry_run=False)
            result=execute_authoring(root,rec.edit_name,rec.version_label,dry_run=False)
            self.assertEqual(len(result['manifest']['layers']),1)
            self.assertEqual(len(result['manifest']['audio_layers']),1)
            self.assertEqual(result['manifest']['title_layers'],[])
            self.assertEqual(len(result['manifest']['unmaterialized_titles']),1)
            self.assertIn('schéma Tesseract installé ne confirme pas', ' '.join(result['manifest']['warnings']))
            project=root/'edits'/rec.edit_name/rec.version_label/f'{rec.edit_name}_{rec.version_label}.tsrct'
            doc=json.loads(project.read_text())
            kinds=[x['type'] for x in doc['composition']['layers']]
            self.assertEqual(kinds,['Video','Audio'])
            audio_layer=doc['composition']['layers'][1]
            self.assertEqual(audio_layer['activeRange'],{'start':3000,'duration':5000})
            self.assertEqual(audio_layer['sourceRange'],{'start':500,'duration':5000})
            self.assertAlmostEqual(audio_layer['volume'],10**(-6/20),places=6)
            manifest_audio=result['manifest']['audio_layers'][0]
            self.assertEqual(manifest_audio['gain_db'],-6)
            self.assertEqual(manifest_audio['pan'],-.25)
            self.assertEqual(manifest_audio['role'],'vo')
            self.assertEqual(manifest_audio['volume_envelope'],[
                {'time_ms':1000,'gain_db':-6.0},
                {'time_ms':3000,'gain_db':-12.0},
            ])

    @unittest.skipIf(os.name == 'nt','POSIX executable fixture')
    def test_second_authoring_is_refused(self):
        with TemporaryDirectory() as tmp:
            base=Path(tmp); root, edit, version=make_project(base); install_fake(base,root)
            execute_bootstrap(root,edit,version,dry_run=False)
            execute_authoring(root,edit,version,dry_run=False)
            with self.assertRaises(TesseractBridgeError):
                execute_authoring(root,edit,version,dry_run=False)


if __name__ == '__main__': unittest.main()
