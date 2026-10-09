from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import finance_candidate_policy_terminal_signatures_v1 as producer
from canonical.runtime import finance_candidate_policy_terminal_signatures_verify_v1 as verifier
from canonical.runtime import r2_finance_candidate_policy_terminal_signatures_direct_adequacy_v1 as route
from canonical.runtime import finance_normalized_unless_branch_v1 as unless_policy
from canonical.runtime import finance_normalized_if_branch_v1 as if_policy


def unless_case(bindings):
    source_id = "test-unless-source"
    source_text = "Use ordinary treatment unless exception applies."
    base = unless_policy.compute({
        "schema": unless_policy.INPUT_SCHEMA,
        "source_id": source_id,
        "source_text": source_text,
        "exception_applies": False,
    })
    return {
        "schema": producer.INPUT_SCHEMA,
        "domain": "FINANCE",
        "scope_id": base["scope_id"],
        "source_id": source_id,
        "source_text": source_text,
        "policy_family": producer.POLICY_UNLESS,
        "candidate_fact_bindings": bindings,
    }


def if_case(bindings):
    source_id = "test-if-source"
    source_text = "If capital falls, apply restriction."
    base = if_policy.compute({
        "schema": if_policy.INPUT_SCHEMA,
        "source_id": source_id,
        "source_text": source_text,
        "antecedent_holds": False,
    })
    return {
        "schema": producer.INPUT_SCHEMA,
        "domain": "FINANCE",
        "scope_id": base["scope_id"],
        "source_id": source_id,
        "source_text": source_text,
        "policy_family": producer.POLICY_IF,
        "candidate_fact_bindings": bindings,
    }


class CandidatePolicyTerminalSignatureTests(unittest.TestCase):
    def test_unless_same_fact_collapses_to_one_terminal_class(self):
        case = unless_case({"a": False, "b": False})
        out = producer.compute(case)
        checked = verifier.verify(case, out)
        self.assertTrue(checked["verified"], checked)
        self.assertTrue(out["all_candidates_terminally_equivalent"])
        self.assertEqual(out["terminal_equivalence_class_count"], 1)
        self.assertEqual(set(out["terminal_signatures"]), {"a", "b"})
        self.assertTrue(all(
            row["terminal_signature_complete"] is True
            for row in out["terminal_signatures"].values()
        ))
        self.assertFalse(out["declared_candidate_set_semantic_completeness_claimed"])
        self.assertFalse(out["candidate_fact_truth_inferred"])

    def test_unless_distinct_facts_produce_two_terminal_classes(self):
        case = unless_case({"ordinary": False, "exception": True})
        out = producer.compute(case)
        checked = verifier.verify(case, out)
        self.assertTrue(checked["verified"], checked)
        self.assertFalse(out["all_candidates_terminally_equivalent"])
        self.assertEqual(out["terminal_equivalence_class_count"], 2)
        branches = {
            row["terminal_signature"]["selected_branch"]
            for row in out["terminal_signatures"].values()
        }
        self.assertEqual(branches, {"ORDINARY_BRANCH", "EXCEPTION_BRANCH"})

    def test_if_distinct_facts_produce_two_terminal_classes(self):
        case = if_case({"not_met": False, "met": True})
        out = producer.compute(case)
        checked = verifier.verify(case, out)
        self.assertTrue(checked["verified"], checked)
        self.assertFalse(out["all_candidates_terminally_equivalent"])
        self.assertEqual(out["terminal_equivalence_class_count"], 2)
        branches = {
            row["terminal_signature"]["selected_branch"]
            for row in out["terminal_signatures"].values()
        }
        self.assertEqual(branches, {"CONDITION_NOT_MET", "CONSEQUENT_BRANCH"})

    def test_verifier_rejects_tampered_terminal_signature(self):
        case = unless_case({"a": False, "b": True})
        out = producer.compute(case)
        tampered = deepcopy(out)
        tampered["terminal_signatures"]["a"]["terminal_signature"]["selected_branch"] = "FORGED"
        checked = verifier.verify(case, tampered)
        self.assertFalse(checked["verified"])
        self.assertIn("TERMINAL_SIGNATURE_MISMATCH", checked["reason"])

    def test_non_boolean_candidate_fact_fails_closed(self):
        case = unless_case({"a": False})
        case["candidate_fact_bindings"]["b"] = "false"
        out = producer.run(case)
        self.assertFalse(out["pass"])
        self.assertIn("CANDIDATE_FACT_BOOLEAN_REQUIRED", out["reason"])

    def test_scope_mismatch_fails_closed(self):
        case = unless_case({"a": False})
        case["scope_id"] = "SCOPE-forged"
        out = producer.run(case)
        self.assertFalse(out["pass"])
        self.assertIn("SCOPE_ID_MISMATCH", out["reason"])

    def test_direct_route_executes_and_independently_verifies(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "canonical/evidence/candidate_policy_case.json"
            outp = root / "canonical/verification/candidate_policy_result.json"
            inp.parent.mkdir(parents=True, exist_ok=True)
            inp.write_text(json.dumps(unless_case({"a": False, "b": True})), encoding="utf-8")
            goal = (
                "Using the bounded finance candidate policy worldset at "
                "canonical/evidence/candidate_policy_case.json, derive and independently "
                "verify complete candidate terminal signatures and save them to "
                "canonical/verification/candidate_policy_result.json."
            )
            request = {"task_id": "candidate-terminal-signatures", "goal": goal}
            pf = route.preflight(request, repo_root=root)
            self.assertTrue(pf["matched"], pf)
            self.assertEqual(pf["status"], "DIRECT_ADEQUACY_ROUTE_MATCHED")
            self.assertFalse(outp.exists(), "preflight must be effect-free")
            result = route.run(request, repo_root=root)
            self.assertTrue(result["pass"], result)
            self.assertTrue(result["direct_adequacy_authority"])
            self.assertTrue(result["actual_goal_satisfaction_verified"])
            self.assertFalse(result["terminal_authority"])
            self.assertEqual(result["terminal_credit_delta"], 0)
            saved = json.loads(outp.read_text(encoding="utf-8"))
            self.assertTrue(verifier.verify(unless_case({"a": False, "b": True}), saved)["verified"])

    def test_matching_invalid_case_fails_closed_not_not_applicable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "canonical/evidence/candidate_policy_case.json"
            inp.parent.mkdir(parents=True, exist_ok=True)
            bad = unless_case({"a": False})
            bad["candidate_fact_bindings"]["b"] = "not-a-bool"
            inp.write_text(json.dumps(bad), encoding="utf-8")
            goal = (
                "Using the bounded finance candidate policy worldset at "
                "canonical/evidence/candidate_policy_case.json, derive and independently "
                "verify complete candidate terminal signatures and save them to "
                "canonical/verification/candidate_policy_result.json."
            )
            out = route.preflight({"task_id": "x", "goal": goal}, repo_root=root)
            self.assertTrue(out["matched"], out)
            self.assertEqual(out["status"], "FAIL_CLOSED")
            self.assertIn("CANDIDATE_FACT_BOOLEAN_REQUIRED", out["reason"])

    def test_route_nonmatching_goal_is_not_applicable(self):
        out = route.preflight({"task_id": "x", "goal": "do something else"}, repo_root=".")
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"], "NOT_APPLICABLE")


if __name__ == "__main__":
    unittest.main()
