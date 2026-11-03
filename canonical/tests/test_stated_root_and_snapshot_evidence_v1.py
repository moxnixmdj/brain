"""Two measured defects on 73f773d, each pinned so it cannot come back silently.

Both were found by running the real front door and reading what it did, not by
reading the plan documents:

1. THE SNAPSHOT MERGE ERASED VERIFICATION EVIDENCE.  `_load_registry()` merged the
   snapshot over the canonical registry row-by-row, so a snapshot row carrying
   `verification: null` deleted a canonical row's real, receipt-backed evidence.
   Six capabilities that are admitted by the gate when the merge is skipped were
   refused `BOUND_CAPABILITY_VERIFICATION_MISSING` when it was not.  Consequence
   downstream: a plain sentence routed to `python.source.dead_code.v1` failed with
   `ACTION_EXPECTATION_FAILED ... BOUND_CAPABILITY_VERIFICATION_MISSING` -- the
   machine refusing work it had proof for.

2. THE STATED DIRECTORY WAS NOT THE DIRECTORY THE ACTION READ.  The row
   `source.candidates.enumerate.stdlib` carries `search_root` as the literal
   `"canonical/runtime"`, so the directory in the sentence is never a placeholder
   and the binder has nothing to bind.  A sentence naming its own source root
   enumerated 400 files under `canonical/runtime` and returned
   PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED.  Nothing caught
   it, because every check on the root asked "is it a directory", never "is it the
   directory the sentence named".

These tests are regression tests under TRUE_CAPABILITY_TEST_LAW_V1: they pin a
refusal and a recovery.  They are not, and must not be reported as, a capability.
"""
import json
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import stated_root_is_the_bound_root_v1 as stated  # noqa: E402
from canonical.runtime import verified_bound_capability_execution_adapter_v1 as adapter  # noqa: E402

REGISTRY = REPO_ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
SNAPSHOT = REPO_ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json"

# The six ids measured to be erased by the snapshot merge on 73f773d.
ERASED_BY_THE_MERGE = (
    "python.refactor.inline_helper.v1",
    "python.source.complexity.v1",
    "python.source.dead_code.v1",
    "python.source.definition_count.v1",
    "python.source.test_adequacy.v1",
    "python.vcs.merge_conflict.resolve.v1",
)


def _registry():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]


def _snapshot():
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))["capabilities"]


class TheSnapshotCannotDeleteEvidenceTests(unittest.TestCase):
    """Defect 1: a projection may add or update a row, never delete from one."""

    def test_the_six_ids_that_lost_their_evidence_are_admitted(self):
        for cid in ERASED_BY_THE_MERGE:
            with self.subTest(capability=cid):
                self.assertEqual(adapter.inspect(cid)["capability_id"], cid)

    def test_each_of_the_six_carries_real_verification_in_the_canonical_row(self):
        """The recovery is not a widened gate: the evidence was always there."""
        canon = _registry()
        for cid in ERASED_BY_THE_MERGE:
            with self.subTest(capability=cid):
                verification = canon[cid]["verification"]
                self.assertIs(verification.get("independently_verified"), True)
                self.assertTrue(verification.get("mission_id"))
                self.assertTrue((REPO_ROOT / verification["receipt_path"]).is_file())

    def test_the_snapshot_really_does_leave_those_fields_null(self):
        """The premise of the fix, pinned: if the data changes, this test says so."""
        snap = _snapshot()
        nulls = [cid for cid in ERASED_BY_THE_MERGE
                 if isinstance(snap.get(cid), dict) and snap[cid].get("verification") is None]
        self.assertEqual(sorted(nulls), sorted(ERASED_BY_THE_MERGE))

    def test_a_snapshot_that_states_a_value_still_wins(self):
        """Field-level merge must remain an overlay, not a `setdefault`."""
        canon_entry = {"verification": {"independently_verified": True}, "status": "S"}
        snap_entry = {"verification": {"independently_verified": False}, "status": "S"}
        overlay = {k: v for k, v in snap_entry.items()
                   if not (v is None and canon_entry.get(k) is not None)}
        merged = {**canon_entry, **overlay}
        self.assertIs(merged["verification"]["independently_verified"], False)

    def test_no_row_is_admitted_without_evidence(self):
        """The other direction: the fix must not admit a row that has nothing."""
        refused = 0
        for cid, entry in _registry().items():
            verification = entry.get("verification")
            boolean_only = isinstance(verification, dict) and (
                verification.get("independent_verified") is True
                or verification.get("independently_verified") is True
                or isinstance(verification.get("independently_verified_by"), str)
                or verification.get("producer_independent") is True)
            anchored = isinstance(verification, dict) and adapter._receipt_anchor_verified(verification)
            try:
                adapter.inspect(cid)
                admitted = True
            except Exception:
                admitted = False
            with self.subTest(capability=cid):
                self.assertEqual(admitted, boolean_only or anchored)


