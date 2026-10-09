from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from canonical.runtime import r2_finance_defined_term_raw_fact_unless_direct_adequacy_v1 as direct
from canonical.tests.test_finance_defined_term_raw_fact_unless_v1 import case, coverage


def goal(
    inp="canonical/tmp/finance_defined_term_case.json",
    out="canonical/tmp/finance_defined_term_result.json",
):
    return (
        "Using the source-defined raw-fact finance UNLESS case at "
        f"{inp}, select and independently verify the applicable branch "
        f"and save it to {out}."
    )


class R2FinanceDefinedTermRawFactUnlessDirectTests(unittest.TestCase):
    def test_preflight_is_side_effect_free(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "canonical/tmp/finance_defined_term_case.json"
            inp.parent.mkdir(parents=True, exist_ok=True)
            inp.write_text(json.dumps(case()), encoding="utf-8")
            request = {"task_id": "fd1", "goal": goal()}
            pf = direct.preflight(request, repo_root=root)
            self.assertTrue(pf["matched"], pf)
            self.assertEqual(pf["route_id"], direct.ROUTE_ID)
            self.assertEqual(pf["selected_branch"], "EXCEPTION_BRANCH")
            self.assertFalse(
                (root / "canonical/tmp/finance_defined_term_result.json").exists()
            )

    def test_transactional_run_commits_verified_result(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "canonical/tmp/finance_defined_term_case.json"
            inp.parent.mkdir(parents=True, exist_ok=True)
            inp.write_text(json.dumps(case("100.00")), encoding="utf-8")
            request = {"task_id": "fd2", "goal": goal()}
            out = direct.run(request, repo_root=root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["selected_branch"], "ORDINARY_BRANCH")
            self.assertTrue(out["semantic_acceptance_complete"])
            self.assertTrue(out["actual_goal_satisfaction_verified"])
            self.assertTrue(out["input_immutability_verified"])
            self.assertTrue(out["acceptance_receipt"]["producer_independent"])

    def test_matched_semantic_failure_fails_closed_without_fallback(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "canonical/tmp/finance_defined_term_case.json"
            inp.parent.mkdir(parents=True, exist_ok=True)
            policy = (
                "Total exposure means exposure_amount.\n"
                "Apply Rule A unless Aggregate exposure is at least 125.50.\n"
            )
            c = case()
            c["policy_source_text"] = policy
            c.update(coverage(policy))
            inp.write_text(json.dumps(c), encoding="utf-8")
            out = direct.preflight(
                {"task_id": "fd3", "goal": goal()},
                repo_root=root,
            )
            self.assertTrue(out["matched"])
            self.assertFalse(out["pass"])
            self.assertEqual(out["status"], "FAIL_CLOSED")
            self.assertIn("DEFINED_TERM_RAW_FACT_CONDITION_NOT_PROVED", out["reason"])

    def test_verifier_failure_rolls_back_existing_output(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "canonical/tmp/finance_defined_term_case.json"
            outp = root / "canonical/tmp/finance_defined_term_result.json"
            inp.parent.mkdir(parents=True, exist_ok=True)
            inp.write_text(json.dumps(case()), encoding="utf-8")
            outp.write_text('{"old":true}\n', encoding="utf-8")
            original = outp.read_bytes()
            request = {"task_id": "fd4", "goal": goal()}
            real_verify = direct.verifier.verify
            calls = {"n": 0}

            def fail_after_preflight(case_row, result_row):
                calls["n"] += 1
                if calls["n"] == 1:
                    return real_verify(case_row, result_row)
                return {
                    "verified": False,
                    "producer_independent": True,
                    "producer_module_imported": False,
                    "defined_term_evaluator_imported": False,
                    "raw_context_compiler_imported": False,
                    "scope_parser_imported": False,
                    "model_dependency_count": 0,
                    "errors": ["forced"],
                }

            with patch.object(direct.verifier, "verify", side_effect=fail_after_preflight):
                out = direct.run(request, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertTrue(out["transaction_rolled_back"])
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(outp.read_bytes(), original)

    def test_nonmatching_goal_does_not_claim_scope(self):
        with TemporaryDirectory() as td:
            out = direct.preflight(
                {"task_id": "fd5", "goal": "Analyze this finance policy."},
                repo_root=Path(td),
            )
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"], "NOT_APPLICABLE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
