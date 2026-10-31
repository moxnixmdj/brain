"""Diff-to-minimal-test-set selection (``python.source.change_impact.testselect.v1``).

Paying a full battery for a one-line edit is the oldest speed tax in
engineering. This capability ends it for Python: parse the changed lines,
locate the touched symbols in the semantic index, walk callers and importers
downstream, and select exactly the tests that can still observe the change.
The law is never-miss with carried evidence: over-selection is a reported
cost, silent omission is a defect.

Pins: chain escalation (helper -> origin -> entrypoint -> its test), import
edges, unrelated-test exclusion, module-wide changes, non-Python truthfulness,
missing-input and path-escape refusals, determinism, and registry contract.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ADAPTER_PATH = os.path.join(
    REPO_ROOT, "canonical", "runtime", "bound_capabilities",
    "python_change_impact_testselect.py",
)
_spec = importlib.util.spec_from_file_location(
    "python_change_impact_testselect_test", ADAPTER_PATH
)
adapter = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = adapter
_spec.loader.exec_module(adapter)

CAPABILITY_ID = "python.source.change_impact.testselect.v1"

A_PY = '''\
def helper(x):
    return x + 1

def origin(x):
    return helper(x) * 2

def leaf(x):
    return x * 3
'''

B_PY = '''\
from pkg.a import origin

def entrypoint(x):
    return origin(x) + leafless(x)

def leafless(x):
    return x
'''

TEST_A = '''\
from pkg.a import helper, origin

def test_helper():
    assert helper(1) == 2
'''

TEST_B = '''\
from pkg.b import entrypoint

def test_entrypoint():
    assert entrypoint(1) == 4
'''

TEST_UNRELATED = '''\
def test_strings():
    assert "a" + "b" == "ab"
'''


def _make_repo(work):
    """pkg: a (helper<-origin), b (imports a, entrypoint<-origin); tests."""
    os.makedirs(os.path.join(work, "pkg"), exist_ok=True)
    os.makedirs(os.path.join(work, "tests"), exist_ok=True)
    open(os.path.join(work, "pkg", "__init__.py"), "w").write("")
    open(os.path.join(work, "pkg", "a.py"), "w").write(A_PY)
    open(os.path.join(work, "pkg", "b.py"), "w").write(B_PY)
    open(os.path.join(work, "tests", "__init__.py"), "w").write("")
    open(os.path.join(work, "tests", "test_a.py"), "w").write(TEST_A)
    open(os.path.join(work, "tests", "test_b.py"), "w").write(TEST_B)
    open(os.path.join(work, "tests", "test_unrelated.py"), "w").write(TEST_UNRELATED)


def _run(work, **extra):
    args = {
        "source_root": ".",
        "output_path": os.path.join(work, "out", "selection.json"),
        "test_roots": ["tests"],
    }
    args.update(extra)
    return adapter.run(args, work)


class ChangeImpactSelectionTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="changeimpact-test-")
        self.addCleanup(shutil.rmtree, self.work, True)
        _make_repo(self.work)

    def _selected(self, result):
        with open(os.path.join(self.work, result["output_path"]), encoding="utf-8") as h:
            return json.load(h)["selected_tests"], json.load

    def _selection(self, result):
        with open(os.path.join(self.work, result["output_path"]), encoding="utf-8") as h:
            return json.load(h)

    def test_a_change_deep_in_a_reaches_every_test_that_can_observe_it(self):
        """helper <- origin <- entrypoint: both test_a and test_b must come
        back; the unrelated string test must not."""
        result = _run(self.work, changed_paths=["pkg/a.py"])
        report = self._selection(result)
        self.assertEqual(result["selected_test_count"], 2)
        self.assertEqual(
            report["selected_tests"], ["tests/test_a.py", "tests/test_b.py"]
        )
        reasons = {t["path"]: t["reason"] for t in report["tests"]}
        self.assertEqual(reasons["tests/test_unrelated.py"], "UNAFFECTED")

    def test_a_change_in_b_selects_only_the_b_test(self):
        result = _run(self.work, changed_paths=["pkg/b.py"])
        report = self._selection(result)
        self.assertEqual(report["selected_tests"], ["tests/test_b.py"])

    def test_a_truly_unobservable_change_selects_no_tests_truthfully(self):
        """`leaf` is defined, uncalled, and unimported anywhere: no test can
        observe the change, so the honest answer is the empty set (never-miss
        protects OBSERVABLE paths; it does not manufacture phantom ones)."""
        diff = (
            "--- a/pkg/a.py\n+++ b/pkg/a.py\n"
            "@@ -7,2 +7,2 @@\n def leaf(x):\n-    return x * 3\n+    return x * 4\n"
        )
        diff_path = os.path.join(self.work, "change.diff")
        open(diff_path, "w").write(diff)
        result = _run(self.work, diff_path="change.diff")
        report = self._selection(result)
        self.assertEqual(report["selected_tests"], [])
        self.assertEqual(result["selected_test_count"], 0)
        self.assertEqual(result["candidate_test_count"], 3)

    def test_an_uncalled_but_imported_symbol_still_selects_its_importer(self):
        """If a test imports the changed symbol by name, it observes it."""
        changed_a = A_PY.replace("def leaf", "def unused_helper")
        open(os.path.join(self.work, "pkg", "a.py"), "w").write(changed_a)
        test_leaf = TEST_A.replace(
            "from pkg.a import helper, origin",
            "from pkg.a import helper, origin, unused_helper",
        )
        open(os.path.join(self.work, "tests", "test_a.py"), "w").write(test_leaf)
        diff = (
            "--- a/pkg/a.py\n+++ b/pkg/a.py\n"
            "@@ -7,2 +7,2 @@\n def unused_helper(x):\n-    return x * 3\n+    return x * 4\n"
        )
        diff_path = os.path.join(self.work, "change.diff")
        open(diff_path, "w").write(diff)
        result = _run(self.work, diff_path="change.diff")
        report = self._selection(result)
        self.assertEqual(report["selected_tests"], ["tests/test_a.py"])

    def test_a_unified_diff_locates_exactly_the_touched_symbol(self):
        """A hunk inside helper() names only helper as the changed symbol."""
        diff = (
            "--- a/pkg/a.py\n+++ b/pkg/a.py\n"
            "@@ -1,2 +1,2 @@\n def helper(x):\n-    return x + 1\n+    return x + 2\n"
        )
        diff_path = os.path.join(self.work, "change.diff")
        open(diff_path, "w").write(diff)
        result = _run(self.work, diff_path="change.diff")
        report = self._selection(result)
        self.assertEqual(result["changed_symbol_count"], 1)
        self.assertEqual(
            report["changed_symbols"]["pkg/a.py"]["symbols"], ["helper"]
        )
        # helper is observed by both chains: helper->origin (same module) and
        # origin->entrypoint (imported into b) so both tests come back.
        self.assertEqual(
            report["selected_tests"], ["tests/test_a.py", "tests/test_b.py"]
        )

    def test_changed_lines_outside_any_definition_are_module_wide_truthfully(self):
        # a line appended AFTER the last definition touches no def span
        diff = (
            "--- a/pkg/a.py\n+++ b/pkg/a.py\n"
            "@@ -8,0 +9,1 @@\n+# trailing module comment\n"
        )
        diff_path = os.path.join(self.work, "change.diff")
        open(diff_path, "w").write(diff)
        result = _run(self.work, diff_path="change.diff")
        report = self._selection(result)
        row = report["changed_symbols"]["pkg/a.py"]
        self.assertEqual(row["reason"], "NO_DEFINITION_SPANS_TOUCHED")
        self.assertTrue(row["module_wide"])

    def test_non_python_changes_are_reported_not_silently_dropped(self):
        result = _run(self.work, changed_paths=["README.md", "pkg/b.py"])
        report = self._selection(result)
        self.assertEqual(result["ignored_non_python_count"], 1)
        self.assertEqual(report["ignored_non_python"], ["README.md"])

    def test_no_input_is_refused(self):
        with self.assertRaises(RuntimeError) as caught:
            _run(self.work)
        self.assertIn("CHANGE_IMPACT_INPUT_REQUIRED", str(caught.exception))

    def test_a_source_root_outside_the_repository_is_refused(self):
        with self.assertRaises(RuntimeError) as caught:
            adapter.run({
                "source_root": "..",
                "output_path": os.path.join(self.work, "o.json"),
                "changed_paths": ["pkg/a.py"],
            }, self.work)
        self.assertIn("PATH_OUTSIDE_REPOSITORY", str(caught.exception))

    def test_determinism_and_artifact_sha(self):
        result_a = _run(self.work, changed_paths=["pkg/a.py"])
        sha_a = result_a["output_sha256"]
        os.remove(os.path.join(self.work, result_a["output_path"]))
        result_b = _run(self.work, changed_paths=["pkg/a.py"])
        self.assertEqual(sha_a, result_b["output_sha256"])
        data = open(
            os.path.join(self.work, result_b["output_path"]), "rb"
        ).read()
        self.assertEqual(sha_a, hashlib.sha256(data).hexdigest())


class ChangeImpactRegistryContractTests(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(
            REPO_ROOT, "canonical", "runtime", "BOUND_CAPABILITY_REGISTRY_V1.json"
        ), "r", encoding="utf-8") as handle:
            self.entry = json.load(handle)["capabilities"][CAPABILITY_ID]

    def test_the_entry_is_a_verified_bound_capability(self):
        self.assertEqual(self.entry["status"], "VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(self.entry["provides"], ["python.source.change_impact.test_selection"])
        self.assertEqual(self.entry["requires"], [])
        self.assertEqual(self.entry["adapter_module"], "python_change_impact_testselect")
        self.assertEqual(self.entry["incremental_spend_usd"], 0)

    def test_every_declared_result_field_is_actually_returned(self):
        work = tempfile.mkdtemp(prefix="changeimpact-contract-")
        self.addCleanup(shutil.rmtree, work, True)
        _make_repo(work)
        result = _run(work, changed_paths=["pkg/a.py"])
        self.assertEqual(sorted(result), sorted(self.entry["result_fields"]))

    def test_the_verification_receipt_exists_and_is_measured(self):
        verification = self.entry["verification"]
        self.assertTrue(verification["independently_verified"])
        for key in ("receipt_path", "state_path"):
            self.assertTrue(
                os.path.isfile(os.path.join(REPO_ROOT, verification[key]))
            )
        self.assertGreater(verification["observed_effect"]["selected_tests"], 0)


if __name__ == "__main__":
    unittest.main()
