"""Generic trace acceptance: attacked, not asserted.

Acceptance decides whether the machine really did what the sentence asked, so
the refusals matter more than the acceptance. Every test here either drives the
real machine or takes a real trace and breaks exactly one thing about it, then
requires the specific refusal that break deserves. A verifier that could be
convinced by a claim instead of by bytes would pass most of these -- which is
the point of writing them.
"""
import copy
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

import sys  # noqa: E402
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import (  # noqa: E402
    load_verified_registry,
    run_raw_goal,
)
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract  # noqa: E402
from canonical.runtime.raw_goal_trace_acceptance_v1 import (  # noqa: E402
    INSPECTORS,
    _action_rows,
    _plan_chain,
    verify,
)

TAR_GOAL = "Verify a tar.gz archive against its manifest."
RANK_BIND_GOAL = "Extract evidence from a source, then rank it, then bind it to a claim."
CLAIM_BIND_GOAL = "Bind evidence claims to an explicit comparison."
TAR_CAPABILITY = "archive.verify.tar_gz.gnu"


def _contract(goal):
    """Rebuild the obligation envelope exactly the way the front door does."""
    registry = dict(load_verified_registry())
    compiled = gc.compile_goal(goal, registry, str(REPO_ROOT))
    targets = list(compiled.get("target_effects") or [])
    if not targets:
        for part in compiled.get("compiled_parts") or []:
            for effect in (part or {}).get("target_effects") or []:
                if isinstance(effect, str) and effect and effect not in targets:
                    targets.append(effect)
    return compiled, compile_contract(
        goal, source_id="user", routing_target_effects=targets)


