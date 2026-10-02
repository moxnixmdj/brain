from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.witness_target_binding_totalizer_v1 import totalize

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class WitnessTargetBindingTotalizerTests(unittest.TestCase):
    def docs(self):
        return (
            load("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json"),
            load("canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"),
        )

    def test_live_surface_is_totalized_without_invented_semantics(self):
        targets, witnesses = self.docs()
        out = totalize(targets, witnesses)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["binding_surface_totalized"])
        self.assertEqual(out["target_count"], 11)
        self.assertEqual(out["witness_count"], 9)
        self.assertEqual(out["pair_count"], 99)
        self.assertEqual(out["target_atom_occurrence_count"], 47)
        self.assertEqual(out["target_metric_occurrence_count"], 10)
        self.assertEqual(out["direct_atom_binding_count"], 0)
        self.assertEqual(out["direct_metric_binding_count"], 0)
        self.assertFalse(out["semantic_implication_verified"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertTrue(all(not p["bound_atoms"] and not p["bound_metrics"] for p in out["pairs"]))

    def test_positive_atom_without_independent_binding_receipt_fails_closed(self):
        targets, witnesses = self.docs()
        witnesses = copy.deepcopy(witnesses)
        witnesses["witnesses"][0]["normalized_target_atoms"] = [
            "invariant:zero_critical_authority_violations"
        ]
        out = totalize(targets, witnesses)
        self.assertFalse(out["pass"])
        self.assertTrue(any("ATOM_BINDING_RECEIPT_MISSING" in e for e in out["errors"]))


    def test_positive_atom_even_with_receipt_is_forbidden_in_v1(self):
        targets, witnesses = self.docs()
        witnesses = copy.deepcopy(witnesses)
        atom = "invariant:zero_critical_authority_violations"
        witnesses["witnesses"][0]["normalized_target_atoms"] = [atom]
        witnesses["witnesses"][0]["target_atom_binding_receipts"] = {atom: "receipt://not-enough"}
        out = totalize(targets, witnesses)
        self.assertFalse(out["pass"])
        self.assertTrue(any("POSITIVE_SEMANTIC_BINDING_FORBIDDEN_IN_V1" in e for e in out["errors"]))

    def test_atom_outside_frozen_target_vocabulary_fails_closed(self):
        targets, witnesses = self.docs()
        witnesses = copy.deepcopy(witnesses)
        witnesses["witnesses"][0]["normalized_target_atoms"] = ["invented:semantic_shortcut"]
        witnesses["witnesses"][0]["target_atom_binding_receipts"] = {
            "invented:semantic_shortcut": "receipt://fake"
        }
        out = totalize(targets, witnesses)
        self.assertFalse(out["pass"])
        self.assertTrue(any("ATOM_OUTSIDE_TARGET_VOCAB" in e for e in out["errors"]))

    def test_unverified_semantic_edge_fails_closed(self):
        targets, witnesses = self.docs()
        witnesses = copy.deepcopy(witnesses)
        witnesses["witnesses"][0]["semantic_implications"] = [{
            "if_all": ["x"],
            "then": ["y"],
            "verified": False,
            "receipt": "receipt://bad"
        }]
        out = totalize(targets, witnesses)
        self.assertFalse(out["pass"])
        self.assertTrue(any("SEMANTIC_EDGE_0_NOT_INDEPENDENTLY_VERIFIED" in e for e in out["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
