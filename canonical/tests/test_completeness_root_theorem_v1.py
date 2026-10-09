from __future__ import annotations

import json
from pathlib import Path
import unittest

from canonical.runtime.completeness_root_theorem_v1 import (
    ROOTS,
    classify_new_e,
    evaluate_terminal,
    run_seeded_falsifiers,
    validate_spec,
)

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "canonical/governance/COMPLETENESS_ROOT_THEOREM_20261009_V1.json"


class Tests(unittest.TestCase):
    def load_spec(self):
        return json.loads(SPEC.read_text(encoding="utf-8"))

    def test_spec_is_exact_four_root_zero_credit_meta_control(self):
        doc = self.load_spec()
        out = validate_spec(doc)
        self.assertTrue(out["pass"], out)
        self.assertEqual(tuple(doc["roots"].keys()), ROOTS)
        self.assertEqual(doc["current_activation"]["terminal_credit_delta"], 0)

    def test_terminal_requires_all_four_roots(self):
        open_state = {r: True for r in ROOTS}
        open_state["R3_TERMINAL_CLOSURE"] = False
        self.assertFalse(evaluate_terminal(open_state)["terminal"])
        self.assertTrue(evaluate_terminal({r: True for r in ROOTS})["terminal"])

    def test_countermodel_blocks_terminal_even_when_roots_are_asserted_true(self):
        out = evaluate_terminal({r: True for r in ROOTS}, false_success_witness=True)
        self.assertFalse(out["pass"])
        self.assertFalse(out["terminal"])
        self.assertTrue(out["new_root_review_required"])

    def test_existing_root_counterexample_does_not_create_new_root(self):
        out = classify_new_e({"violated_roots": ["R1_REALITY_CONTAINMENT"]})
        self.assertEqual(out["classification"], "EXISTING_ROOT_COUNTEREXAMPLE")
        self.assertFalse(out["new_root_allowed"])

    def test_no_root_or_cost_delta_is_demoted(self):
        out = classify_new_e({})
        self.assertEqual(out["classification"], "DEMOTE_FROM_CANONICAL_ARCHITECTURE")
        self.assertFalse(out["new_root_allowed"])

    def test_proof_search_failure_is_capability_not_falsehood(self):
        out = classify_new_e({"proof_search_failure_only": True})
        self.assertTrue(out["classification"].startswith("CAPABILITY_CLOSURE"))
        self.assertFalse(out["new_root_allowed"])

    def test_seeded_falsification_campaign_detects_all_ten(self):
        out = run_seeded_falsifiers()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["detected"], 10)
        self.assertEqual(out["total"], 10)
        self.assertEqual(out["mutation_score"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
