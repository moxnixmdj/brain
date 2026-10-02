from __future__ import annotations
import copy, json, unittest
from pathlib import Path
from canonical.runtime.opus55_acceptance_residual_compiler_v2 import evaluate

ROOT = Path(__file__).resolve().parents[2]

def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

class Tests(unittest.TestCase):
    def setUp(self):
        self.registry = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
        self.evidence = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
        self.comparator = load("canonical/reasoning/2026-10-02_EXACT_OPUS55_ZERO_COST_COMPARATOR_ROUTE_RECONCILIATION_V1.json")
        self.readiness = load("canonical/governance/OPUS55_PUBLIC_BAR_SCORE_READINESS_MATRIX_V1.json")

    def family(self, out, name):
        return next(r for r in out["families"] if r["family"] == name)

    def test_tool_learning_becomes_three_of_three_proved(self):
        out = evaluate(self.registry, self.evidence, self.comparator, self.readiness)
        self.assertEqual(out["errors"], [])
        row = self.family(out, "TOOL_DISCOVERY_SELECTION_AND_LEARNING")
        self.assertEqual(row["predicate_count"], 3)
        self.assertEqual(row["proved"], 3)
        self.assertEqual(row["open"], 0)
        self.assertEqual(row["blocked"], 0)
        self.assertEqual(row["state"], "PROVED")
        self.assertFalse(out["terminal_promotion_allowed"])
        claim = next(c for c in self.evidence["claims"] if c["predicate_id"] == "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
        self.assertEqual(claim["proof_kind"], "ABSOLUTE_CEILING")
        self.assertEqual(claim["source_sha"], "60a7c1139cad315d977bf5ed97e708cc5ec3fcc7")
        self.assertTrue(claim["scope_complete"])
        self.assertTrue(claim["independent_or_objective"])

    def test_removing_ceiling_claim_reopens_tool_learning(self):
        e = copy.deepcopy(self.evidence)
        e["claims"] = [c for c in e["claims"] if c.get("predicate_id") != "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"]
        out = evaluate(self.registry, e, self.comparator, self.readiness)
        row = self.family(out, "TOOL_DISCOVERY_SELECTION_AND_LEARNING")
        self.assertNotEqual(row["state"], "PROVED")
        self.assertEqual(row["proved"], 2)

if __name__ == "__main__":
    unittest.main(verbosity=2)