class GenericTraceAcceptanceTests(unittest.TestCase):
    """Drive the real machine, then attack the acceptance decision."""

    @classmethod
    def setUpClass(cls):
        # Real runs. Acceptance is tested against what the machine actually
        # produced on disk, never against a fixture invented here.
        cls.tar = run_raw_goal({"task_id": "GTA_TAR", "goal": TAR_GOAL})
        cls.rank_bind = run_raw_goal(
            {"task_id": "GTA_RANK", "goal": RANK_BIND_GOAL})
        cls.claim_bind = run_raw_goal(
            {"task_id": "GTA_CLAIM", "goal": CLAIM_BIND_GOAL})
        cls.compiled, cls.contract = _contract(TAR_GOAL)

    @classmethod
    def tearDownClass(cls):
        for result in (cls.tar, cls.rank_bind, cls.claim_bind):
            checkpoint = (result.get("controller_checkpoint") or {}).get("path")
            if checkpoint:
                (REPO_ROOT / checkpoint).unlink(missing_ok=True)

    # -- helpers ---------------------------------------------------------
    def trace(self, result=None):
        source = result if result is not None else self.tar
        trace = (source.get("controller_execution") or {}).get("trace")
        self.assertIsInstance(trace, list)
        return copy.deepcopy(trace)

    def check(self, **overrides):
        kwargs = {
            "goal": TAR_GOAL,
            "compiled_plan": self.compiled,
            "execution": self.trace(),
            "raw_contract": self.contract,
            "root": REPO_ROOT,
        }
        kwargs.update(overrides)
        return verify(**kwargs)

    def setUp(self):
        # A negative control that trips the wrong check looks green. The
        # envelope has to be valid before any of these refusals mean anything.
        self.assertIs(self.contract.get("pass"), True, self.contract.get("errors"))
        self.assertIs(self.tar.get("pass"), True, self.tar.get("reason"))

    # -- the positive case ----------------------------------------------
    def test_a_real_run_is_accepted_and_every_step_is_reinspected(self):
        result = self.check()
        self.assertIs(result["semantic_acceptance_complete"], True, result)
        self.assertIs(result["independent_reinspection"], True)
        rows = _action_rows(self.trace())
        self.assertEqual(result["reinspected_step_count"], len(rows))
        self.assertEqual(
            [row["capability_id"] for row in result["reinspection_ledger"]],
            [row["args"]["capability_id"] for row in rows],
        )
        self.assertEqual(
            len(result["accepted_obligation_ids"]),
            self.tar["raw_acceptance_obligation_count"],
        )

    def test_the_front_door_reports_the_same_acceptance(self):
        self.assertIs(self.tar["semantic_acceptance_complete"], True, self.tar)
        self.assertEqual(
            len(self.tar["accepted_raw_obligation_ids"]),
            self.tar["raw_acceptance_obligation_count"],
        )
        self.assertIn("ACCEPTANCE_VERIFIED", self.tar["status"])

    def test_the_accepted_archive_is_still_on_disk_with_those_members(self):
        rows = _action_rows(self.trace())
        archive = REPO_ROOT / rows[0]["args"]["archive_path"]
        self.assertTrue(archive.is_file(), archive)
        import tarfile
        with tarfile.open(archive, "r:gz") as handle:
            members = sorted(handle.getnames())
        self.assertEqual(members, sorted(rows[0]["result"]["members"]))
        self.assertTrue(members)

    def test_a_capability_with_no_inspector_is_registered_nowhere(self):
        # The refusal is only meaningful if the inspector table is real.
        self.assertIn(TAR_CAPABILITY, INSPECTORS)
        self.assertNotIn("this.capability.does.not.exist", INSPECTORS)

    # -- the sentence and the plan --------------------------------------
    def test_a_different_sentence_is_refused(self):
        result = self.check(goal="Verify a tar.gz archive against its manifest!")
        self.assertEqual(result["reason"], "RAW_GOAL_HASH_MISMATCH")

    def test_an_unverified_contract_is_refused(self):
        broken = copy.deepcopy(self.contract)
        broken["pass"] = False
        result = self.check(raw_contract=broken)
        self.assertEqual(result["reason"], "RAW_TASK_CONTRACT_NOT_VERIFIED")

    def test_a_contract_with_no_obligations_is_refused(self):
        broken = copy.deepcopy(self.contract)
        broken["acceptance_contract"]["obligations"] = []
        result = self.check(raw_contract=broken)
        self.assertEqual(result["reason"], "RAW_OBLIGATIONS_MISSING")

    def test_a_plan_capability_missing_from_the_trace_is_refused(self):
        # The plan asked for create-then-verify; the trace only verified. The
        # capability that never ran is the one that must be named.
        plan = {"compiled_parts": [
            {"mode": "VERIFIED_CAPABILITY",
             "selected_capability": "archive.tar_gz.create_from_manifest"},
            {"mode": "VERIFIED_CAPABILITY", "selected_capability": TAR_CAPABILITY},
        ]}
        result = self.check(compiled_plan=plan)
        self.assertEqual(result["reason"], "PLAN_CAPABILITY_ABSENT_FROM_TRACE")
        self.assertEqual(
            result["missing_capabilities"], ["archive.tar_gz.create_from_manifest"])

    def test_a_trace_that_ends_on_the_wrong_capability_is_refused(self):
        # Both planned capabilities ran, but in the wrong order, so the plan's
        # last capability is not what the machine finished on. The ordering
        # check runs before any artifact is opened, so no files are needed.
        enumerate_cid = "source.candidates.enumerate.stdlib"
        rank_cid = "source.objective_relevance.rank.bm25"
        trace = [
            {"cycle": 0, "plan": {"args": {"capability_id": rank_cid}},
             "result": {"capability_id": rank_cid}},
            {"cycle": 1, "plan": {"args": {"capability_id": enumerate_cid}},
             "result": {"capability_id": enumerate_cid}},
            {"cycle": 2, "plan": {"args": {}}, "result": {"type": "finish"}},
        ]
        plan = {"compiled_parts": [
            {"mode": "VERIFIED_CAPABILITY", "selected_capability": enumerate_cid},
            {"mode": "VERIFIED_CAPABILITY", "selected_capability": rank_cid},
        ]}
        result = self.check(compiled_plan=plan, execution=trace)
        self.assertEqual(
            result["reason"], "TRACE_DOES_NOT_END_WITH_THE_PLANS_LAST_CAPABILITY")
        self.assertEqual(result["last_executed"], enumerate_cid)
        self.assertEqual(result["planned_last"], rank_cid)

    def test_a_trace_without_a_finish_row_is_refused(self):
        trace = self.trace()
        trace = [row for row in trace
                 if (row.get("result") or {}).get("type") != "finish"]
        result = self.check(execution=trace)
        self.assertEqual(result["reason"], "TRACE_DID_NOT_REACH_FINISH")

    def test_a_trace_with_no_capability_actions_is_refused(self):
        trace = [row for row in self.trace()
                 if not ((row.get("plan") or {}).get("args") or {}).get("capability_id")]
        self.assertEqual(trace[-1]["result"]["type"], "finish")
        result = self.check(execution=trace)
        self.assertEqual(result["reason"], "TRACE_HAS_NO_CAPABILITY_ACTIONS")

    def test_a_step_the_sentence_never_asked_for_is_refused(self):
        trace = self.trace()
        trace.insert(0, {"cycle": 0, "plan": {"args": {
            "capability_id": "totally.unrelated.capability",
            "output_path": "canonical/CANONICAL_POINTER.json",
        }}, "result": {"capability_id": "totally.unrelated.capability"}})
        result = self.check(execution=trace)
        self.assertEqual(result["reason"], "UNCONSUMED_STEP_THE_SENTENCE_DID_NOT_ASK_FOR")
        self.assertEqual(result["capability_id"], "totally.unrelated.capability")

    def test_a_capability_with_no_reinspector_can_never_be_accepted(self):
        unknown = "a.capability.nobody.can.reinspect"
        trace = self.trace()
        trace[0]["plan"]["args"]["capability_id"] = unknown
        trace[0]["result"]["capability_id"] = unknown
        result = self.check(
            compiled_plan={"selected_capability": unknown}, execution=trace)
        self.assertEqual(result["reason"], "NO_INDEPENDENT_REINSPECTION_FOR:" + unknown)

    # -- the bytes -------------------------------------------------------
    def test_a_missing_artifact_is_refused(self):
        trace = self.trace()
        trace[0]["plan"]["args"]["archive_path"] = (
            "canonical/astra_runtime/tmp/does-not-exist.tar.gz")
        result = self.check(execution=trace)
        self.assertEqual(result["reason"], "STEP_PATH_ABSENT_FROM_DISK")
        self.assertEqual(result["argument"], "archive_path")

    def test_a_path_outside_the_repository_is_refused(self):
        trace = self.trace()
        trace[0]["plan"]["args"]["archive_path"] = "/etc/passwd"
        result = self.check(execution=trace)
        self.assertEqual(result["reason"], "STEP_PATH_OUTSIDE_REPOSITORY")

    def test_a_claimed_digest_that_does_not_match_the_file_is_refused(self):
        trace = self.trace()
        trace[0]["result"]["output_sha256"] = "0" * 64
        trace[0]["result"]["output_path"] = trace[0]["plan"]["args"]["archive_path"]
        result = self.check(execution=trace)
        self.assertEqual(result["reason"], "DECLARED_OUTPUT_SHA256_MISMATCH")

    def test_a_producer_that_admitted_failure_is_refused(self):
        trace = self.trace()
        trace[0]["result"]["verified"] = False
        result = self.check(execution=trace)
        self.assertEqual(result["reason"], "STEP_NOT_VERIFIED_BY_ITS_PRODUCER")

    def test_a_tampered_member_list_is_refused(self):
        trace = self.trace()
        trace[0]["result"]["members"] = ["canonical/README.md"]
        result = self.check(execution=trace)
        self.assertEqual(result["reason"], "ARCHIVE_MEMBERS_MISMATCH")

    def test_a_tampered_member_count_is_refused(self):
        trace = self.trace()
        trace[0]["result"]["member_count"] = 99
        result = self.check(execution=trace)
        self.assertEqual(result["reason"], "ARCHIVE_MEMBER_COUNT_MISMATCH")

    # -- the real machine refusing honestly ------------------------------
    def test_a_goal_whose_own_producer_said_unverified_is_not_accepted(self):
        for result, name in ((self.rank_bind, RANK_BIND_GOAL),
                             (self.claim_bind, CLAIM_BIND_GOAL)):
            with self.subTest(goal=name):
                self.assertIs(result["pass"], True, result.get("reason"))
                self.assertIs(result["semantic_acceptance_complete"], False, result)
                compiled, contract = _contract(name)
                acceptance = verify(
                    goal=name,
                    compiled_plan=compiled,
                    execution=(result.get("controller_execution") or {}).get("trace"),
                    raw_contract=contract,
                    root=REPO_ROOT,
                )
                self.assertEqual(
                    acceptance["reason"], "STEP_OUTPUT_NOT_VERIFIED_BY_ITS_PRODUCER")
                self.assertEqual(
                    acceptance["capability_id"],
                    "source.evidence.extract.objective_grounded.stdlib",
                )
                self.assertEqual(acceptance["accepted_obligation_ids"], [])

    def test_no_benchmark_goal_outside_the_inspected_set_is_silently_accepted(self):
        # Acceptance must never be granted to a capability nobody can inspect.
        for capability in ("image.qr.generate.qrencode",
                           "image.extract.ocr.tesseract",
                           "document.convert.markdown_pdf.pandoc_weasyprint"):
            self.assertNotIn(capability, INSPECTORS)

    def test_the_plan_chain_helper_ignores_absorbed_clauses(self):
        plan = {"compiled_parts": [
            {"mode": "VERIFIED_CAPABILITY", "selected_capability": "a.one"},
            {"mode": "SUBGOAL_ABSORBED_BY_COMPILED_PREFIX",
             "selected_capability": "a.one"},
            {"mode": "VERIFIED_CAPABILITY", "selected_capability": "b.two"},
        ]}
        self.assertEqual(_plan_chain(plan), ["a.one", "b.two"])
        self.assertEqual(_plan_chain({"selected_capability": "c.three"}), ["c.three"])
        self.assertEqual(_plan_chain(None), [])


if __name__ == "__main__":
    unittest.main()
