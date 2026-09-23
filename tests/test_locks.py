from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from piste_studio.project import init_project
from piste_studio.locks import add_lock, check_operation


class LockTests(unittest.TestCase):
    def test_hard_lock_blocks_intersection(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "PISTE_0"
            init_project(root, "PISTE 0")
            add_lock(root, "Opening validated", 0, 17.24, "HARD", ["trim", "reorder"])
            d = check_operation(root, "trim", 12, 13)
            self.assertFalse(d.allowed)
            self.assertEqual(d.decision, "BLOCKED")

    def test_hard_lock_allows_non_forbidden_operation(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "PISTE_0"
            init_project(root, "PISTE 0")
            add_lock(root, "Opening validated", 0, 17.24, "HARD", ["trim"])
            d = check_operation(root, "note", 12, 13)
            self.assertTrue(d.allowed)

    def test_soft_lock_requires_explicit_unlock(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "PISTE_0"
            init_project(root, "PISTE 0")
            add_lock(root, "Scene good", 20, 30, "SOFT", ["trim"])
            d1 = check_operation(root, "trim", 21, 22)
            self.assertFalse(d1.allowed)
            self.assertEqual(d1.decision, "REQUIRES_EXPLICIT_UNLOCK")
            d2 = check_operation(root, "trim", 21, 22, explicit_soft_unlock=True)
            self.assertTrue(d2.allowed)

    def test_master_is_always_blocked(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "PISTE_0"
            init_project(root, "PISTE 0")
            d = check_operation(root, "overwrite", target="master")
            self.assertFalse(d.allowed)
            self.assertEqual(d.decision, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