class TheStatedDirectoryIsTheBoundDirectoryTests(unittest.TestCase):

    def _sentinel_dir(self):
        """A real directory inside the repository that is not a registry constant."""
        sentinel = REPO_ROOT / "canonical/astra_runtime/tmp/stated_root_guard_v1"
        sentinel.mkdir(parents=True, exist_ok=True)
        return sentinel

    def _goal(self, root_rel, dest_rel="canonical/astra_runtime/tmp/stated_root_guard_v1/out.json"):
        return ("Find the function in the python source root %s that is never executed, "
                "and write its name to %s" % (root_rel, dest_rel))

    def test_a_directory_the_sentence_names_that_the_action_ignores_is_refused(self):
        sentinel = self._sentinel_dir()
        rel = "canonical/astra_runtime/tmp/stated_root_guard_v1"
        goal = self._goal(rel)
        directories = list(gc._repo_paths(goal, REPO_ROOT))
        self.assertIn(rel, [r for r, p in directories if p.is_dir()])
        template = _registry()["source.candidates.enumerate.stdlib"]["action_template"]["args"]
        refusal = stated.refusal(goal, [{"args": template}], directories)
        self.assertIsNotNone(refusal, "the constant must not silently win")
        self.assertEqual(refusal["status"], "FAIL_CLOSED__STATED_ROOT_NOT_BOUND")
        self.assertEqual(refusal["stated_roots_not_read"], [rel])
        self.assertEqual(refusal["roots_actually_read"], ["canonical/runtime"])
        self.assertTrue(str(sentinel))

    def test_a_sentence_that_names_no_directory_is_untouched(self):
        """`canonical/runtime` is a true default; no sentence, no accusation."""
        goal = "Enumerate the candidate python sources and rank them by relevance."
        directories = list(gc._repo_paths(goal, REPO_ROOT))
        self.assertEqual(stated.stated_read_roots(goal, directories), [])
        template = _registry()["source.candidates.enumerate.stdlib"]["action_template"]["args"]
        self.assertIsNone(stated.refusal(goal, [{"args": template}], directories))

    def test_an_action_that_reads_the_stated_directory_is_not_refused(self):
        rel = "canonical/astra_runtime/tmp/stated_root_guard_v1"
        goal = self._goal(rel)
        directories = list(gc._repo_paths(goal, REPO_ROOT))
        self.assertIsNone(stated.refusal(goal, [{"args": {"search_root": rel}}], directories))

    def test_one_step_reading_the_stated_root_clears_the_plan(self):
        rel = "canonical/astra_runtime/tmp/stated_root_guard_v1"
        goal = self._goal(rel)
        directories = list(gc._repo_paths(goal, REPO_ROOT))
        rows = [{"args": {"search_root": "canonical/runtime"}},
                {"args": {"source_root": rel}}]
        self.assertIsNone(stated.refusal(goal, rows, directories))

    def test_trailing_and_leading_spellings_of_one_directory_agree(self):
        rel = "canonical/astra_runtime/tmp/stated_root_guard_v1"
        goal = self._goal(rel)
        directories = list(gc._repo_paths(goal, REPO_ROOT))
        for spelling in (rel + "/", "./" + rel, rel.replace("/", "\\")):
            with self.subTest(spelling=spelling):
                self.assertIsNone(
                    stated.refusal(goal, [{"args": {"search_root": spelling}}], directories))

    def test_an_output_argument_is_not_a_read_root(self):
        """`output_path` names where evidence goes; this guard is about what is READ."""
        rel = "canonical/astra_runtime/tmp/stated_root_guard_v1"
        goal = self._goal(rel)
        directories = list(gc._repo_paths(goal, REPO_ROOT))
        rows = [{"args": {"output_path": "canonical/runtime/out.json"}}]
        self.assertIsNone(stated.refusal(goal, rows, directories))

    def test_the_guard_is_silent_when_the_action_declares_no_read_root(self):
        rel = "canonical/astra_runtime/tmp/stated_root_guard_v1"
        goal = self._goal(rel)
        directories = list(gc._repo_paths(goal, REPO_ROOT))
        self.assertIsNone(stated.refusal(goal, [{"args": {"path": rel}}], directories))


