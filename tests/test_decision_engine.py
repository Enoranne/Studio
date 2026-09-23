from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from piste_studio.project import init_project
from piste_studio.media import scan_media
from piste_studio.db import connect
from piste_studio.metadata import set_media_metadata
from piste_studio.decision_engine import build_teaser_brief
from piste_studio.versioning import create_brief_version, list_versions


class DecisionEngineTests(unittest.TestCase):
    def _make_project(self, base: Path) -> Path:
        root = base / "PISTE_0"
        init_project(root, "PISTE 0")
        (root / "rushes" / "safe.mp4").write_bytes(b"safe")
        (root / "rushes" / "spoiler.mp4").write_bytes(b"spoiler")
        scan_media(root)
        conn = connect(root / "media.sqlite")
        try:
            rows = conn.execute("SELECT id, relative_path FROM media ORDER BY id").fetchall()
            ids = {r["relative_path"]: r["id"] for r in rows}
            conn.execute(
                "UPDATE media SET status='APPROVED', spoiler_level=0, canonical=1, trailer_safe=1 WHERE id=?",
                (ids['rushes/safe.mp4'],),
            )
            conn.execute(
                "UPDATE media SET status='APPROVED', spoiler_level=2, canonical=0, trailer_safe=1 WHERE id=?",
                (ids['rushes/spoiler.mp4'],),
            )
            conn.commit()
        finally:
            conn.close()
        set_media_metadata(root, ids['rushes/safe.mp4'], title='REC', rating=5, tags=['rec', 'malo'])
        set_media_metadata(root, ids['rushes/spoiler.mp4'], title='Reveal', rating=5, tags=['spoiler'])
        return root

    def test_brief_filters_spoilers_and_versions(self):
        with TemporaryDirectory() as tmp:
            root = self._make_project(Path(tmp))
            brief, decisions = build_teaser_brief(root, duration_seconds=30, max_spoiler=0)
            self.assertEqual(len(brief['candidate_pool']), 1)
            self.assertEqual(brief['candidate_pool'][0]['title'], 'REC')
            self.assertEqual(sum(b['duration'] for b in brief['suggested_beats']), 30.0)
            rec = create_brief_version(root, 'Teaser 30', brief, decisions)
            self.assertEqual(rec.version_label, 'V001')
            rows = list_versions(root, 'teaser_30')
            self.assertEqual(len(rows), 1)
            self.assertTrue((root / 'edits' / 'teaser_30' / 'V001' / 'brief.yaml').exists())


if __name__ == '__main__':
    unittest.main()
