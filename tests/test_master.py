from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from piste_studio.project import init_project, verify_master


class MasterTests(unittest.TestCase):
    def test_master_integrity_detects_change(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            master = base / "master.mp4"
            master.write_bytes(b"original")
            root = base / "project"
            init_project(root, "PISTE 0", master)
            ok, _ = verify_master(root)
            self.assertTrue(ok)
            master.write_bytes(b"changed")
            ok, _ = verify_master(root)
            self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
