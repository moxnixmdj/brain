from __future__ import annotations
from copy import deepcopy
import unittest

from canonical.runtime.coverage_claim_scope_guard_v1 import compute_claim_id
from canonical.runtime import coverage_claim_scope_guard_v2 as v2

AUTH_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
AUTH_PATH="canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"
OBJECTIVE="BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE"

def pointer():
    return {
      "schema":"PROJECT_BRAIN_CURRENT_MISSION_OBJECTIVE_POINTER_V1",
      "status":"ACTIVE",
      "authoritative_source":{"path":AUTH_PATH},
      "real_objective":OBJECTIVE,
      "arbitrary_current_projection":{"counter":1},
    }

def authority():
    return {
      "schema":"PROJECT_BRAIN_REAL_MISSION_OBJECTIVE_V1",
      "status":"ACTIVE_CANONICAL_MISSION_OBJECTIVE_OVERRIDE",
      "real_objective":OBJECTIVE,
    }

def claim(mission_blob=AUTH_BLOB):
    c={
      "claim_kind":"PROPERTY_CERTIFICATE",
      "mission_blob_sha":mission_blob,
      "scope_sha256":"1"*64,
      "target_predicate_sha256":"2"*64,
      "semantics_sha256":"3"*64,
      "epoch":"TEST_EPOCH",
      "authority_id":"TEST_AUTHORITY",
      "terminal_credit_delta":0,
    }
    c["claim_id"]=compute_claim_id(c)
    return c

class MissionAuthorityClaimGuardV2Tests(unittest.TestCase):
    def test_stable_authority_survives_mutable_pointer_projection_change(self):
        p1=pointer(); p2=deepcopy(p1); p2["arbitrary_current_projection"]={"counter":999,"new":"state"}
        a=authority(); c=claim()
        self.assertTrue(v2.validate_claim(c,current_pointer=p1,mission_authority=a,mission_authority_blob_sha=AUTH_BLOB)["pass"])
        self.assertTrue(v2.validate_claim(c,current_pointer=p2,mission_authority=a,mission_authority_blob_sha=AUTH_BLOB)["pass"])

    def test_old_mutable_pointer_blob_is_not_accepted_as_mission_identity(self):
        out=v2.validate_claim(claim("51327d24f82809279e37e51cf3d994d13a6f1ff3"),current_pointer=pointer(),mission_authority=authority(),mission_authority_blob_sha=AUTH_BLOB)
        self.assertFalse(out["pass"]); self.assertIn("MISSION_AUTHORITY_BINDING_STALE",out["errors"])

    def test_authoritative_source_path_substitution_fails(self):
        p=pointer(); p["authoritative_source"]["path"]="canonical/governance/OTHER.json"
        out=v2.validate_claim(claim(),current_pointer=p,mission_authority=authority(),mission_authority_blob_sha=AUTH_BLOB)
        self.assertFalse(out["pass"]); self.assertIn("MISSION_AUTHORITY_PATH_DRIFT",out["errors"])

    def test_pointer_objective_drift_fails(self):
        p=pointer(); p["real_objective"]="WEAKER_OBJECTIVE"
        out=v2.validate_claim(claim(),current_pointer=p,mission_authority=authority(),mission_authority_blob_sha=AUTH_BLOB)
        self.assertFalse(out["pass"]); self.assertIn("CURRENT_POINTER_OBJECTIVE_DRIFT",out["errors"])

    def test_authority_objective_drift_fails(self):
        a=authority(); a["real_objective"]="WEAKER_OBJECTIVE"
        out=v2.validate_claim(claim(),current_pointer=pointer(),mission_authority=a,mission_authority_blob_sha=AUTH_BLOB)
        self.assertFalse(out["pass"]); self.assertIn("MISSION_AUTHORITY_OBJECTIVE_DRIFT",out["errors"])

    def test_claim_id_tamper_fails(self):
        c=claim(); c["claim_id"]="0"*64
        out=v2.validate_claim(c,current_pointer=pointer(),mission_authority=authority(),mission_authority_blob_sha=AUTH_BLOB)
        self.assertFalse(out["pass"]); self.assertIn("CLAIM_ID_MISMATCH",out["errors"])

    def test_nonzero_credit_fails(self):
        c=claim(); c["terminal_credit_delta"]=1; c["claim_id"]=compute_claim_id(c)
        out=v2.validate_claim(c,current_pointer=pointer(),mission_authority=authority(),mission_authority_blob_sha=AUTH_BLOB)
        self.assertFalse(out["pass"]); self.assertIn("NONZERO_CREDIT_FORBIDDEN",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
