from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from canonical.runtime.material_condition_closure_v1 import compile_material_condition_closure

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class MaterialConditionClosureTests(unittest.TestCase):
    def docs(self):
        return (
            load("canonical/governance/OPUS55_MATERIAL_CONDITION_REGISTRY_V1.json"),
            load("canonical/governance/OPUS55_MATERIAL_CONDITION_EVIDENCE_BINDINGS_V1.json"),
            load("canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json"),
        )

    def test_live_known_conditions_fail_terminal_gate_without_overclaim(self):
        registry, evidence, envelope = self.docs()
        out = compile_material_condition_closure(registry, evidence, envelope)
        self.assertTrue(out["pass"], out)
        self.assertGreater(out["condition_count"], 0)
        self.assertEqual(out["proved_condition_count"], 0)
        self.assertEqual(out["open_condition_count"], out["condition_count"])
        self.assertFalse(out["source_universe_sealed"])
        self.assertFalse(out["terminal_condition_gate_pass"])
        self.assertFalse(out["legacy_atomic_predicate_denominator_sufficient_for_terminal_finality"])

    def test_denominator_is_dynamic_not_hard_coded(self):
        registry, evidence, envelope = self.docs()
        registry = copy.deepcopy(registry)
        registry["conditions"].append({
            "id": "FUTURE_DISCOVERED_MATERIAL_CONDITION",
            "kind": "CROSS_CUTTING_TEST_CONDITION",
            "families": ["COMMUNICATION_AND_SYNTHESIS"],
            "source": "test",
            "acceptance": "test"
        })
        out = compile_material_condition_closure(registry, evidence, envelope)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["condition_count"], len(registry["conditions"]))
        self.assertIn("FUTURE_DISCOVERED_MATERIAL_CONDITION", out["open_conditions"])

    def test_all_known_conditions_are_still_insufficient_while_universe_unsealed(self):
        registry, evidence, envelope = self.docs()
        evidence = copy.deepcopy(evidence)
        evidence["claims"] = [
            {"condition_id": row["id"], "state": "PROVED", "scope_complete": True}
            for row in registry["conditions"]
        ]
        out = compile_material_condition_closure(registry, evidence, envelope)
        self.assertEqual(out["proved_condition_count"], out["condition_count"])
        self.assertFalse(out["source_universe_sealed"])
        self.assertFalse(out["terminal_condition_gate_pass"])

    def test_seal_plus_all_scope_complete_conditions_closes_gate(self):
        registry, evidence, envelope = self.docs()
        registry = copy.deepcopy(registry)
        evidence = copy.deepcopy(evidence)
        registry["source_universe"]["sealed"] = True
        registry["source_universe"]["independent_seal_receipt"] = {
            "path": "canonical/verification/test-independent-receipt.json",
            "git_blob_sha": "a" * 40,
            "state": "INDEPENDENT_PASS",
        }
        evidence["claims"] = [
            {"condition_id": row["id"], "state": "PROVED", "scope_complete": True}
            for row in registry["conditions"]
        ]
        out = compile_material_condition_closure(
            registry, evidence, envelope,
            verified_source_universe_receipt_sha="a" * 40,
        )
        self.assertTrue(out["terminal_condition_gate_pass"], out)

    def test_declared_seal_with_unverified_blob_fails_closed(self):
        registry, evidence, envelope = self.docs()
        registry = copy.deepcopy(registry)
        evidence = copy.deepcopy(evidence)
        registry["source_universe"]["sealed"] = True
        registry["source_universe"]["independent_seal_receipt"] = {
            "path": "canonical/verification/fake.json",
            "git_blob_sha": "b" * 40,
            "state": "INDEPENDENT_PASS",
        }
        evidence["claims"] = [
            {"condition_id": row["id"], "state": "PROVED", "scope_complete": True}
            for row in registry["conditions"]
        ]
        out = compile_material_condition_closure(
            registry, evidence, envelope,
            verified_source_universe_receipt_sha=None,
        )
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_UNIVERSE_SEAL_RECEIPT_BLOB_NOT_VERIFIED", out["errors"])
        self.assertFalse(out["terminal_condition_gate_pass"])

    def test_scope_incomplete_claim_does_not_close_condition(self):
        registry, evidence, envelope = self.docs()
        target = registry["conditions"][0]["id"]
        evidence = copy.deepcopy(evidence)
        evidence["claims"] = [
            {"condition_id": target, "state": "PROVED", "scope_complete": False}
        ]
        out = compile_material_condition_closure(registry, evidence, envelope)
        self.assertIn(target, out["open_conditions"])

    def test_family_outside_envelope_fails_closed(self):
        registry, evidence, envelope = self.docs()
        registry = copy.deepcopy(registry)
        registry["conditions"][0]["families"] = ["NONEXISTENT_FAMILY"]
        out = compile_material_condition_closure(registry, evidence, envelope)
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("CONDITION_FAMILY_OUTSIDE_TARGET_ENVELOPE") for x in out["errors"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
