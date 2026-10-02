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
                    json.dumps({"affected_contract_classes": list(open_domain)}),
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

    def test_open_domain_route_uses_matched_protocol_not_scope_expansion(self):
        out = self.run_basis([
            {
                "behavior_id": "OPEN",
                "portfolio": "T0_T1_T2_T3",
                "proof_state": "INDEPENDENT_PREFLIGHT_PASS",
                "blockers": [
                    "WHOLE_OPEN_ENDED_CONTRACT_SCOPE_EQUIVALENCE_NOT_YET_PROVEN",
                    "SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS",
                    "POST_FREEZE_TERMINAL_POPULATION_BINDING_PENDING",
                ],
            },
        ], open_domain={"OPEN"})
        row = out["queue"][0]
        self.assertEqual(row["proof_route_class"], "OPEN_DOMAIN_MATCHED")
        self.assertEqual(
            row["next_action_class"],
            "FREEZE_MATCHED_PROTOCOL_AND_RESOLVE_COMPARATOR_ACCESS",
        )

    def test_finite_route_keeps_scope_equivalence_path(self):
        out = self.run_basis([
            {
                "behavior_id": "FINITE",
                "portfolio": "T1",
                "proof_state": "INDEPENDENT_PREFLIGHT_PASS",
                "blockers": [
                    "WHOLE_CONTRACT_SCOPE_EQUIVALENCE_NOT_YET_PROVEN",
                    "SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS",
                ],
            },
        ], open_domain=set())
        row = out["queue"][0]
        self.assertEqual(row["proof_route_class"], "FINITE_OR_FORMAL")
        self.assertEqual(
            row["next_action_class"],
            "CLOSE_SCOPE_EQUIVALENCE_THEN_FREEZE_BINDING",
        )

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


if __name__ == "__main__":
    unittest.main()
