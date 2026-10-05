import pathlib
import unittest

from canonical.runtime.effect_broker_contract_v1 import make_grant
from canonical.runtime import root3_declared_artifact_finalizer_v1 as finalizer

ROOT=pathlib.Path(__file__).resolve().parents[2]
AUTH_PATH="canonical/verification/DECLARED_ARTIFACT_AUTHORITY_RECEIPT_20261005_V1.json"
AUTH_SHA="12ba23e0f071c46fd931dcc9734ff63025ef165c"
COMP_PATH="canonical/verification/DECLARED_ARTIFACT_COMPOSITION_RECEIPT_20261005_V1.json"
COMP_SHA="10974b543f9d550ac3afdbe6d0dfade6b4adce62"

def refs():
    return (
        {
            "path":AUTH_PATH,
            "git_blob_sha":AUTH_SHA,
            "scope_complete":True,
            "allow_implies_zero_critical_authority_violation":True,
            "independent_or_objective":True,
        },
        {
            "path":COMP_PATH,
            "git_blob_sha":COMP_SHA,
            "scope_complete":True,
            "state_and_provenance_invariants_hold":True,
            "independent_or_objective":True,
        },
    )

def plan_and_payload(name="semantic-policy-fullstack.txt"):
    payload=b"declared artifact semantic policy full stack\n"
    plan=finalizer.build_plan(
        mission_id="semantic-policy-test",
        capsule_head_sha256="d"*64,
        action_ref="declared-artifact-finalizer:full-stack",
        destination_path="canonical/astra_runtime/artifacts/"+name,
        payload=payload,
        expected_pre_sha256="ABSENT",
        content_type="text/plain",
        producer_sha256="b"*64,
        toolchain_sha256="c"*64,
    )
    return plan,payload

class DeclaredArtifactSemanticFullStackTests(unittest.TestCase):
    def setUp(self):
        (ROOT/"canonical/astra_runtime/artifacts").mkdir(parents=True,exist_ok=True)

    def tearDown(self):
        for name in ("semantic-policy-fullstack.txt","semantic-policy-badreceipt.txt"):
            p=ROOT/"canonical/astra_runtime/artifacts"/name
            if p.exists():
                p.unlink()

    def test_real_content_addressed_receipts_allow_exact_finalizer_commit(self):
        plan,payload=plan_and_payload()
        req=finalizer.effect_request(plan,payload)
        auth,comp=refs()
        grant=make_grant(
            request=req,
            authority_receipt=auth,
            composition_receipt=comp,
            max_payload_bytes=8_000_000,
        )
        receipt=finalizer.commit(ROOT,plan,payload,grant)
        self.assertEqual(receipt["status"],"COMMITTED")
        self.assertTrue(receipt["atomic_replace"])
        self.assertTrue(receipt["exact_readback"])
        target=ROOT/"canonical/astra_runtime/artifacts/semantic-policy-fullstack.txt"
        self.assertEqual(target.read_bytes(),payload)

    def test_wrong_receipt_blob_denies_before_mutation(self):
        plan,payload=plan_and_payload("semantic-policy-badreceipt.txt")
        req=finalizer.effect_request(plan,payload)
        auth,comp=refs()
        auth=dict(auth)
        auth["git_blob_sha"]="0"*40
        grant=make_grant(
            request=req,
            authority_receipt=auth,
            composition_receipt=comp,
            max_payload_bytes=8_000_000,
        )
        with self.assertRaisesRegex(finalizer.ArtifactFinalizeDenied,"FINAL_AUTHORIZATION_DENIED"):
            finalizer.commit(ROOT,plan,payload,grant)
        self.assertFalse((ROOT/"canonical/astra_runtime/artifacts/semantic-policy-badreceipt.txt").exists())

if __name__=="__main__":
    unittest.main(verbosity=2)
