"""Compound archive acceptance: the archive is re-opened, never believed.

This is acceptance code -- the thing that decides whether the machine actually
did what the sentence asked. So the refusals matter more than the acceptance:
every way this could be fooled has to be pinned as a refusal.
"""
import json
import pathlib
import shutil
import tarfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

import sys  # noqa: E402
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime.live_integrated_brain_v1 import run_raw_goal  # noqa: E402
from canonical.runtime.raw_goal_archive_compound_acceptance_v1 import (  # noqa: E402
    GRAMMAR,
    verify,
)

GOAL = ("Create a tar.gz archive from a manifest and verify the archive "
        "against that manifest.")
CREATE = "archive.tar_gz.create_from_manifest"
VERIFY_CAP = "archive.verify.tar_gz.gnu"


def _trace(manifest, archive, *, output_verified=True, verified=True):
    return [
        {"cycle": 0, "plan": {"args": {
            "capability_id": CREATE,
            "manifest_path": manifest,
            "output_path": archive,
        }}, "result": {"capability_id": CREATE, "output_verified": output_verified}},
        {"cycle": 1, "plan": {"args": {
            "capability_id": VERIFY_CAP,
            "manifest_path": manifest,
            "archive_path": archive,
        }}, "result": {"capability_id": VERIFY_CAP, "verified": verified}},
        {"cycle": 2, "plan": {"args": {}}, "result": {"type": "finish"}},
    ]


