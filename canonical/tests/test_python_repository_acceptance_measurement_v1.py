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


class RepoRelativeTestPathTests(unittest.TestCase):
    """The compiler states repository-relative paths; the adapter read source-root-relative ones.

    Two spellings of one question.  Refusing the compiler's spelling made this
    capability unreachable from the front door with ``TEST_PATH_INVALID`` even
    though the sentence named a real test file that really was inside the stated
    source root.
    """

    SOURCE = "def f():\n    return 1\n"
    TEST = """
        import unittest
        from m import f
        class T(unittest.TestCase):
            def test_f(self): self.assertEqual(f(), 1)
        if __name__ == "__main__": unittest.main()
        """
    BROKEN = "def f():\n    return 2\n"

    def fixture(self, source=SOURCE):
        td = tempfile.TemporaryDirectory()
        root = pathlib.Path(td.name)
        proj = root / "proj"
        proj.mkdir()
        (proj / "m.py").write_text(source, encoding="utf-8")
        (proj / "test_m.py").write_text(textwrap.dedent(self.TEST), encoding="utf-8")
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

    def test_both_spellings_of_the_same_path_measure_identically(self):
        td, root, _ = self.fixture()
        with td:
            a = self.run_measure(root, test_paths=["test_m.py"])
            b = self.run_measure(root, test_paths=["proj/test_m.py"])
            self.assertTrue(a["pass"], a)
            self.assertTrue(b["pass"], b)
            self.assertEqual(a["measurements"], b["measurements"])
            self.assertEqual(a["test_evidence"]["returncode"], b["test_evidence"]["returncode"])

    def test_a_repo_relative_path_outside_the_source_root_is_still_refused(self):
        # The nearest world in which the test above must fail: widening the
        # accepted spelling must not widen what may be measured.
        td, root, _ = self.fixture()
        with td:
            (root / "outside.py").write_text("x = 1\n", encoding="utf-8")
            with self.assertRaisesRegex(m.MeasurementError, "TEST_PATH_INVALID"):
                self.run_measure(root, test_paths=["outside.py"])

    def test_a_path_that_is_not_a_python_file_is_still_refused(self):
        td, root, _ = self.fixture()
        with td:
            (root / "proj" / "notes.txt").write_text("hello\n", encoding="utf-8")
            with self.assertRaisesRegex(m.MeasurementError, "TEST_PATH_INVALID"):
                self.run_measure(root, test_paths=["proj/notes.txt"])

    def test_a_failing_suite_is_measured_as_failing_and_not_reported_as_passing(self):
        # `pass` on this capability means the measurement succeeded, not that the
        # tests passed.  A failing suite must be measured as failing.
        td, root, _ = self.fixture(source=self.BROKEN)
        with td:
            out = self.run_measure(root, test_paths=["proj/test_m.py"])
            self.assertTrue(out["pass"], out)
            self.assertIs(out["measurements"]["tests_pass"], False)
            self.assertEqual(out["measurements"]["test_returncode"], 1)
            self.assertEqual(out["test_evidence"]["returncode"], 1)
            self.assertIn("MEASUREMENT_SUCCESS_IS_NOT_TASK_ACCEPTANCE", out["hard_nonclaims"])


class SuppliedArgvCarriesTheCallersSpellingTests(unittest.TestCase):
    """The caller states repository-relative paths; measurement runs in a COPIED workspace.

    ``_run_tests`` uses the workspace as its cwd, so a supplied ``test_argv``
    carrying ``proj/test_m.py`` named nothing there: the suite runner loaded no
    tests and the measurement recorded a failure with ``test_count`` 0 for a
    suite that passes.
    """

    SOURCE = "def f():\n    return 1\n"
    TEST = """
        import unittest
        from m import f
        class T(unittest.TestCase):
            def test_f(self): self.assertEqual(f(), 1)
        """

    def fixture(self, source=SOURCE):
        td = tempfile.TemporaryDirectory()
        root = pathlib.Path(td.name)
        proj = root / "proj"
        proj.mkdir()
        (proj / "m.py").write_text(source, encoding="utf-8")
        (proj / "test_m.py").write_text(textwrap.dedent(self.TEST), encoding="utf-8")
        return td, root, proj

    def run_measure(self, root, **extra):
        args = {"source_root": "proj", "test_paths": ["test_m.py"],
                "output_path": "receipt.json", "timeout_s": 10}
        args.update(extra)
        return m.run(args, root)

    def test_a_supplied_argv_naming_the_test_by_its_repo_relative_path_measures_it(self):
        td, root, _ = self.fixture()
        with td:
            argv = m._PATCH.suite_argv(sys.executable, "proj/test_m.py")
            out = self.run_measure(root, test_paths=["proj/test_m.py"], test_argv=argv)
            self.assertIs(out["measurements"]["tests_pass"], True, out["measurements"])
            self.assertEqual(out["measurements"]["test_returncode"], 0)
            self.assertEqual(out["measurements"]["test_count"], 1)

    def test_it_matches_the_measurement_taken_when_no_argv_is_supplied(self):
        td, root, _ = self.fixture()
        with td:
            a = self.run_measure(root, test_paths=["proj/test_m.py"])
            b = self.run_measure(
                root, test_paths=["proj/test_m.py"],
                test_argv=m._PATCH.suite_argv(sys.executable, "proj/test_m.py"))
            self.assertEqual(a["measurements"], b["measurements"])

    def test_a_failing_suite_supplied_the_same_way_is_still_measured_as_failing(self):
        td, root, _ = self.fixture(source="def f():\n    return 2\n")
        with td:
            out = self.run_measure(
                root, test_paths=["proj/test_m.py"],
                test_argv=m._PATCH.suite_argv(sys.executable, "proj/test_m.py"))
            self.assertIs(out["measurements"]["tests_pass"], False)
            self.assertEqual(out["measurements"]["test_returncode"], 1)
            self.assertEqual(out["measurements"]["test_count"], 1)

    def test_an_argument_that_is_not_a_test_path_passes_through_verbatim(self):
        # The nearest world in which the rewrite above must not fire: only tokens
        # that resolve to a validated test file may be touched.
        td, root, _ = self.fixture()
        with td:
            harness = m._PATCH.SUITE_RUNNER + m._PATCH.SUITE_ENTRY
            argv = m._validate_argv(
                [sys.executable, "-c", harness, "proj/test_m.py"],
                ["test_m.py"], root / "proj", root)
            self.assertEqual(argv[0], sys.executable)
            self.assertEqual(argv[1], "-c")
            self.assertEqual(argv[2], harness)
            self.assertEqual(argv[3], "test_m.py")
