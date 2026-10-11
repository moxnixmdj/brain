from __future__ import annotations

import pathlib
import sys
import tempfile
import textwrap
import unittest

from canonical.runtime.bound_capabilities import python_repository_acceptance_measurement_v1 as m


class RepositoryAcceptanceMeasurementV1Tests(unittest.TestCase):
    def fixture(self, source: str, test: str):
        td = tempfile.TemporaryDirectory()
        root = pathlib.Path(td.name)
        proj = root / "proj"
        proj.mkdir()
        (proj / "m.py").write_text(source, encoding="utf-8")
        (proj / "test_m.py").write_text(textwrap.dedent(test), encoding="utf-8")
        return td, root, proj

    def run_measure(self, root, **extra):
        args = {
            "source_root": "proj",
            "test_paths": ["test_m.py"],
            "test_argv": [sys.executable, "test_m.py"],
            "output_path": "receipt.json",
            "timeout_s": 5,
        }
        args.update(extra)
        return m.run(args, root)

    def test_passing_tests_are_measured_true(self):
        td, root, _ = self.fixture(
            "def f():\n    return 1\n",
            """
            import unittest
            from m import f
            class T(unittest.TestCase):
                def test_f(self): self.assertEqual(f(), 1)
            if __name__ == "__main__": unittest.main()
            """,
        )
        with td:
            out = self.run_measure(root)
            self.assertTrue(out["pass"], out)
            self.assertTrue(out["measurements"]["tests_pass"])
            self.assertTrue(out["measurements"]["python_parse_ok"])
            self.assertEqual(out["measurements"]["test_count"], 1)
            self.assertTrue(out["measurements"]["repository_source_unchanged"])
            self.assertEqual(out["model_dependency_count"], 0)

    def test_failing_tests_are_measured_false_not_measurement_failure(self):
        td, root, _ = self.fixture(
            "def f():\n    return 1\n",
            """
            import unittest
            from m import f
            class T(unittest.TestCase):
                def test_f(self): self.assertEqual(f(), 2)
            if __name__ == "__main__": unittest.main()
            """,
        )
        with td:
            out = self.run_measure(root)
            self.assertTrue(out["pass"], out)
            self.assertFalse(out["measurements"]["tests_pass"])
            self.assertNotEqual(out["measurements"]["test_returncode"], 0)

    def test_syntax_error_is_objectively_measured(self):
        td, root, _ = self.fixture(
            "def f(:\n    pass\n",
            """
            import unittest
            class T(unittest.TestCase):
                def test_placeholder(self): self.assertTrue(True)
            if __name__ == "__main__": unittest.main()
            """,
        )
        with td:
            out = self.run_measure(root)
            self.assertFalse(out["measurements"]["python_parse_ok"])
            self.assertTrue(out["python_parse_errors"])

    def test_test_side_mutation_occurs_only_in_isolated_copy(self):
        td, root, proj = self.fixture(
            "def f():\n    return 1\n",
            """
            import pathlib, unittest
            class T(unittest.TestCase):
                def test_mutate(self):
                    pathlib.Path("mutated.txt").write_text("x")
                    self.assertTrue(True)
            if __name__ == "__main__": unittest.main()
            """,
        )
        with td:
            out = self.run_measure(root)
            self.assertTrue(out["measurements"]["tests_pass"])
            self.assertFalse((proj / "mutated.txt").exists())
            self.assertTrue(out["measurements"]["repository_source_unchanged"])

    def test_subject_and_spec_hashes_are_deterministic(self):
        td, root, _ = self.fixture(
            "def f():\n    return 1\n",
            """
            import unittest
            class T(unittest.TestCase):
                def test_x(self): self.assertTrue(True)
            if __name__ == "__main__": unittest.main()
            """,
        )
        with td:
            a = self.run_measure(root, output_path="a.json")
            b = self.run_measure(root, output_path="b.json")
            self.assertEqual(a["subject"]["snapshot_sha256"], b["subject"]["snapshot_sha256"])
            self.assertEqual(a["measurement_spec_sha256"], b["measurement_spec_sha256"])
            self.assertEqual(a["measurement_program_sha256"], b["measurement_program_sha256"])

    def test_source_root_escape_rejected(self):
        td, root, _ = self.fixture(
            "def f():\n    return 1\n",
            "import unittest\n",
        )
        with td:
            with self.assertRaisesRegex(m.MeasurementError, "SOURCE_ROOT"):
                self.run_measure(root, source_root="../outside")

    def test_non_python_test_executable_rejected(self):
        td, root, _ = self.fixture(
            "def f():\n    return 1\n",
            "import unittest\n",
        )
        with td:
            with self.assertRaisesRegex(m.MeasurementError, "TEST_EXECUTABLE_NOT_PYTHON"):
                self.run_measure(root, test_argv=["sh", "-c", "true"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