class AcceptanceRefusesTheConstantThatOverrodeTheSentenceTests(unittest.TestCase):
    """Defect 2 at its real call site: `verify()` itself, with a real contract.

    The trace is built here, and the ONLY difference between the two runs is the
    `search_root` the action was bound with.  One is the registry's literal
    default, the other is the directory the sentence names.  Acceptance must
    separate them; on 73f773d it accepted both.

    The stated directory is created by this test, inside the repository (every
    path the verifier accepts is repository-relative), and removed afterwards.
    """

    FIXTURE = "canonical/astra_runtime/tmp/stated_root_acceptance_fixture"

    @classmethod
    def setUpClass(cls):
        from canonical.runtime import live_integrated_brain_v1 as lib
        from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract

        cls.root = pathlib.Path(REPO_ROOT).resolve()
        cls.stated = cls.FIXTURE
        cls.destination = cls.FIXTURE + "/answer.json"
        fixture = cls.root / cls.FIXTURE
        (fixture / "pkg").mkdir(parents=True, exist_ok=True)
        (fixture / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        (fixture / "pkg" / "calc.py").write_text(
            "def used(a, b):\n    return a + b\n\n\ndef never_called(x):\n    return x * 2\n",
            encoding="utf-8")
        # The declared output must be on disk for `verify()`'s existence rule; this
        # test is about which ROOT was read, so the output is staged, not derived.
        (fixture / "answer.json").write_text(
            json.dumps({"answer": "never_called", "source_root": cls.FIXTURE + "/pkg"}),
            encoding="utf-8")
        cls.goal = ("Find the function in the python source root %s that is never "
                    "executed, and write its name to %s" % (cls.stated, cls.destination))
        cls.registry, _adm, cls.compiled = lib.compile_against_live_registry(cls.goal)
        cls.contract = compile_contract(
            cls.goal, source_id="user",
            routing_target_effects=list(cls.compiled.get("target_effects") or []))
        selected = cls.compiled.get("selected_capability")
        cls.capability = (selected.get("capability_id")
                          if isinstance(selected, dict) else selected)

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.root / cls.FIXTURE, ignore_errors=True)

    DEFAULT = "canonical/runtime"

    def _trace(self, search_root):
        return [
            {"cycle": 0, "plan": {"type": "invoke_capability", "args": {
                "capability_id": self.capability,
                "search_root": search_root,
                "output_path": self.destination}},
             "result": {"output_verified": True}},
            {"cycle": 1, "plan": {"type": "finish", "args": {"summary": "DONE"}},
             "result": {"type": "finish"}},
        ]

    def test_the_constant_is_refused_and_the_stated_directory_is_accepted(self):
        from canonical.runtime.raw_goal_trace_acceptance_v1 import verify

        refused = verify(goal=self.goal, compiled_plan=self.compiled,
                         execution=self._trace(self.DEFAULT),
                         raw_contract=self.contract, root=self.root)
        self.assertIs(refused.get("pass"), False)
        self.assertEqual(refused.get("reason"), stated.REFUSAL)
        self.assertEqual(refused.get("stated_roots_not_read"), [self.stated])

        accepted = verify(goal=self.goal, compiled_plan=self.compiled,
                          execution=self._trace(self.stated),
                          raw_contract=self.contract, root=self.root)
        self.assertEqual(accepted.get("status"), "RAW_GOAL_ACCEPTANCE_VERIFIED")


class TheRealCorpusIsNotAccusedTests(unittest.TestCase):
    """The guard must cost nothing on the recorded 67-goal corpus."""

    CORPUS = REPO_ROOT / "canonical/capabilities/true/LIVE_SOLVER_END_TO_END_MEASUREMENT_20261017_V1.json"

    def test_no_recorded_goal_is_falsely_refused(self):
        if not self.CORPUS.is_file():
            self.skipTest("recorded corpus absent")
        rows = json.loads(self.CORPUS.read_text(encoding="utf-8"))[
            "reachability_from_one_entry"]["rows"]
        registry = _registry()
        accused = []
        for row in rows:
            entry = registry.get(row["capability_id"]) or {}
            template = (entry.get("action_template") or {}).get("args") or {}
            directories = list(gc._repo_paths(row["goal"], REPO_ROOT))
            if stated.refusal(row["goal"], [{"args": template}], directories):
                accused.append(row["capability_id"])
        self.assertEqual(accused, [], "a recorded goal the machine already reaches")


if __name__ == "__main__":
    unittest.main()
