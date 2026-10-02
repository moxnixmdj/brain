from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.terminal_route_closure_controller import evaluate


class TerminalRouteClosureControllerTests(unittest.TestCase):
    def run_basis(self, contracts, declared_closed=None, open_domain=None):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/governance"
            p.mkdir(parents=True)
            closed = sum(
                x.get("proof_state") == "TERMINAL_ROUTE_FROZEN_ADMISSIBLE"
                for x in contracts
            )
            (p / "ACTIVE_TERMINAL_PROOF_BASIS_V1.json").write_text(
                json.dumps({
                    "active_contract_count": len(contracts),
                    "admissible_frozen_terminal_route_count": (
                        closed if declared_closed is None else declared_closed
                    ),
                    "contracts": contracts,
                }),
                encoding="utf-8",
            )
            if open_domain is not None:
                (p / "OPEN_DOMAIN_PREQUALIFICATION_DEADLOCK_AUDIT_V1.json").write_text(
                    json.dumps({
                        "status": "FAIL_CLOSED_CONTROLLER_DEFECT_FOUND__FINITE_SCOPE_EQUIVALENCE_MUST_NOT_BE_REQUIRED_FOR_CANONICAL_OPEN_DOMAIN_MATCHED_PROTOCOLS",
                        "affected_contract_classes": list(open_domain),
                        "corrected_prequalification_law": {
                            "open_domain_matched_routes": "FREEZE_MATCHED_PROTOCOL_NOT_SYNTHETIC_WHOLE_SCOPE_PROOF"
                        },
                    }),
                    encoding="utf-8",
                )
            return evaluate(root)

    def test_closed_routes_are_removed_from_queue(self):
        out = self.run_basis([
            {
                "behavior_id": "A",
                "portfolio": "T1",
                "proof_state": "TERMINAL_ROUTE_FROZEN_ADMISSIBLE",
                "blockers": [],
            },
            {
                "behavior_id": "B",
                "portfolio": "T2",
                "proof_state": "INDEPENDENT_PREFLIGHT_PASS",
                "blockers": ["POST_FREEZE_TERMINAL_POPULATION_BINDING_PENDING"],
            },
        ])
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["closed_route_count"], 1)
        self.assertEqual([x["behavior_id"] for x in out["queue"]], ["B"])

    def test_binding_only_precedes_scope_expansion(self):
        out = self.run_basis([
            {
                "behavior_id": "BIND",
                "portfolio": "T2",
                "proof_state": "INDEPENDENT_PREFLIGHT_PASS",
                "blockers": [
                    "SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS",
                    "POST_FREEZE_TERMINAL_POPULATION_BINDING_PENDING",
                ],
            },
            {
                "behavior_id": "EXPAND",
                "portfolio": "T0_T1",
                "proof_state": "INDEPENDENT_PREFLIGHT_PASS",
                "blockers": [
                    "WHOLE_CONTRACT_SCOPE_EQUIVALENCE_NOT_YET_PROVEN",
                    "SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS",
                ],
            },
        ])
        self.assertEqual(out["queue"][0]["behavior_id"], "BIND")

    def test_multiportfolio_leverage_breaks_equal_cost_tie(self):
        out = self.run_basis([
            {
                "behavior_id": "ONE",
                "portfolio": "T1",
                "proof_state": "INDEPENDENT_PREFLIGHT_PASS",
                "blockers": ["POST_FREEZE_TERMINAL_POPULATION_BINDING_PENDING"],
            },
            {
                "behavior_id": "FOUR",
                "portfolio": "T0_T1_T2_T3",
                "proof_state": "INDEPENDENT_PREFLIGHT_PASS",
                "blockers": ["POST_FREEZE_TERMINAL_POPULATION_BINDING_PENDING"],
            },
        ])
        self.assertEqual(out["queue"][0]["behavior_id"], "FOUR")

    def test_declared_closed_count_cannot_drift(self):
        out = self.run_basis([
            {
                "behavior_id": "A",
                "portfolio": "T1",
                "proof_state": "TERMINAL_ROUTE_FROZEN_ADMISSIBLE",
                "blockers": [],
            },
        ], declared_closed=0)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("ADMISSIBLE_ROUTE_COUNT_MISMATCH", out["errors"])

    def test_open_route_without_blocker_fails_closed(self):
        out = self.run_basis([
            {
                "behavior_id": "A",
                "portfolio": "T1",
                "proof_state": "ROUTE_REQUIRED",
                "blockers": [],
            },
        ])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("OPEN_ROUTE_WITHOUT_BLOCKER:A", out["errors"])

    def test_external_comparator_block_is_classified_and_not_scope_expansion(self):
        out = self.run_basis([
            {
                "behavior_id": "TRAJECTORY",
                "portfolio": "T0_T2",
                "proof_state": "BOUNDED_INFORMATION_SAFE_PREFLIGHT_PRESERVED__OPEN_DOMAIN_MATCHED_TERMINAL_PROTOCOL_FREEZE_PENDING",
                "blockers": [
                    "FREEZE_SELF_VERIFICATION_CAUSAL_INTERVENTION_CHALLENGE_SOURCE_POOL_AND_SCORER",
                    "FREEZE_MATCHED_HARNESS_INFORMATION_TOOL_RESOURCE_AND_AUTHORITY_SYMMETRY",
                    "EXACT_OPUS_5_5_CASE_LEVEL_COMPARATOR_UNAVAILABLE_AT_ZERO_INCREMENTAL_SPEND_FOR_UNCOVERED_CAUSAL_RECOVERY_SCOPE",
                ],
            },
        ])
        self.assertEqual(out["status"], "PASS")
        row = out["queue"][0]
        self.assertEqual(row["blocker_classes"]["external_block"], 1)
        self.assertEqual(row["blocker_classes"]["open_domain_protocol"], 2)
        self.assertEqual(row["blocker_classes"]["scope_expansion"], 0)
        self.assertEqual(
            row["next_action_class"],
            "EXTERNAL_BLOCKED__FREEZE_INTERNAL_PROTOCOL_FIELDS_ONLY__DO_NOT_SPEND_CLEAN_CASES",
        )

    def test_external_blocked_lane_is_ranked_after_actionable_internal_lane(self):
        out = self.run_basis([
            {
                "behavior_id": "ACTIONABLE",
                "portfolio": "T1",
                "proof_state": "INDEPENDENT_PREFLIGHT_PASS",
                "blockers": [
                    "SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS",
                    "POST_FREEZE_TERMINAL_POPULATION_BINDING_PENDING",
                ],
            },
            {
                "behavior_id": "BLOCKED",
                "portfolio": "T0_T2",
                "proof_state": "BOUNDED_INFORMATION_SAFE_PREFLIGHT_PRESERVED",
                "blockers": [
                    "FREEZE_MATCHED_HARNESS_INFORMATION_TOOL_RESOURCE_AND_AUTHORITY_SYMMETRY",
                    "EXACT_OPUS_5_5_CASE_LEVEL_COMPARATOR_UNAVAILABLE_AT_ZERO_INCREMENTAL_SPEND",
                ],
            },
        ])
        self.assertEqual(
            [x["behavior_id"] for x in out["queue"]],
            ["ACTIONABLE", "BLOCKED"],
        )

    def test_canonical_open_domain_legacy_scope_blocker_is_reclassified_first(self):
        out = self.run_basis([
            {
                "behavior_id": "OPEN",
                "portfolio": "T1_T3",
                "proof_state": "INDEPENDENT_INFORMATION_SAFE_PREFLIGHT_PASS__WHOLE_SCOPE_ADMISSION_PENDING",
                "blockers": [
                    "WHOLE_OPEN_ENDED_CONTRACT_SCOPE_EQUIVALENCE_NOT_YET_PROVEN",
                    "SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS",
                    "POST_FREEZE_TERMINAL_POPULATION_BINDING_PENDING",
                ],
            },
        ], open_domain=["OPEN"])
        self.assertEqual(out["status"], "PASS")
        row = out["queue"][0]
        self.assertTrue(row["open_domain_matched_protocol"])
        self.assertEqual(row["next_action_class"], "RECLASSIFY_TO_OPEN_DOMAIN_MATCHED_PROTOCOL")
        self.assertEqual(row["blocker_classes"]["legacy_open_domain_scope_equivalence"], 2)
        self.assertEqual(out["reclassification_required_behavior_ids"], ["OPEN"])

    def test_invalid_open_domain_audit_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "canonical/governance"
            p.mkdir(parents=True)
            (p / "ACTIVE_TERMINAL_PROOF_BASIS_V1.json").write_text(json.dumps({
                "active_contract_count": 0,
                "admissible_frozen_terminal_route_count": 0,
                "contracts": [],
            }))
            (p / "OPEN_DOMAIN_PREQUALIFICATION_DEADLOCK_AUDIT_V1.json").write_text(json.dumps({
                "status": "DRAFT",
                "affected_contract_classes": ["OPEN"],
                "corrected_prequalification_law": {"open_domain_matched_routes": "x"},
            }))
            out = evaluate(root)
            self.assertEqual(out["status"], "FAIL_CLOSED")
            self.assertTrue(out["errors"][0].startswith("OPEN_DOMAIN_AUDIT_INVALID:"))


if __name__ == "__main__":
    unittest.main()
