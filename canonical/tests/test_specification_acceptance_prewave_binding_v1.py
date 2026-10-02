from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def git_blob(path):
    return subprocess.check_output(["git","hash-object",str(ROOT/path)],text=True).strip()

class SpecificationAcceptancePrewaveBindingTests(unittest.TestCase):
    def setUp(self):
        self.b=load(Path("canonical/governance/SPECIFICATION_ACCEPTANCE_PREWAVE_BINDING_V1.json"))

    def test_registry_contract_is_active(self):
        reg=load(Path("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"))
        ids={x["behavior_id"] for x in reg["active_contracted_residuals"]}
        self.assertIn("SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",ids)
        self.assertEqual(self.b["behavior_id"],"SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001")

    def test_exact_runtime_blob_is_current(self):
        pkg=self.b["exact_brain_package"]
        self.assertEqual(git_blob(Path(pkg["runtime"])),pkg["runtime_blob_sha"])

    def test_all_four_frozen_portfolios_are_bound(self):
        outer=load(Path("canonical/governance/OUTER_TERMINAL_MULTIPLEX_PORTFOLIOS_V1.json"))
        frozen={x["id"] for x in outer["portfolios"]}
        bound={x["portfolio"] for x in self.b["portfolio_bindings"].values()}
        self.assertEqual(bound,frozen)
        self.assertEqual(set(self.b["portfolio_bindings"]),{"T0","T1","T2","T3"})
        for row in self.b["portfolio_bindings"].values():
            self.assertTrue(row["instrumentation"])
            self.assertIn("ONLY",row["visible_information"])

    def test_counterexample_scorer_fails_closed(self):
        s=self.b["ambiguity_counterexample_scorer"]
        required={
            "CRITICAL_REQUIREMENT_WITHOUT_INDEPENDENT_ACCEPTANCE",
            "UNCOVERED_DECLARED_FAILURE_MODE",
            "BUILDER_CORRELATED_ACCEPTANCE_CHECK",
            "SHARED_NONRAW_DEPENDENCY",
            "DERIVED_FROM_BUILDER_OUTPUT",
            "AMBIGUITY_WITHOUT_FAIL_CLOSED_OR_DISCRIMINATING_EVIDENCE",
        }
        self.assertTrue(required.issubset(set(s["fail_conditions"])))

    def test_post_freeze_accounting_forbids_adaptation(self):
        a=self.b["post_freeze_selector_and_accounting"]
        self.assertIs(a["select_cases_before_candidate_freeze"],False)
        self.assertIs(a["adaptive_case_replacement"],False)
        self.assertIs(a["tune_on_selected_cases"],False)
        self.assertIs(a["scorer_mutation_after_results"],False)
        self.assertIs(a["failed_or_unknown_case_counts_as_pass"],False)
        self.assertIs(a["per_portfolio_semantic_acceptance_receipt_required"],True)
        self.assertIs(a["shared_behavior_credit_requires_direct_instrumentation"],True)

    def test_no_terminal_authority_or_credit(self):
        self.assertEqual(self.b["terminal_results_observed"],0)
        self.assertEqual(self.b["fresh_terminal_evidence_consumed"],0)
        self.assertEqual(self.b["capability_credit_delta"],0)
        self.assertEqual(self.b["family_credit_delta"],0)
        self.assertIn("NO_TERMINAL_RESULT",self.b["limitations"])

if __name__=="__main__":
    unittest.main()
