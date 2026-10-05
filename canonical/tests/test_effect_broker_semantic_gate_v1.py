import unittest
from unittest.mock import patch

import canonical.runtime.effect_broker_semantic_gate_v1 as gate


REQUEST = {
    "request_sha256": "r" * 64,
    "mission_id": "m1",
    "capsule_head_sha256": "c" * 64,
    "effect_kind": "REPO_WRITE",
    "resource": "repo/path",
    "operation": "create",
    "payload_sha256": "p" * 64,
}


def resolved(schema):
    return {
        "path": "canonical/verification/x.json",
        "git_blob_sha": "a" * 40,
        "document": {"schema": schema, "self_asserted": True},
    }


def exact_verifier(role, schema):
    def verifier(document, binding):
        return {
            "verified": True,
            "role": role,
            "receipt_schema": schema,
            **binding,
            "verifier_id": role + "-v1",
            "proof_digest": role + "-proof",
        }
    return verifier


class SemanticGateTests(unittest.TestCase):
    def test_unknown_byte_valid_schema_denies(self):
        out = gate.authorize_semantics(
            request=REQUEST,
            resolved_authority_receipt=resolved("SELF_ASSERTED_AUTH"),
            resolved_composition_receipt=resolved("SELF_ASSERTED_COMP"),
        )
        self.assertFalse(out["allowed"])
        self.assertIn("AUTHORITY_SCHEMA_UNVERIFIED", out["reason"])

    def test_one_known_one_unknown_denies(self):
        reg = {("authority", "AUTH_V1"): exact_verifier("authority", "AUTH_V1")}
        with patch.object(gate, "BUILTIN_VERIFIERS", reg):
            out = gate.authorize_semantics(
                request=REQUEST,
                resolved_authority_receipt=resolved("AUTH_V1"),
                resolved_composition_receipt=resolved("COMP_UNKNOWN"),
            )
        self.assertFalse(out["allowed"])
        self.assertIn("COMPOSITION_SCHEMA_UNVERIFIED", out["reason"])

    def test_both_exact_pinned_verifiers_allow(self):
        reg = {
            ("authority", "AUTH_V1"): exact_verifier("authority", "AUTH_V1"),
            ("composition", "COMP_V1"): exact_verifier("composition", "COMP_V1"),
        }
        with patch.object(gate, "BUILTIN_VERIFIERS", reg):
            out = gate.authorize_semantics(
                request=REQUEST,
                resolved_authority_receipt=resolved("AUTH_V1"),
                resolved_composition_receipt=resolved("COMP_V1"),
            )
        self.assertTrue(out["allowed"])
        self.assertTrue(out["effect_carrier_enforcement_still_required"])

    def test_verifier_cannot_rebind_request(self):
        def liar(document, binding):
            out = exact_verifier("authority", "AUTH_V1")(document, binding)
            out["request_sha256"] = "evil"
            return out
        reg = {
            ("authority", "AUTH_V1"): liar,
            ("composition", "COMP_V1"): exact_verifier("composition", "COMP_V1"),
        }
        with patch.object(gate, "BUILTIN_VERIFIERS", reg):
            out = gate.authorize_semantics(
                request=REQUEST,
                resolved_authority_receipt=resolved("AUTH_V1"),
                resolved_composition_receipt=resolved("COMP_V1"),
            )
        self.assertFalse(out["allowed"])
        self.assertIn("VERIFIER_BINDING_MISMATCH:request_sha256", out["reason"])

    def test_extra_unbound_verifier_claim_denies(self):
        def noisy(document, binding):
            out = exact_verifier("authority", "AUTH_V1")(document, binding)
            out["trust_me"] = True
            return out
        reg = {
            ("authority", "AUTH_V1"): noisy,
            ("composition", "COMP_V1"): exact_verifier("composition", "COMP_V1"),
        }
        with patch.object(gate, "BUILTIN_VERIFIERS", reg):
            out = gate.authorize_semantics(
                request=REQUEST,
                resolved_authority_receipt=resolved("AUTH_V1"),
                resolved_composition_receipt=resolved("COMP_V1"),
            )
        self.assertFalse(out["allowed"])
        self.assertIn("VERIFIER_OUTPUT_UNBOUND_FIELDS", out["reason"])

    def test_missing_request_binding_denies(self):
        broken = dict(REQUEST)
        broken.pop("payload_sha256")
        out = gate.authorize_semantics(
            request=broken,
            resolved_authority_receipt=resolved("AUTH_V1"),
            resolved_composition_receipt=resolved("COMP_V1"),
        )
        self.assertFalse(out["allowed"])
        self.assertIn("PAYLOAD_SHA256_INVALID", out["reason"])


if __name__ == "__main__":
    unittest.main()
