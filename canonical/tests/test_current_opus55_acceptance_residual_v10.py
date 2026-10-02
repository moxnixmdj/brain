from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.opus55_acceptance_residual_compiler_v2 import evaluate

ROOT = Path(__file__).resolve().parents[2]

def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class CurrentAcceptanceResidualV10Tests(unittest.TestCase):
    def live(self):
        return [
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
            load("canonical/reasoning/2026-10-02_EXACT_OPUS55_ZERO_COST_COMPARATOR_ROUTE_RECONCILIATION_V1.json"),
            load("canonical/governance/OPUS55_PUBLIC_BAR_SCORE_READINESS_MATRIX_V1.json"),
        ]

    def test_live_residual_is_exactly_9_proved_29_blocked(self):
        out = evaluate(*self.live())
        self.assertEqual(out["errors"], [], out)
        self.assertTrue(out["receipt_saturation_complete"], out)
        self.assertEqual(out["predicate_count"], 38)
        self.assertEqual(out["proved_predicate_count"], 9)
        self.assertEqual(out["open_predicate_count"], 0)
        self.assertEqual(out["blocked_predicate_count"], 29)
        self.assertEqual(out["refuted_predicate_count"], 0)
        self.assertEqual(out["authorized_actions"], [])
        delegation = next(
            row for row in out["families"]
            if row["family"] == "SUBAGENT_DELEGATION_AND_COORDINATION"
        )
        self.assertEqual(delegation["state"], "PROVED")
        self.assertEqual(delegation["proved"], delegation["predicate_count"])

    def test_delegation_ceiling_claim_is_load_bearing(self):
        registry, evidence, comparator, readiness = self.live()
        evidence = json.loads(json.dumps(evidence))
        evidence["claims"] = [
            c for c in evidence["claims"]
            if c.get("predicate_id") != "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"
        ]
        out = evaluate(registry, evidence, comparator, readiness)
        self.assertEqual(out["proved_predicate_count"], 8)
        self.assertEqual(out["blocked_predicate_count"], 30)
        delegation = next(
            row for row in out["families"]
            if row["family"] == "SUBAGENT_DELEGATION_AND_COORDINATION"
        )
        self.assertNotEqual(delegation["state"], "PROVED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
