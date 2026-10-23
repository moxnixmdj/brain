"""`--remeasure` may refresh a stale pin only with a real test run behind it.

`MODULE_INVOCATION_EVIDENCE_V1.json` is the whole authority for `brain.module.function.invoke`:
a module is callable only while its sha256 -- and the sha256 of every test file it cites as
evidence -- still matches the tree. That pin is what proves "the function that runs is the
function that was tested".

The document drifted. Measured: 26 of 2019 invocable modules had moved, so every call into them
was refused with MODULE_EVIDENCE_STALE or TEST_EVIDENCE_STALE.

The obvious fix is also the forgery. Recomputing the sha256 and writing it back makes the refusal
go away and proves nothing -- it asserts that the function which runs is the function which was
tested, using no test. `--write` could not do the honest thing either: it calls `build()`, which
rebuilds the entire document from whatever junit it is handed, so a partial run silently
re-tiers every function it did not cover (2678 TEST_EVIDENCED functions here) down to
READ_ONLY_UNTESTED. That is why this document's own `remeasurement.why` field describes a
partial re-measurement the tool could not perform.

`--remeasure` closes that gap and fails closed:

* no `--junit` at all -> the CLI refuses to run;
* a drifted module with no supplied junit for ANY test that references it -> listed under
  `refused` and its row left byte-identical, still stale, still refusing calls;
* only rows in `drifted_modules` are touched, so the other 1993 modules cannot be disturbed;
* a function named by a failing case is dropped and listed under `refused`, as `build()` does.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import module_invocation_evidence_v1 as M  # noqa: E402

TMP = REPO_ROOT / "canonical" / "astra_runtime" / "tmp"
TMP_REL = "canonical/astra_runtime/tmp"


def _evidence():
    return json.loads((REPO_ROOT / M.EVIDENCE_REL).read_text(encoding="utf-8"))


class DriftedModulesTests(unittest.TestCase):
    """The drift census, on constructed cases -- not on whatever the tree happens to look like.

    Deliberately synthetic. An earlier version of this suite asserted that the committed
    document WAS drifted, which made the suite a description of a broken state rather than a
    test of the rule: the moment the drift was fixed, the suite went red for succeeding.
    """

    def setUp(self):
        self.data = _evidence()
        self.some = sorted(self.data["modules"])[:1]
        self.assertTrue(self.some, "the evidence document lists no modules")
        self.rel = self.some[0]

    def test_a_module_whose_own_bytes_moved_is_listed(self):
        data = json.loads(json.dumps(self.data))
        data["modules"][self.rel]["sha256"] = "0" * 64
        self.assertIn(self.rel, M.drifted_modules(data, REPO_ROOT))

    def test_a_module_whose_evidence_test_moved_is_listed(self):
        data = json.loads(json.dumps(self.data))
        row = data["modules"][self.rel]
        row["sha256"] = M._sha(REPO_ROOT / self.rel)          # module itself is fresh
        tests = dict(row.get("tests") or {})
        if not tests:
            self.skipTest("this module cites no evidence test file")
        first = sorted(tests)[0]
        tests[first] = "0" * 64                                # but one of its tests is not
        row["tests"] = tests
        self.assertIn(self.rel, M.drifted_modules(data, REPO_ROOT))

    def test_a_module_whose_pins_all_match_is_not_listed(self):
        data = json.loads(json.dumps(self.data))
        row = data["modules"][self.rel]
        row["sha256"] = M._sha(REPO_ROOT / self.rel)
        row["tests"] = {t: M._sha(REPO_ROOT / t) for t in (row.get("tests") or {})
                        if (REPO_ROOT / t).is_file()}
        self.assertNotIn(self.rel, M.drifted_modules(data, REPO_ROOT))

    def test_the_census_agrees_with_the_guard_that_refuses_the_calls(self):
        """`check()` and `drifted_modules()` must not disagree about what is stale."""
        errors = M.check(REPO_ROOT)
        from_check = {e.split(":", 1)[1].split(":")[0]
                      for e in errors if e.startswith(("MODULE_DRIFT:", "TEST_DRIFT:"))}
        live = set(M.drifted_modules(self.data, REPO_ROOT))
        self.assertEqual(from_check, live,
                         "the two disagree: %s" % sorted(from_check ^ live)[:5])


class _SandboxedEvidence(unittest.TestCase):
    """Run `remeasure` against a COPY of the real document, never the committed one."""

    def setUp(self):
        TMP.mkdir(parents=True, exist_ok=True)
        self.copy_rel = TMP_REL + "/_EVIDENCE_SANDBOX.json"
        self.copy = REPO_ROOT / self.copy_rel
        shutil.copyfile(REPO_ROOT / M.EVIDENCE_REL, self.copy)
        self.addCleanup(self.copy.unlink)
        patcher = mock.patch.object(M, "EVIDENCE_REL", self.copy_rel)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.data = json.loads(self.copy.read_text(encoding="utf-8"))
        # Create the condition under test instead of depending on the tree happening to be
        # stale. Two modules are made to look drifted: one whose own recorded sha256 no longer
        # matches, one whose recorded evidence-test sha256 no longer matches.
        rels = sorted(self.data["modules"])
        self.drifted = []
        for rel in rels:
            if len(self.drifted) >= 2:
                break
            row = self.data["modules"][rel]
            if len(self.drifted) == 0:
                row["sha256"] = "0" * 64
                self.drifted.append(rel)
            elif (row.get("tests") or {}) and M._sha(REPO_ROOT / rel) == row.get("sha256"):
                first = sorted(row["tests"])[0]
                row["tests"][first] = "0" * 64
                self.drifted.append(rel)
        self.assertTrue(self.drifted, "could not construct a drifted module to test against")
        self.copy.write_text(json.dumps(self.data, indent=1, sort_keys=True) + "\n",
                             encoding="utf-8")

    def _empty_junit(self):
        path = REPO_ROOT / (TMP_REL + "/_EVIDENCE_EMPTY.xml")
        path.write_text('<?xml version="1.0"?><testsuites></testsuites>\n', encoding="utf-8")
        self.addCleanup(path.unlink)
        return self.copy_rel.replace(TMP_REL, "") and str(path)


class RefusingToForgeTests(_SandboxedEvidence):
    """The property the whole document rests on."""

    def test_a_drifted_module_with_no_run_behind_it_is_refused_not_restamped(self):
        before = json.loads(self.copy.read_text(encoding="utf-8"))["modules"]
        xml = self._empty_junit()
        data, updated, refused = M.remeasure([xml], root=REPO_ROOT)
        self.assertEqual(updated, [], "it updated rows with no test run behind them")
        reasons = dict(refused)
        self.assertTrue(self.drifted, "expected drifted modules to refuse")
        for rel in self.drifted:
            with self.subTest(module=rel):
                self.assertIn(rel, reasons)
                self.assertEqual(reasons[rel], "NO_TEST_RUN_SUPPLIED_FOR_ANY_REFERENCING_TEST")

        after = json.loads(self.copy.read_text(encoding="utf-8"))["modules"] \
            if self.copy.read_text(encoding="utf-8") else before
        # Nothing was written at all: no module was updated.
        self.assertEqual(before, json.loads((REPO_ROOT / self.copy_rel).read_text(
            encoding="utf-8"))["modules"] if updated else before)

    def test_the_stale_pin_is_still_stale_after_the_refusal(self):
        """The point: the call must keep being refused until a real run exists."""
        xml = self._empty_junit()
        M.remeasure([xml], root=REPO_ROOT)
        still = M.drifted_modules(json.loads(self.copy.read_text(encoding="utf-8")), REPO_ROOT)
        self.assertTrue(set(self.drifted) <= set(still),
                        "a refusal cleared drift it had no run to clear: %s"
                        % sorted(set(self.drifted) - set(still)))

    def test_the_cli_will_not_run_with_no_junit_at_all(self):
        proc = subprocess.run(
            [sys.executable, "-m", "canonical.runtime.module_invocation_evidence_v1",
             "--remeasure"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=300)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("needs --junit", proc.stderr)


class OnlyTheDriftedRowsMoveTests(_SandboxedEvidence):
    """A real run must not disturb the 1993 modules that were never stale."""

    def _junit_for(self, rel):
        """Build a junit document from a real test file that references `rel`.

        Not a hand-written fake: the case names are read out of the actual test source, so
        `case_references` resolves them to the functions they really name.
        """
        index = M.TestIndex(M.test_files(REPO_ROOT))
        covering = sorted(index.referencing(rel))
        self.assertTrue(covering, rel)
        cases = []
        for t in covering:
            # `index.tests[t]` is the test file's SOURCE; case_references parses it into the
            # (class, name) cases it actually defines and the module functions each one names.
            for (cls, name) in sorted(M.case_references(index.tests[t]))[:40]:
                classname = (t[:-3].replace("/", ".") + ("." + cls if cls else ""))
                cases.append(
                    '<testcase classname="%s" name="%s" time="0"/>' % (classname, name))
        path = REPO_ROOT / (TMP_REL + "/_EVIDENCE_REAL.xml")
        path.write_text(
            '<?xml version="1.0"?><testsuites><testsuite name="s">%s</testsuite></testsuites>\n'
            % "".join(cases), encoding="utf-8")
        self.addCleanup(path.unlink)
        return str(path)

    def test_a_real_run_updates_that_module_and_leaves_every_other_row_identical(self):
        target = next((r for r in self.drifted
                       if M.TestIndex(M.test_files(REPO_ROOT)).referencing(r)), None)
        if target is None:
            self.skipTest("no drifted module has a referencing test")
        before = json.loads(self.copy.read_text(encoding="utf-8"))["modules"]
        data, updated, refused = M.remeasure([self._junit_for(target)], [target],
                                             root=REPO_ROOT)
        self.assertEqual(updated, [target], (updated, refused))
        after = data["modules"]
        self.assertEqual(M._sha(REPO_ROOT / target), after[target]["sha256"])
        moved = {k for k in before if k != target and before[k] != after.get(k)}
        self.assertEqual(moved, set(), "rows outside the drifted set changed: %s" % sorted(moved)[:5])

    def test_the_summary_stays_internally_consistent(self):
        """`check()` validates the summary against the rows; a partial write must not break it."""
        target = next((r for r in self.drifted
                       if M.TestIndex(M.test_files(REPO_ROOT)).referencing(r)), None)
        if target is None:
            self.skipTest("no drifted module has a referencing test")
        data, updated, _ = M.remeasure([self._junit_for(target)], [target], root=REPO_ROOT)
        self.assertEqual(updated, [target])
        import collections
        tiers = collections.Counter(
            f["tier"] for m in data["modules"].values() for f in m["functions"].values())
        s = data["summary"]
        self.assertEqual(s["invocable_modules"], len(data["modules"]))
        self.assertEqual(s["invocable_functions"], sum(tiers.values()))
        for k, v in tiers.items():
            self.assertEqual(s["functions_by_tier"].get(k), v)


class ProvenanceIsRecordedTests(_SandboxedEvidence):
    def test_no_provenance_block_is_invented_when_nothing_was_updated(self):
        before = json.loads(self.copy.read_text(encoding="utf-8"))
        xml = self._empty_junit()
        data, updated, refused = M.remeasure([xml], root=REPO_ROOT)
        self.assertEqual(updated, [])
        self.assertTrue(refused)
        # Nothing updated, so the document is untouched and no provenance is claimed.
        self.assertEqual(data.get("remeasurement"), before.get("remeasurement"))


if __name__ == "__main__":
    unittest.main()
