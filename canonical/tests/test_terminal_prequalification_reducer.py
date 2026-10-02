from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.terminal_prequalification_reducer import evaluate


class TerminalPrequalificationReducerTests(unittest.TestCase):
    def fixture(self, blockers=None):
        blockers = blockers or {}
        return {
            "schema": "PROJECT_BRAIN_EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1",
            "core_deduction": {
                "preproof_implementation_residual_count": 0,
                "consequence": "NO_NEW_GENERIC_MECHANISM_WORK_BEFORE_TERMINAL_WAVE",
            },
            "prequalification_progress": {
                "exact_cut_current_and_verified": True,
                "zero_open_specification_holes": True,
                "zero_preproof_implementation_residuals": True,
                "shared_one_shot_contamination_oracle_mutation_protocol_frozen": True,
                "public_evaluation_route_matrix_frozen": True,
                "brain_route_and_dependency_manifest_frozen": "PASS__receipt",
                "no_known_opaque_target_capability_provider_in_operative_brain_route": "PASS__receipt",
                "no_known_unresolved_composition_defect_before_wave": "PASS__receipt",
                "every_surface_zero_cost_route_frozen": True,
                "every_surface_oracle_and_verifier_binding_frozen": True,
                "every_portfolio_task_case_harness_metric_stop_rule_and_mutation_set_frozen": True,
                "four_portfolios_pairwise_execution_independent": "PASS__FROZEN",
            },
            "portfolio_status": {
                "T0_CODING_SEMANTIC_GEOMETRY_PORTFOLIO": {"blockers": blockers.get("T0", [])},
                "T1_PROFESSIONAL_FINANCE_ARTIFACT_SYNTHESIS_VISION_PORTFOLIO": {"blockers": blockers.get("T1", [])},
                "T2_INTERACTIVE_AGENCY_RECOVERY_SCOPE_DELEGATION_COMPOSITION_PORTFOLIO": {"blockers": blockers.get("T2", [])},
                "T3_RESEARCH_UNKNOWN_DOMAIN_PORTFOLIO": {"blockers": blockers.get("T3", [])},
            },
            "remaining_irreducible_prequalification_blockers": [],
        }

    def run_fixture(self, payload):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "canonical/governance"
            path.mkdir(parents=True)
            (path / "EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            return evaluate(root)

    def test_all_explicit_gates_pass(self):
        out = self.run_fixture(self.fixture())
        self.assertTrue(out["pass"])
        self.assertEqual(out["authorization"], "T0_T1_T2_T3_PARALLEL_TERMINAL_WAVE")

    def test_surface_blocker_fails_closed(self):
        out = self.run_fixture(self.fixture({"T1": ["SCORER_OPEN"]}))
        self.assertFalse(out["pass"])
        self.assertIn("PORTFOLIO_BLOCKED:T1_PROFESSIONAL_FINANCE_ARTIFACT_SYNTHESIS_VISION_PORTFOLIO", out["failed_predicates"])

    def test_missing_boolean_gate_fails_closed(self):
        p = self.fixture()
        p["prequalification_progress"]["every_surface_zero_cost_route_frozen"] = False
        out = self.run_fixture(p)
        self.assertFalse(out["pass"])

    def test_stale_optimistic_status_cannot_override_blocker(self):
        p = self.fixture({"T3": ["GRADER_OPEN"]})
        p["status"] = "EXECUTION_READY"
        p["execution_authority"] = True
        out = self.run_fixture(p)
        self.assertFalse(out["pass"])


if __name__ == "__main__":
    unittest.main()
