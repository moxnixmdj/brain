"""Real traces: only failing execution of declared application files is guidance."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime.bound_capabilities import python_dynamic_fault_localizer_v1 as localizer


class FaultLocalizationSourceScopeTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix="brain-localization-scope-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.write("app/__init__.py", "")
        self.write("app/core.py", "def buggy(x):\n    return x - 1\n")
        self.write("app_extra/noise.py", "def work():\n    n = 0\n    for i in range(2000):\n        n += i\n    return n\n")

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_localizer(self, tests, source="app", **extra):
        return localizer.run({"source_root": source, "test_paths": tests,
                              "output_path": "localization.json", "timeout_s": 10,
                              **extra}, self.root)

    def test_sibling_prefix_code_cannot_supply_application_evidence(self):
        self.write("test_fail.py", "from app_extra.noise import work\nwork()\nassert 1 == 2\n")
        with self.assertRaisesRegex(localizer.FaultLocalizerError,
                                    "NO_LOCALIZED_LINE_FROM_THE_FAILING_RUN"):
            self.run_localizer(["test_fail.py"])
        self.assertFalse((self.root / "localization.json").exists())

    def test_trace_and_ranking_stay_inside_source_plus_stated_test(self):
        self.write("test_fail.py", "from app.core import buggy\nfrom app_extra.noise import work\n"
                                     "work()\nassert buggy(2) == 3\n")
        result = self.run_localizer(["test_fail.py"])
        self.assertEqual(result["ranked_symbols"][0]["symbol"], "buggy")
        self.assertTrue(result["ranked_lines"])
        self.assertTrue(all(row["path"].startswith("app/") for row in result["ranked_lines"]))
        events = result["test_traces"][0]["events"]
        self.assertTrue(all(event[0] == "test_fail.py" or event[0].startswith("app/")
                            for event in events))
        written = json.loads((self.root / "localization.json").read_text())
        self.assertEqual(written["ranked_lines"], result["ranked_lines"])

    def test_irrelevant_events_cannot_exhaust_application_trace_budget(self):
        self.write("test_fail.py", "from app_extra.noise import work\nwork()\n"
                                     "from app.core import buggy\nassert buggy(2) == 3\n")
        result = self.run_localizer(["test_fail.py"], max_trace_events=100)
        self.assertTrue(any(row["function"] == "buggy" and row["line"] == 2
                            for row in result["ranked_lines"]))
        self.assertLess(result["test_traces"][0]["event_count"], 100)

    def test_ignored_environment_is_not_application_when_scope_is_repository(self):
        self.write(".venv/dependency.py", "def noisy():\n    return 1\n")
        self.write("test_fail.py", "import importlib.util\nfrom pathlib import Path\n"
                   "spec = importlib.util.spec_from_file_location('fixture_dependency', "
                   "Path(__file__).parent / '.venv/dependency.py')\n"
                   "dependency = importlib.util.module_from_spec(spec)\n"
                   "spec.loader.exec_module(dependency)\ndependency.noisy()\nassert 1 == 2\n")
        with self.assertRaisesRegex(localizer.FaultLocalizerError,
                                    "NO_LOCALIZED_LINE_FROM_THE_FAILING_RUN"):
            self.run_localizer(["test_fail.py"], source=".")

    def test_arbitrarily_named_stated_test_is_not_application(self):
        self.write("checks.py", "assert 1 == 2\n")
        with self.assertRaisesRegex(localizer.FaultLocalizerError,
                                    "NO_LOCALIZED_LINE_FROM_THE_FAILING_RUN"):
            self.run_localizer(["checks.py"], source=".")

    def test_suffix_named_test_is_not_application(self):
        self.write("arithmetic_test.py", "assert 1 == 2\n")
        with self.assertRaisesRegex(localizer.FaultLocalizerError,
                                    "NO_LOCALIZED_LINE_FROM_THE_FAILING_RUN"):
            self.run_localizer(["arithmetic_test.py"], source=".")

    def test_passing_only_application_execution_cannot_localize_a_failure(self):
        self.write("test_pass.py", "from app.core import buggy\nassert buggy(2) == 1\n")
        self.write("test_fail.py", "assert 1 == 2\n")
        with self.assertRaisesRegex(localizer.FaultLocalizerError,
                                    "NO_LOCALIZED_LINE_FROM_THE_FAILING_RUN"):
            self.run_localizer(["test_fail.py", "test_pass.py"])

    def test_positive_application_trace_and_shared_coverage_are_retained(self):
        self.write("test_pass.py", "from app.core import buggy\nassert buggy(2) == 1\n")
        self.write("test_fail.py", "from app.core import buggy\nassert buggy(2) == 3\n")
        result = self.run_localizer(["test_fail.py", "test_pass.py"])
        self.assertEqual(result["failing_test_count"], 1)
        self.assertEqual(result["passing_test_count"], 1)
        body = next(row for row in result["ranked_lines"] if row["function"] == "buggy")
        self.assertEqual(body["fail_coverage"], 1)
        self.assertEqual(body["pass_coverage"], 1)
        self.assertIn("PASSING_TEST_OVERLAP", body["reasons"])

    def test_application_free_failing_test_refuses(self):
        self.write("test_fail.py", "assert 1 == 2\n")
        with self.assertRaisesRegex(localizer.FaultLocalizerError,
                                    "NO_LOCALIZED_LINE_FROM_THE_FAILING_RUN"):
            self.run_localizer(["test_fail.py"])

    def test_deleted_application_file_cannot_supply_stale_guidance(self):
        self.write("test_fail.py", "from pathlib import Path\nfrom app.core import buggy\n"
                   "(Path(__file__).parent / 'app/core.py').unlink()\nassert buggy(2) == 3\n")
        with self.assertRaisesRegex(localizer.FaultLocalizerError,
                                    "NO_LOCALIZED_LINE_FROM_THE_FAILING_RUN"):
            self.run_localizer(["test_fail.py"])

    def test_positive_run_is_deterministic(self):
        self.write("test_fail.py", "from app.core import buggy\nassert buggy(2) == 3\n")
        before = (self.root / "app/core.py").read_bytes()
        first = self.run_localizer(["test_fail.py"])
        second = self.run_localizer(["test_fail.py"])
        self.assertEqual(first["ranked_lines"], second["ranked_lines"])
        self.assertEqual(first["ranked_symbols"], second["ranked_symbols"])
        self.assertEqual((self.root / "app/core.py").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
