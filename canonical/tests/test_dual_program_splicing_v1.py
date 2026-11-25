"""Pure and runner-backed checks for counterexample-partitioned splicing."""
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import dual_program_splicing_v1 as splice  # noqa: E402

PARENT = "def f(x):\n    return x + 1\n\ndef g(x):\n    return x - 1\n"
A = "def f(x):\n    return x + 2\n\ndef g(x):\n    return x - 1\n"
B = "def f(x):\n    return x + 1\n\ndef g(x):\n    return x - 2\n"


class SplicingTests(unittest.TestCase):
    def test_edits_are_line_level(self):
        self.assertEqual(len(splice.edits(PARENT, A)), 1)
        self.assertEqual(len(splice.edits(PARENT, B)), 1)

    def test_non_overlapping_edits_are_combined(self):
        candidates = splice.splice(PARENT, A, B)
        self.assertIn(
            "def f(x):\n    return x + 2\n\ndef g(x):\n    return x - 2\n",
            candidates,
        )

    def test_splice_is_verified_on_the_union(self):
        with tempfile.TemporaryDirectory() as where:
            root = pathlib.Path(where)
            (root / "mod.py").write_text(PARENT, encoding="utf-8")
            (root / "test_mod.py").write_text(
                "from mod import f, g\n\n"
                "def test_f():\n    assert f(1) == 3\n\n"
                "def test_g():\n    assert g(1) == -1\n",
                encoding="utf-8",
            )
            report = splice.splice_and_verify(
                root, "mod.py", "test_mod.py", PARENT, A, B,
                ["test_mod.py::test_f"], ["test_mod.py::test_g"], 20,
            )
            self.assertTrue(report["verified"])
            self.assertEqual(report["verification"]["outcome"], {
                "test_mod.py::test_f": "PASS", "test_mod.py::test_g": "PASS",
            })
            self.assertEqual((root / "mod.py").read_text(encoding="utf-8"), PARENT)


if __name__ == "__main__":
    unittest.main()
