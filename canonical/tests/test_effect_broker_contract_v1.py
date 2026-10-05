from __future__ import annotations
import copy
import unittest

from canonical.runtime.effect_broker_contract_v1 import make_request, make_grant, admit

HEAD="a"*64
BLOB="b"*40


def receipts():
    return (
        {
            "path":"canonical/verification/authority.json",
            "git_blob_sha":BLOB,
            "scope_complete":True,
            "allow_implies_zero_critical_authority_violation":True,
            "independent_or_objective":True,
        },
        {
            "path":"canonical/verification/composition.json",
            "git_blob_sha":BLOB,
            "scope_complete":True,
            "state_and_provenance_invariants_hold":True,
            "independent_or_objective":True,
        },
    )


def fixture():
    req=make_request(
        mission_id="m1",
        capsule_head_sha256=HEAD,
        action_ref="a1",
        effect_kind="REPO_WRITE",
        resource="canonical/out.json",
        operation="atomic_replace",
        payload={"x":1},
    )
    ar,cr=receipts()
    grant=make_grant(
        request=req,
        authority_receipt=ar,
        composition_receipt=cr,
        max_payload_bytes=1000,
    )
    return req,grant


class Tests(unittest.TestCase):
    def test_exact_pair_allows(self):
        req,grant=fixture()
        self.assertEqual(admit(req,grant)["status"],"ALLOW_PRECOMMIT")

    def test_payload_tamper_denied(self):
        req,grant=fixture()
        req=copy.deepcopy(req)
        req["payload"]["x"]=2
        self.assertEqual(admit(req,grant)["status"],"DENY_FAIL_CLOSED")

    def test_resource_tamper_denied(self):
        req,grant=fixture()
        req=copy.deepcopy(req)
        req["resource"]="canonical/other.json"
        self.assertEqual(admit(req,grant)["status"],"DENY_FAIL_CLOSED")

    def test_grant_hash_tamper_denied(self):
        req,grant=fixture()
        grant=copy.deepcopy(grant)
        grant["grant_sha256"]="0"*64
        self.assertEqual(admit(req,grant)["status"],"DENY_FAIL_CLOSED")

    def test_receipt_flag_tamper_denied(self):
        req,grant=fixture()
        grant=copy.deepcopy(grant)
        grant["authority_receipt"]["scope_complete"]=False
        self.assertEqual(admit(req,grant)["status"],"DENY_FAIL_CLOSED")

    def test_state_head_mismatch_denied(self):
        req,grant=fixture()
        req2=make_request(
            mission_id="m1",
            capsule_head_sha256="c"*64,
            action_ref="a1",
            effect_kind="REPO_WRITE",
            resource="canonical/out.json",
            operation="atomic_replace",
            payload={"x":1},
        )
        self.assertEqual(admit(req2,grant)["status"],"DENY_FAIL_CLOSED")

    def test_unbound_receipt_field_denied(self):
        req,grant=fixture()
        grant=copy.deepcopy(grant)
        grant["composition_receipt"]["surprise"]=True
        self.assertEqual(admit(req,grant)["status"],"DENY_FAIL_CLOSED")


if __name__=="__main__":
    unittest.main(verbosity=2)