class CompoundArchiveAcceptanceTests(unittest.TestCase):
    """Drive the real machine, then attack the acceptance decision."""

    @classmethod
    def setUpClass(cls):
        # One real run for the whole class: acceptance is tested against what
        # the machine actually produced, not against a fixture I invented.
        cls.result = run_raw_goal({"task_id": "ACC01", "goal": GOAL})

    @classmethod
    def tearDownClass(cls):
        checkpoint = (cls.result.get("controller_checkpoint") or {}).get("path")
        if checkpoint:
            (REPO_ROOT / checkpoint).unlink(missing_ok=True)

    def setUp(self):
        r = self.result
        self.assertTrue(r.get("pass"), "the goal must execute before acceptance is testable")
        ce = r.get("controller_execution") or {}
        self.trace = ce.get("trace")
        rows = [x for x in self.trace if ((x.get("plan") or {}).get("args") or {}).get("capability_id")]
        self.manifest = rows[0]["plan"]["args"]["manifest_path"]
        self.archive = rows[0]["plan"]["args"]["output_path"]
        # Rebuild the contract exactly the way the front door does: routing
        # targets come from the COMPILED plan's parts, not from the trace. Get
        # this wrong and every negative control trips
        # RAW_TASK_CONTRACT_NOT_VERIFIED instead of the check under test.
        from canonical.runtime import goal_compiler as gc
        from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
        import json as _json
        registry = _json.loads(
            (REPO_ROOT / "canonical" / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json")
            .read_text(encoding="utf-8")
        )["capabilities"]
        compiled = gc.compile_goal(GOAL, registry, str(REPO_ROOT))
        targets = []
        for part in compiled.get("compiled_parts") or [compiled]:
            for eff in part.get("target_effects") or []:
                if isinstance(eff, str) and eff and eff not in targets:
                    targets.append(eff)
        self.contract = compile_contract(GOAL, source_id="user",
                                        routing_target_effects=targets)
        self.assertTrue(
            self.contract.get("pass") is True,
            f"the test needs a verified contract, got {self.contract.get('status')}",
        )

    def _contract_passes(self):
        return self.contract.get("pass") is True

    def test_the_goal_is_accepted_end_to_end(self):
        r = self.result
        self.assertTrue(r.get("semantic_acceptance_complete"),
                        f"not accepted: {json.dumps(r.get('raw_goal_acceptance'))[:200]}")
        acc = r.get("raw_goal_acceptance") or {}
        self.assertTrue(acc.get("independent_reinspection"))
        self.assertEqual(
            len(acc.get("accepted_obligation_ids") or []),
            r.get("raw_acceptance_obligation_count"),
            "every raw obligation must be discharged, not some of them",
        )
        self.assertEqual(
            r.get("status"),
            "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED",
        )

    def test_the_grammar_does_not_match_a_similar_sentence(self):
        """NEGATIVE CONTROL: acceptance is keyed to the exact sentence."""
        for other in (
            "Create a tar.gz archive from a manifest.",
            "Create a tar.gz archive from a manifest and verify the archive.",
            "Create a tar.gz archive from a manifest and verify the archive "
            "against a different manifest.",
            "Please create a tar.gz archive from a manifest and verify the "
            "archive against that manifest.",
        ):
            self.assertIsNone(GRAMMAR.fullmatch(other), other)
            out = verify(goal=other, execution=self.trace,
                         raw_contract=self.contract, root=REPO_ROOT)
            self.assertEqual(out.get("reason"), "NO_EXACT_AUTHENTICATED_GOAL_GRAMMAR")
            self.assertFalse(out.get("semantic_acceptance_complete"))

    def test_a_trace_without_the_verify_step_is_refused(self):
        """NEGATIVE CONTROL: half the sentence is not the sentence."""
        rows = [x for x in self.trace if ((x.get("plan") or {}).get("args") or {}).get("capability_id")]
        create_only = [rows[0]]
        out = verify(goal=GOAL, execution=create_only,
                     raw_contract=self.contract, root=REPO_ROOT)
        self.assertEqual(out.get("reason"), "TRACE_IS_NOT_CREATE_THEN_VERIFY")
        self.assertFalse(out.get("semantic_acceptance_complete"))

    def test_verify_against_a_different_manifest_is_refused(self):
        """NEGATIVE CONTROL: "against that manifest" is the whole point."""
        rows = [x for x in self.trace if ((x.get("plan") or {}).get("args") or {}).get("capability_id")]
        tampered = json.loads(json.dumps(rows))
        tampered[1]["plan"]["args"]["manifest_path"] = "canonical/some_other_manifest.json"
        out = verify(goal=GOAL, execution=tampered,
                     raw_contract=self.contract, root=REPO_ROOT)
        self.assertEqual(out.get("reason"), "VERIFY_USED_A_DIFFERENT_MANIFEST")

    def test_verify_of_a_different_archive_is_refused(self):
        rows = [x for x in self.trace if ((x.get("plan") or {}).get("args") or {}).get("capability_id")]
        tampered = json.loads(json.dumps(rows))
        tampered[1]["plan"]["args"]["archive_path"] = "canonical/elsewhere.tar.gz"
        out = verify(goal=GOAL, execution=tampered,
                     raw_contract=self.contract, root=REPO_ROOT)
        self.assertEqual(out.get("reason"), "VERIFY_USED_A_DIFFERENT_ARCHIVE")

    def test_a_create_step_that_was_not_output_verified_is_refused(self):
        rows = [x for x in self.trace if ((x.get("plan") or {}).get("args") or {}).get("capability_id")]
        tampered = json.loads(json.dumps(rows))
        tampered[0]["result"]["output_verified"] = False
        out = verify(goal=GOAL, execution=tampered,
                     raw_contract=self.contract, root=REPO_ROOT)
        self.assertEqual(out.get("reason"), "CREATE_STEP_NOT_OUTPUT_VERIFIED")

    def test_a_verify_step_that_did_not_verify_is_refused(self):
        rows = [x for x in self.trace if ((x.get("plan") or {}).get("args") or {}).get("capability_id")]
        tampered = json.loads(json.dumps(rows))
        tampered[1]["result"]["verified"] = False
        out = verify(goal=GOAL, execution=tampered,
                     raw_contract=self.contract, root=REPO_ROOT)
        self.assertEqual(out.get("reason"), "VERIFY_STEP_NOT_VERIFIED")

    def test_a_missing_archive_on_disk_is_refused(self):
        """NEGATIVE CONTROL: the plan can claim an archive that is not there.

        This is the check that makes the acceptance independent of the plan.
        Point the trace at a path that does not exist and acceptance must fail
        even though every step reported success.
        """
        rows = [x for x in self.trace if ((x.get("plan") or {}).get("args") or {}).get("capability_id")]
        ghost = json.loads(json.dumps(rows))
        ghost[0]["plan"]["args"]["output_path"] = "canonical/astra_runtime/tmp/does_not_exist.tar.gz"
        ghost[1]["plan"]["args"]["archive_path"] = "canonical/astra_runtime/tmp/does_not_exist.tar.gz"
        out = verify(goal=GOAL, execution=ghost,
                     raw_contract=self.contract, root=REPO_ROOT)
        self.assertEqual(out.get("reason"), "ARCHIVE_ABSENT_FROM_DISK")

    def test_an_archive_whose_member_is_not_in_the_repository_is_refused(self):
        """NEGATIVE CONTROL: a real tar.gz containing a fabricated member.

        The archive is re-opened and every member must exist inside the
        repository. A tar that merely opens is not evidence of anything.
        """
        tmp = REPO_ROOT / "canonical" / "astra_runtime" / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        forged = tmp / "_forged_member_archive.tar.gz"
        staged = tmp / "_forged_member_payload.txt"
        staged.write_text("payload\n", encoding="utf-8")
        try:
            with tarfile.open(forged, "w:gz") as handle:
                handle.add(staged, arcname="canonical/nowhere/at_all.txt")
            rows = [x for x in self.trace if ((x.get("plan") or {}).get("args") or {}).get("capability_id")]
            forged_trace = json.loads(json.dumps(rows))
            rel = forged.relative_to(REPO_ROOT).as_posix()
            forged_trace[0]["plan"]["args"]["output_path"] = rel
            forged_trace[1]["plan"]["args"]["archive_path"] = rel
            out = verify(goal=GOAL, execution=forged_trace,
                         raw_contract=self.contract, root=REPO_ROOT)
            self.assertEqual(out.get("reason"), "ARCHIVE_MEMBER_ABSENT_FROM_REPOSITORY")
        finally:
            forged.unlink(missing_ok=True)
            staged.unlink(missing_ok=True)

    def test_a_goal_hash_mismatch_is_refused(self):
        """NEGATIVE CONTROL: the obligations must belong to THIS sentence."""
        contract = json.loads(json.dumps(self.contract))
        contract["task_sha256"] = "0" * 64
        out = verify(goal=GOAL, execution=self.trace,
                     raw_contract=contract, root=REPO_ROOT)
        self.assertEqual(out.get("reason"), "RAW_GOAL_HASH_MISMATCH")

    def test_an_unverified_raw_contract_is_refused(self):
        contract = json.loads(json.dumps(self.contract))
        contract["pass"] = False
        out = verify(goal=GOAL, execution=self.trace,
                     raw_contract=contract, root=REPO_ROOT)
        self.assertEqual(out.get("reason"), "RAW_TASK_CONTRACT_NOT_VERIFIED")

    def test_empty_obligations_are_refused(self):
        """NEGATIVE CONTROL: accepting zero obligations is not acceptance."""
        contract = json.loads(json.dumps(self.contract))
        contract["acceptance_contract"]["obligations"] = []
        contract["acceptance_contract"]["required_obligation_ids"] = []
        out = verify(goal=GOAL, execution=self.trace,
                     raw_contract=contract, root=REPO_ROOT)
        self.assertEqual(out.get("reason"), "RAW_OBLIGATIONS_MISSING")

    def test_no_other_benchmark_goal_is_accepted_by_this_verifier(self):
        """NEGATIVE CONTROL on scope: the grammar is one sentence, not a family."""
        from canonical.runtime import goal_compilation_benchmark_v1 as bench
        others = [g["goal"] for g in list(bench.BENCHMARK_GOALS)
                  + list(bench.EXTENDED_BENCHMARK_GOALS) if g["goal"] != GOAL]
        self.assertTrue(others)
        for other in others:
            self.assertIsNone(GRAMMAR.fullmatch(other), other)


if __name__ == "__main__":
    unittest.main(verbosity=2)
