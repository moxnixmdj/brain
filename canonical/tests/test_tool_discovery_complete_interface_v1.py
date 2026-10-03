from __future__ import annotations

import unittest

from canonical.runtime.tool_discovery_complete_interface_v1 import evaluate


SPEC = {
    "scope_id": "FROZEN_TOOL_DISCOVERY_TARGET",
    "declared_source_ids": ["REGISTRY_A", "REGISTRY_B"],
    "source_set_completeness_evidence_id": "E_SET",
    "unknown_identity_discovery_required": True,
    "preenumerated_tool_ids_required": False,
}
VERIFIED = ["E_SET", "E_A", "E_B"]


def receipt(source_id: str, evidence_id: str, tool_ids=None, **kw):
    out = {
        "kind": "COMPLETE_DISCOVERY_RESULT",
        "source_id": source_id,
        "scope_id": "FROZEN_TOOL_DISCOVERY_TARGET",
        "exhaustive_for_scope": True,
        "completeness_evidence_id": evidence_id,
        "tool_ids": list(tool_ids or []),
    }
    out.update(kw)
    return out


class CompleteDiscoveryInterfaceTests(unittest.TestCase):
    def test_accepts_arbitrary_nonpreenumerated_tool_ids(self):
        weird = ["vendor/tool@2026.10", "urn:plugin:ζ", "totally-new-id-991827"]
        out = evaluate(
            SPEC,
            [receipt("REGISTRY_A", "E_A", weird), receipt("REGISTRY_B", "E_B", ["X"])],
            verified_evidence_ids=VERIFIED,
        )
        self.assertTrue(out["admit_interface"])
        self.assertTrue(out["conditional_implication_proved"])
        self.assertFalse(out["target_proof_atom_discharged"])
        self.assertEqual(set(out["covered_tool_ids"]), set(weird + ["X"]))
        self.assertFalse(out["preenumerated_tool_ids_required"])

    def test_requires_source_set_completeness_evidence(self):
        out = evaluate(
            SPEC,
            [receipt("REGISTRY_A", "E_A"), receipt("REGISTRY_B", "E_B")],
            verified_evidence_ids=["E_A", "E_B"],
        )
        self.assertFalse(out["admit_interface"])
        self.assertIn("UNVERIFIED_SOURCE_SET_COMPLETENESS", out["errors"])

    def test_requires_every_declared_source(self):
        out = evaluate(
            SPEC,
            [receipt("REGISTRY_A", "E_A")],
            verified_evidence_ids=VERIFIED,
        )
        self.assertFalse(out["admit_interface"])
        self.assertIn("MISSING_SOURCE_RECEIPT:REGISTRY_B", out["errors"])

    def test_rejects_undeclared_source(self):
        out = evaluate(
            SPEC,
            [
                receipt("REGISTRY_A", "E_A"),
                receipt("REGISTRY_B", "E_B"),
                receipt("REGISTRY_C", "E_B"),
            ],
            verified_evidence_ids=VERIFIED,
        )
        self.assertFalse(out["admit_interface"])
        self.assertIn("UNDECLARED_SOURCE:REGISTRY_C", out["errors"])

    def test_rejects_scope_mismatch(self):
        out = evaluate(
            SPEC,
            [
                receipt("REGISTRY_A", "E_A", scope_id="OTHER"),
                receipt("REGISTRY_B", "E_B"),
            ],
            verified_evidence_ids=VERIFIED,
        )
        self.assertFalse(out["admit_interface"])
        self.assertIn("SCOPE_MISMATCH:REGISTRY_A", out["errors"])

    def test_rejects_nonexhaustive_source(self):
        out = evaluate(
            SPEC,
            [
                receipt("REGISTRY_A", "E_A", exhaustive_for_scope=False),
                receipt("REGISTRY_B", "E_B"),
            ],
            verified_evidence_ids=VERIFIED,
        )
        self.assertFalse(out["admit_interface"])
        self.assertIn("SOURCE_NOT_EXHAUSTIVE:REGISTRY_A", out["errors"])

    def test_rejects_unverified_per_source_completeness(self):
        out = evaluate(
            SPEC,
            [receipt("REGISTRY_A", "NOT_VERIFIED"), receipt("REGISTRY_B", "E_B")],
            verified_evidence_ids=VERIFIED,
        )
        self.assertFalse(out["admit_interface"])
        self.assertIn("UNVERIFIED_SOURCE_COMPLETENESS:REGISTRY_A", out["errors"])

    def test_rejects_duplicate_source_receipt(self):
        out = evaluate(
            SPEC,
            [
                receipt("REGISTRY_A", "E_A"),
                receipt("REGISTRY_A", "E_A"),
                receipt("REGISTRY_B", "E_B"),
            ],
            verified_evidence_ids=VERIFIED,
        )
        self.assertFalse(out["admit_interface"])
        self.assertIn("DUPLICATE_SOURCE_RECEIPT:REGISTRY_A", out["errors"])

    def test_rejects_pre_enumerated_identity_dependency(self):
        bad = dict(SPEC)
        bad["preenumerated_tool_ids_required"] = True
        out = evaluate(
            bad,
            [receipt("REGISTRY_A", "E_A"), receipt("REGISTRY_B", "E_B")],
            verified_evidence_ids=VERIFIED,
        )
        self.assertFalse(out["admit_interface"])
        self.assertEqual(out["status"], "FAIL_CLOSED__INVALID_SPEC")

    def test_requires_unknown_identity_semantics(self):
        bad = dict(SPEC)
        bad["unknown_identity_discovery_required"] = False
        out = evaluate(
            bad,
            [receipt("REGISTRY_A", "E_A"), receipt("REGISTRY_B", "E_B")],
            verified_evidence_ids=VERIFIED,
        )
        self.assertFalse(out["admit_interface"])

    def test_empty_tool_results_are_valid_when_scope_is_verified_complete(self):
        out = evaluate(
            SPEC,
            [receipt("REGISTRY_A", "E_A", []), receipt("REGISTRY_B", "E_B", [])],
            verified_evidence_ids=VERIFIED,
        )
        self.assertTrue(out["admit_interface"])
        self.assertEqual(out["covered_tool_ids"], [])

    def test_grants_zero_terminal_authority(self):
        out = evaluate(
            SPEC,
            [receipt("REGISTRY_A", "E_A", ["A"]), receipt("REGISTRY_B", "E_B", ["B"])],
            verified_evidence_ids=VERIFIED,
        )
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
