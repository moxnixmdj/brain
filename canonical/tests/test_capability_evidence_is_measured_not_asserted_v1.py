# PROJECT_BRAIN
"""Pins for execution_guard/capability_evidence_probe_v1.py — evidence, not status.

The registry test `test_no_registry_entry_is_left_without_proof` demands a verification block on
every entry. A block that says "VERIFIED" without saying what was verified is the same assertion
it was meant to replace, so these pins hold the probe to the four things that make its receipts
evidence rather than paperwork:

* the fixture really contains the defects the oracle claims to plant;
* a verb that executes but does NOT find its planted defect is reported as MISSED (the probe is
  allowed to find a capability guilty, and is not allowed to find everything innocent);
* two observations start from byte-identical worlds, so "reproduced" means the work reproduced
  and not that the first run left its answer behind;
* the volatile-projection drops what belongs to the run (paths, clocks, transcripts, commit ids)
  and keeps what belongs to the work.

Run: python -m pytest canonical/tests/test_capability_evidence_is_measured_not_asserted_v1.py -q
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from execution_guard import capability_evidence_probe_v1 as probe  # noqa: E402


class FixtureTests(unittest.TestCase):

    def test_the_fixture_really_contains_what_the_oracle_claims(self):
        import tempfile
        work = Path(tempfile.mkdtemp(prefix="evidence_pin_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(work, True))
        source = probe.build_source_fixture(work)
        leak = (source / "pkg" / "io_leak.py").read_text(encoding="utf-8")
        self.assertIn("handle = open(path)", leak)          # an unclosed handle
        self.assertEqual(leak.count("def duplicate_"), 2)   # a duplicated block
        self.assertGreaterEqual(leak.count("elif kind =="), 10)  # above C901's threshold of 10
        self.assertIn("divide(1, 0)", (source / "tests" / "test_calc.py").read_text())
        repo, good, upstream = probe.build_git_fixture(work)
        subjects = __import__("subprocess").run(
            ["git", "log", "--format=%s", "--all"], cwd=str(repo), capture_output=True,
            text=True).stdout.split()
        self.assertIn("bad", subjects)
        self.assertIn("good", subjects)

    def test_an_executed_verb_that_misses_its_defect_is_a_miss_not_a_pass(self):
        # the oracle is a predicate over the capability's RESULT, not over its exit
        label, predicate = probe.ORACLE["python.quality.resource_leak.v1"]
        self.assertTrue(predicate({"gate": "PASS", "leaks_found": 1}))
        self.assertFalse(predicate({"gate": "PASS", "leaks_found": 0}))
        # ...and a result the predicate cannot read is a miss, never a pass
        self.assertFalse(predicate({}))


class ProjectionTests(unittest.TestCase):
    """What belongs to the run must not decide whether the work reproduced."""

    def test_paths_clocks_transcripts_and_commit_ids_are_dropped(self):
        first = {"gate": "PASS", "target": "/tmp/a", "artifact_path": "/tmp/a/out.json",
                 "artifact_sha256": "x", "elapsed_ms": 12, "test_output_tail": ["1 failed in 0.42s"],
                 "sha": "aaa", "leaks_found": 1}
        second = {"gate": "PASS", "target": "/tmp/b", "artifact_path": "/tmp/b/out.json",
                  "artifact_sha256": "y", "elapsed_ms": 99, "test_output_tail": ["1 failed in 0.51s"],
                  "sha": "bbb", "leaks_found": 1}
        self.assertEqual(probe._findings_sha(first), probe._findings_sha(second))

    def test_a_different_finding_still_changes_the_projection(self):
        first = {"gate": "PASS", "leaks_found": 1}
        second = {"gate": "PASS", "leaks_found": 2}
        self.assertNotEqual(probe._findings_sha(first), probe._findings_sha(second))


class ReceiptTests(unittest.TestCase):
    """Every receipt in the repository is one this probe could have written."""

    def test_every_receipt_names_its_probe_reproduction_and_defect(self):
        receipts = sorted((ROOT / "canonical/astra_runtime/evidence").glob(
            "CAPABILITY__*__RECEIPT.json"))
        self.assertGreaterEqual(len(receipts), 16)
        for path in receipts:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema"], "PROJECT_BRAIN_CAPABILITY_EXECUTION_RECEIPT_V1")
            self.assertEqual(receipt["probe_input"][:5], "task-", path.name)
            self.assertTrue(receipt["reproduced_on_second_run"], path.name)
            self.assertIsNone(receipt["independent_verifier"], path.name)
            self.assertFalse(receipt["producer_independent"], path.name)
            self.assertEqual(receipt["model_dependency_count"], 0, path.name)

    # A POINTER THAT NAMES A FILE NOBODY WROTE is the same assertion as a status string wearing
    # a filename.  Measured on this branch: 33 such pointers over 19 capabilities, and the 22
    # belonging to the git surface and to move_function are repaired (their probes now write what
    # the registry says they write).  What is left is pinned BY NAME below: a NEW dangling
    # pointer fails this test, and paying off one of these requires deleting its line.
    KNOWN_DANGLING = {
        "code.multilanguage.parse.tree_sitter.v1",
        "software.hardcore.closing.supercomposer.v1",
        "software.hardcore.kernel.orchestrate.v1",
        "software.repair.choreograph.crossfile.v1",
        "software.repair.loop.cegis_hypothesis.v1",
        "software.review.gate.composer.v1",
        "software.synthesis.grid_induction.v1",
        "test.slice.never_miss.v1",
    }

    def test_every_registry_entry_that_claims_verification_carries_the_receipt(self):
        registry = json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
                              .read_text(encoding="utf-8"))["capabilities"]
        dangling = set()
        for cid, entry in registry.items():
            verification = entry.get("verification")
            self.assertIsInstance(verification, dict, cid)
            self.assertTrue(verification, cid)
            for key in ("receipt_path", "state_path"):
                pointer = verification.get(key)
                if not pointer or not (ROOT / pointer).is_file():
                    if pointer:
                        dangling.add(cid)
                    continue
                receipt = json.loads((ROOT / pointer).read_text(encoding="utf-8"))
                if (receipt.get("schema") == "PROJECT_BRAIN_CAPABILITY_EXECUTION_RECEIPT_V1"
                        and verification.get("module_sha256")):
                    # only the receipts this probe wrote carry a module digest to compare; the
                    # older ASTRA mission receipts attest a mission, not a module
                    self.assertEqual(receipt["module_sha256"], verification["module_sha256"], cid)
        self.assertEqual(dangling, self.KNOWN_DANGLING,
                         "a verification pointer names a file that is not on disk")


if __name__ == "__main__":
    unittest.main()
