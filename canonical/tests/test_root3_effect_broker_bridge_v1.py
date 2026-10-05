from __future__ import annotations

import copy
import json
import unittest

from canonical.runtime import effect_broker_contract_v1 as generic
from canonical.runtime import root3_effect_broker_bridge_v1 as bridge
from canonical.runtime import root3_proof_carrying_effect_v1 as root3
from canonical.runtime.zero_ambient_authority_launcher_v1 import parse_effect_requests

HEAD = "a" * 64
POST = "c" * 64
BLOB = "b" * 40
EPOCH = "epoch-1"


def broker_receipts():
    return (
        {
            "path": "canonical/verification/authority.json",
            "git_blob_sha": BLOB,
            "scope_complete": True,
            "allow_implies_zero_critical_authority_violation": True,
            "independent_or_objective": True,
        },
        {
            "path": "canonical/verification/composition.json",
            "git_blob_sha": BLOB,
            "scope_complete": True,
            "state_and_provenance_invariants_hold": True,
            "independent_or_objective": True,
        },
    )


def fixture(effect_kind="REPO_WRITE", effect_class="durable_write"):
    req = generic.make_request(
        mission_id="m1",
        capsule_head_sha256=HEAD,
        action_ref="a1",
        effect_kind=effect_kind,
        resource="canonical/out.json",
        operation="atomic_replace",
        payload={"x": 1},
    )
    authority_receipt, composition_receipt = broker_receipts()
    grant = generic.make_grant(
        request=req,
        authority_receipt=authority_receipt,
        composition_receipt=composition_receipt,
        max_payload_bytes=1000,
    )
    rr = {
        "schema": root3.REQUEST_SCHEMA,
        "subject": "worker:m1",
        "authority_epoch": EPOCH,
        "effect_class": effect_class,
        "resource": req["resource"],
        "operation": req["operation"],
        "scope": "canonical",
        "payload_sha256": req["payload_sha256"],
        "provenance_refs": [
            "effect_request_sha256:" + req["request_sha256"],
            "mission_id:" + req["mission_id"],
            "action_ref:" + req["action_ref"],
        ],
    }
    if effect_class in {"state_append", "evidence_append", "final_output"}:
        rr.update(
            {
                "pre_state_sha256": HEAD,
                "post_state_sha256": POST,
                "invariant_receipt": {
                    "path": "canonical/verification/invariant.json",
                    "git_blob_sha": BLOB,
                    "cross_component_state_preserved": True,
                    "evidence_provenance_complete": True,
                    "zero_critical_composition_failures": True,
                    "independent_or_objective": True,
                },
            }
        )
    policy = {
        "schema": root3.POLICY_SCHEMA,
        "authority_epoch": EPOCH,
        "rules": [
            {
                "subject": rr["subject"],
                "effect_class": rr["effect_class"],
                "resource": rr["resource"],
                "operation": rr["operation"],
                "scope": rr["scope"],
            }
        ],
    }
    envelope = {
        "type": bridge.ENVELOPE_TYPE,
        "request_id": req["request_sha256"],
        "effect_request": req,
        "root3_request": rr,
    }
    return envelope, grant, policy


class Tests(unittest.TestCase):
    def test_launcher_to_broker_to_root3_structural_path_passes(self):
        envelope, grant, policy = fixture()
        stdout = (
            "ordinary output\nPROJECT_BRAIN_EFFECT_REQUEST_V1:"
            + json.dumps(envelope, sort_keys=True)
            + "\n"
        )
        parsed = parse_effect_requests(stdout)
        self.assertEqual(len(parsed), 1)
        verdict = bridge.admit(parsed[0], grant, policy)
        self.assertEqual(verdict["status"], "PASS_STRUCTURAL_BRIDGED_PRECOMMIT")
        self.assertTrue(verdict["launcher_envelope_bound"])
        self.assertTrue(verdict["effect_broker_bound"])
        self.assertTrue(verdict["root3_guard_bound"])
        self.assertEqual(verdict["material_effects_committed"], 0)
        self.assertFalse(verdict["execution_authority"])

    def test_final_output_binds_composition_pre_state(self):
        envelope, grant, policy = fixture("FINAL_OUTPUT", "final_output")
        verdict = bridge.admit(envelope, grant, policy)
        self.assertEqual(verdict["status"], "PASS_STRUCTURAL_BRIDGED_PRECOMMIT")
        self.assertTrue(verdict["cross_contract"]["composition_pre_state_bound"])

    def test_payload_cross_contract_mismatch_fails_closed(self):
        envelope, grant, policy = fixture()
        envelope = copy.deepcopy(envelope)
        envelope["root3_request"]["payload_sha256"] = "0" * 64
        verdict = bridge.admit(envelope, grant, policy)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("PAYLOAD_SHA256_MISMATCH", verdict["reason"])

    def test_incompatible_effect_class_fails_closed(self):
        envelope, grant, policy = fixture()
        envelope = copy.deepcopy(envelope)
        envelope["root3_request"]["effect_class"] = "network_request"
        policy = copy.deepcopy(policy)
        policy["rules"][0]["effect_class"] = "network_request"
        verdict = bridge.admit(envelope, grant, policy)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("EFFECT_CLASS_INCOMPATIBLE", verdict["reason"])

    def test_missing_cross_provenance_binding_fails_closed(self):
        envelope, grant, policy = fixture()
        envelope = copy.deepcopy(envelope)
        envelope["root3_request"]["provenance_refs"] = [
            x
            for x in envelope["root3_request"]["provenance_refs"]
            if not x.startswith("effect_request_sha256:")
        ]
        verdict = bridge.admit(envelope, grant, policy)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("PROVENANCE_BINDING_MISSING", verdict["reason"])

    def test_composition_pre_state_mismatch_fails_closed(self):
        envelope, grant, policy = fixture("FINAL_OUTPUT", "final_output")
        envelope = copy.deepcopy(envelope)
        envelope["root3_request"]["pre_state_sha256"] = "d" * 64
        verdict = bridge.admit(envelope, grant, policy)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("PRE_STATE_MISMATCH", verdict["reason"])

    def test_broker_grant_tamper_fails_closed(self):
        envelope, grant, policy = fixture()
        grant = copy.deepcopy(grant)
        grant["grant_sha256"] = "0" * 64
        verdict = bridge.admit(envelope, grant, policy)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("EFFECT_BROKER_DENIED", verdict["reason"])

    def test_root3_policy_tamper_fails_closed(self):
        envelope, grant, policy = fixture()
        policy = copy.deepcopy(policy)
        policy["authority_epoch"] = "wrong"
        verdict = bridge.admit(envelope, grant, policy)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("ROOT3_GUARD_DENIED", verdict["reason"])

    def test_request_id_must_be_exact_generic_request_digest(self):
        envelope, grant, policy = fixture()
        envelope = copy.deepcopy(envelope)
        envelope["request_id"] = "not-the-request-digest"
        verdict = bridge.admit(envelope, grant, policy)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("REQUEST_ID_NOT_EXACT_EFFECT_REQUEST_SHA256", verdict["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
