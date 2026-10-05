import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime.effect_broker_contract_v1 import make_grant, make_request
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
import canonical.runtime.effect_broker_semantic_gate_v1 as semantic_gate
from canonical.runtime.effect_broker_final_authorizer_v1 import authorize_effect


def write_receipt(root, rel, schema):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps({"schema": schema}, sort_keys=True) + "\n").encode()
    p.write_bytes(data)
    return {
        "path": rel,
        "git_blob_sha": git_blob_id(data, object_format="sha1"),
    }


def verifier(role, schema):
    def run(document, binding):
        return {
            "verified": True,
            "role": role,
            "receipt_schema": schema,
            **binding,
            "verifier_id": role + "-verifier-v1",
            "proof_digest": role + "-proof-digest",
        }
    return run


def request():
    return make_request(
        mission_id="mission-1",
        capsule_head_sha256="c" * 64,
        action_ref="a1",
        effect_kind="REPO_WRITE",
        resource="canonical/x.json",
        operation="create",
        payload={"x": 1},
    )


def refs(root, auth_schema="AUTH_V1", comp_schema="COMP_V1"):
    a = write_receipt(root, "canonical/verification/a.json", auth_schema)
    c = write_receipt(root, "canonical/verification/c.json", comp_schema)
    a.update({
        "scope_complete": True,
        "allow_implies_zero_critical_authority_violation": True,
        "independent_or_objective": True,
    })
    c.update({
        "scope_complete": True,
        "state_and_provenance_invariants_hold": True,
        "independent_or_objective": True,
    })
    return a, c


class FinalAuthorizerTests(unittest.TestCase):
    def test_unknown_semantics_deny_after_valid_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            req = request()
            a, c = refs(td)
            grant = make_grant(
                request=req,
                authority_receipt=a,
                composition_receipt=c,
                max_payload_bytes=1000,
            )
            out = authorize_effect(req, grant, repo_root=td)
            self.assertFalse(out["allowed"])
            self.assertEqual(out["failed_stage"], "SEMANTIC_VERIFICATION")

    def test_missing_receipt_denies_at_byte_layer(self):
        with tempfile.TemporaryDirectory() as td:
            req = request()
            a, c = refs(td)
            a["path"] = "canonical/verification/missing.json"
            grant = make_grant(
                request=req,
                authority_receipt=a,
                composition_receipt=c,
                max_payload_bytes=1000,
            )
            out = authorize_effect(req, grant, repo_root=td)
            self.assertFalse(out["allowed"])
            self.assertEqual(out["failed_stage"], "RECEIPT_BYTE_IDENTITY")

    def test_tampered_grant_denies_before_receipt_reads(self):
        with tempfile.TemporaryDirectory() as td:
            req = request()
            a, c = refs(td)
            grant = make_grant(
                request=req,
                authority_receipt=a,
                composition_receipt=c,
                max_payload_bytes=1000,
            )
            grant["resource"] = "evil"
            out = authorize_effect(req, grant, repo_root=td)
            self.assertFalse(out["allowed"])
            self.assertEqual(out["failed_stage"], "STRUCTURAL_ADMISSION")

    def test_all_three_layers_required_for_final_allow(self):
        with tempfile.TemporaryDirectory() as td:
            req = request()
            a, c = refs(td)
            grant = make_grant(
                request=req,
                authority_receipt=a,
                composition_receipt=c,
                max_payload_bytes=1000,
            )
            reg = {
                ("authority", "AUTH_V1"): verifier("authority", "AUTH_V1"),
                ("composition", "COMP_V1"): verifier("composition", "COMP_V1"),
            }
            with patch.object(semantic_gate, "BUILTIN_VERIFIERS", reg):
                out = authorize_effect(req, grant, repo_root=td)
            self.assertTrue(out["allowed"])
            self.assertEqual(out["status"], "ALLOW_FINAL_AUTHORIZATION")
            self.assertTrue(
                out["effect_carrier_atomic_enforcement_still_required"]
            )


if __name__ == "__main__":
    unittest.main()
