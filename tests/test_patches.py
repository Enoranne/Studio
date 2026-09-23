from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from piste_studio.project import init_project
from piste_studio.locks import add_lock
from piste_studio.versioning import create_brief_version, list_versions
from piste_studio.patches import create_validated_patch


class PatchTests(unittest.TestCase):
    def test_patch_creates_new_version_outside_lock(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / 'PISTE_0'
            init_project(root, 'PISTE 0')
            add_lock(root, 'Opening', 0, 17.24, 'HARD', ['trim'])
            base = create_brief_version(root, 'teaser_30', {'schema_version': 2}, {'schema_version': 1})
            rec = create_validated_patch(
                root,
                edit_name='teaser_30',
                base_version=base.version_label,
                operation='trim',
                start=20,
                end=21,
                target='timeline',
                property_name='duration',
                old_value='1.0',
                new_value='0.8',
            )
            self.assertEqual(rec.version_label, 'V002')
            self.assertTrue(rec.patch_path.exists())
            self.assertEqual(len(list_versions(root, 'teaser_30')), 2)

    def test_patch_blocked_inside_hard_lock(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / 'PISTE_0'
            init_project(root, 'PISTE 0')
            add_lock(root, 'Opening', 0, 17.24, 'HARD', ['trim'])
            base = create_brief_version(root, 'teaser_30', {'schema_version': 2}, {'schema_version': 1})
            with self.assertRaises(ValueError):
                create_validated_patch(
                    root,
                    edit_name='teaser_30',
                    base_version=base.version_label,
                    operation='trim',
                    start=12,
                    end=13,
                    target='timeline',
                    property_name='duration',
                    old_value='1.0',
                    new_value='0.8',
                )
            self.assertEqual(len(list_versions(root, 'teaser_30')), 1)


if __name__ == '__main__':
    unittest.main()
