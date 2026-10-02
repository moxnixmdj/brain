from __future__ import annotations

import copy
import unittest

from canonical.runtime.residual_frontier_authority_guard import validate_frontier


def basis():
    return {
        "schema": "PROJECT_BRAIN_ACTIVE_TERMINAL_PROOF_BASIS_V1",
        "contracts": [
            {"behavior_id": "A", "blockers": ["A1"]},
            {"behavior_id": "B", "blockers": []},
            {"behavior_id": "C", "blockers": ["C1", "C2"]},
        ],
    }


def residual():
    return {
        "schema": "PROJECT_BRAIN_GLOBAL_RESIDUAL_PROOF_COMPILER_INPUT_V1",
        "obligations": ["A", "C"],
        "blockers": [],
        "semantic_blocker_equivalence": [],
        "routes": [
            {
                "id": "A_ROUTE",
                "covers": ["A"],
            }
        ],
    }


class ResidualFrontierAuthorityGuardTests(unittest.TestCase):
    def test_exact_blocked_set_passes(self):
        out = validate_frontier(basis(), residual())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["blocked_obligation_count"], 2)
        self.assertEqual(out["live_residual_obligations"], ["A", "C"])

    def test_admitted_contract_in_queue_fails_closed(self):
        r = residual()
        r["obligations"].append("B")
        out = validate_frontier(basis(), r)
        self.assertFalse(out["pass"])
        self.assertTrue(
            any(e.startswith("STALE_ADMITTED_OBLIGATIONS:B") for e in out["errors"])
        )

    def test_missing_blocked_contract_fails_closed(self):
        r = residual()
        r["obligations"].remove("C")
        out = validate_frontier(basis(), r)
        self.assertFalse(out["pass"])
        self.assertTrue(
            any(e.startswith("MISSING_BLOCKED_OBLIGATIONS:C") for e in out["errors"])
        )

    def test_unknown_obligation_fails_closed(self):
        r = residual()
        r["obligations"].append("Z")
        out = validate_frontier(basis(), r)
        self.assertFalse(out["pass"])
        self.assertTrue(
            any(e.startswith("UNKNOWN_RESIDUAL_OBLIGATIONS:Z") for e in out["errors"])
        )

    def test_route_covering_off_frontier_contract_fails_closed(self):
        r = residual()
        r["routes"][0]["covers"].append("B")
        out = validate_frontier(basis(), r)
        self.assertFalse(out["pass"])
        self.assertTrue(
            any(e.startswith("ROUTE_COVERS_OFF_FRONTIER:A_ROUTE:B") for e in out["errors"])
        )

    def test_malformed_contract_blockers_fail_closed(self):
        b = copy.deepcopy(basis())
        b["contracts"][0]["blockers"] = "A1"
        out = validate_frontier(b, residual())
        self.assertFalse(out["pass"])
        self.assertIn("CONTRACT_BLOCKERS_INVALID:A", out["errors"])


if __name__ == "__main__":
    unittest.main()
