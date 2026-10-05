import copy
import unittest

import canonical.runtime.effect_broker_semantic_gate_v1 as gate
from canonical.runtime.effect_broker_contract_v1 import make_request

AUTH_SCHEMA="PROJECT_BRAIN_DECLARED_ARTIFACT_AUTHORITY_RECEIPT_V1"
COMP_SCHEMA="PROJECT_BRAIN_DECLARED_ARTIFACT_COMPOSITION_RECEIPT_V1"

def descriptor(path="canonical/astra_runtime/artifacts/result.txt"):
    return {
        "schema":"PROJECT_BRAIN_DECLARED_ARTIFACT_DESCRIPTOR_V1",
        "destination_path":path,
        "artifact_sha256":"a"*64,
        "artifact_bytes":12,
        "expected_pre_sha256":"ABSENT",
        "content_type":"text/plain",
        "producer_sha256":"b"*64,
        "toolchain_sha256":"c"*64,
    }

def request(desc=None):
    d=descriptor() if desc is None else desc
    return make_request(
        mission_id="m1",
        capsule_head_sha256="d"*64,
        action_ref="declared-artifact-finalizer:test",
        effect_kind="FINAL_OUTPUT",
        resource="artifact:"+d["destination_path"],
        operation="replace",
        payload=d,
    )

def resolved(document):
    return {"path":"x","git_blob_sha":"a"*40,"document":document}

AUTH_DOC={
    "schema":AUTH_SCHEMA,
    "policy_id":"DECLARED_ARTIFACT_FINAL_OUTPUT_V1",
    "effect_kind":"FINAL_OUTPUT",
    "operation":"replace",
    "artifact_root":"canonical/astra_runtime/artifacts",
    "max_artifact_bytes":536870912,
    "scope_complete":True,
    "allow_implies_zero_critical_authority_violation":True,
    "independent_or_objective":True,
}
COMP_DOC={
    "schema":COMP_SCHEMA,
    "policy_id":"DECLARED_ARTIFACT_FINAL_OUTPUT_V1",
    "descriptor_schema":"PROJECT_BRAIN_DECLARED_ARTIFACT_DESCRIPTOR_V1",
    "state_and_provenance_invariants_hold":True,
    "scope_complete":True,
    "independent_or_objective":True,
}

class DeclaredArtifactSemanticPolicyTests(unittest.TestCase):
    def authorize(self, req, auth=AUTH_DOC, comp=COMP_DOC):
        return gate.authorize_semantics(
            request=req,
            resolved_authority_receipt=resolved(auth),
            resolved_composition_receipt=resolved(comp),
        )

    def test_exact_declared_artifact_request_allows(self):
        out=self.authorize(request())
        self.assertTrue(out["allowed"],out)

    def test_path_escape_denies(self):
        d=descriptor("../escape.txt")
        out=self.authorize(request(d))
        self.assertFalse(out["allowed"])

    def test_resource_descriptor_mismatch_denies(self):
        req=request()
        req=dict(req)
        req["resource"]="artifact:canonical/astra_runtime/artifacts/other.txt"
        out=self.authorize(req)
        self.assertFalse(out["allowed"])

    def test_payload_tamper_denies(self):
        req=request()
        req=copy.deepcopy(req)
        req["payload"]["artifact_bytes"]=999
        out=self.authorize(req)
        self.assertFalse(out["allowed"])

    def test_broadened_authority_receipt_denies(self):
        auth=dict(AUTH_DOC)
        auth["artifact_root"]="canonical"
        out=self.authorize(request(),auth=auth)
        self.assertFalse(out["allowed"])

    def test_generic_repo_write_stays_denied(self):
        req=make_request(
            mission_id="m1",
            capsule_head_sha256="d"*64,
            action_ref="x",
            effect_kind="REPO_WRITE",
            resource="canonical/x",
            operation="replace",
            payload={"x":1},
        )
        out=self.authorize(req)
        self.assertFalse(out["allowed"])

if __name__=="__main__":
    unittest.main(verbosity=2)
