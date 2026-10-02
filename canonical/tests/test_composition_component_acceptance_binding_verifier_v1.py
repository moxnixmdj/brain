from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.composition_component_acceptance_binding_verifier_v1 import evaluate

ROOT = Path(__file__).resolve().parents[2]
DOC = json.loads((ROOT / "canonical/governance/COMPOSITION_COMPONENT_ACCEPTANCE_BINDINGS_V1.json").read_text())


class Tests(unittest.TestCase):
    def test_live_candidate_reuses_exactly_three_existing_acceptance_proofs(self):
        out = evaluate(DOC)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["scoped_proved_component_count"], 3)
        self.assertEqual(out["scoped_proved_components"], ["delegation", "memory", "tool discovery"])
        self.assertEqual(out["open_component_count"], 9)
        self.assertFalse(out["composition_atomic_predicate_closed"])
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)

    def test_source_blob_tamper_fails_closed(self):
        d = copy.deepcopy(DOC)
        d["bindings"][1]["source_git_blob_sha"] = "0" * 40
        self.assertFalse(evaluate(d)["pass"])

    def test_unfrozen_component_pair_fails_closed(self):
        d = copy.deepcopy(DOC)
        d["bindings"][0]["component_id"] = "semantic memory"
        self.assertFalse(evaluate(d)["pass"])

    def test_uncalibrated_family_fails_closed(self):
        d = copy.deepcopy(DOC)
        d["bindings"][0]["family"] = "COMMUNICATION_AND_SYNTHESIS"
        self.assertFalse(evaluate(d)["pass"])

    def test_cannot_claim_extra_property(self):
        d = copy.deepcopy(DOC)
        d["bindings"][2]["proved_properties"] = ["SCOPED_ACCEPTANCE_PROOF", "SYNTHESIS_PROOF"]
        self.assertFalse(evaluate(d)["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
