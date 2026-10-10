from __future__ import annotations
from copy import deepcopy
import unittest

from canonical.runtime.coverage_claim_scope_guard_v1 import compute_claim_id
from canonical.runtime import coverage_root_certificate_registry_guard_v2 as v2

AUTH_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
AUTH_PATH="canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"
OBJECTIVE="BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE"

def pointer():
    return {
        "schema":"PROJECT_BRAIN_CURRENT_MISSION_OBJECTIVE_POINTER_V1",
        "status":"ACTIVE",
        "authoritative_source":{"path":AUTH_PATH},
        "real_objective":OBJECTIVE,
        "arbitrary_currentness":{"n":1},
    }

def authority():
    return {
        "schema":"PROJECT_BRAIN_REAL_MISSION_OBJECTIVE_V1",
        "status":"ACTIVE_CANONICAL_MISSION_OBJECTIVE_OVERRIDE",
        "real_objective":OBJECTIVE,
    }

def claim(mission_blob=AUTH_BLOB, **overrides):
    c={
        "claim_kind":"PROPERTY_CERTIFICATE",
        "mission_blob_sha":mission_blob,
        "scope_sha256":"1"*64,
        "target_predicate_sha256":"2"*64,
        "semantics_sha256":"3"*64,
        "epoch":"TEST_STABLE_AUTHORITY_EPOCH",
        "authority_id":"TEST_STABLE_AUTHORITY",
        "terminal_credit_delta":0,
    }
    c.update(overrides)
    c["claim_id"]=compute_claim_id(c)
    return c

def slot(root_id,c):
    return {
        "root_id":root_id,
        "status":"PROVED_CURRENT",
        "certificate":{
            "root_id":root_id,
            "mission_authority_blob_sha":AUTH_BLOB,
            "path":f"canonical/governance/{root_id}.json",
            "git_blob_sha":"a"*40,
            "claim_binding":{k:c[k] for k in ("claim_id","claim_kind","mission_blob_sha","scope_sha256","target_predicate_sha256","semantics_sha256","epoch","authority_id")},
        },
        "semantic_verifier":{"path":f"canonical/runtime/{root_id}.py","git_blob_sha":"b"*40},
        "independent_verification":{"path":f"canonical/verification/{root_id}.json","git_blob_sha":"c"*40,"claim_id":c["claim_id"]},
    }

def registry(c=None,proved=()):
    ids=list(v2.CERTIFICATE_ROOT_IDS)
    slots=[]
    for rid in ids:
        if rid in proved:
            slots.append(slot(rid,c))
        else:
            slots.append({"root_id":rid,"status":"OPEN_NO_GLOBAL_CERTIFICATE_BOUND","certificate":None,"semantic_verifier":None,"independent_verification":None})
    return {
        "schema":v2.SCHEMA,
        "namespace":v2.NAMESPACE,
        "mission_binding":{
            "pointer_path":"canonical/governance/CURRENT_MISSION_OBJECTIVE.json",
            "authority_path":AUTH_PATH,
            "authority_git_blob_sha":AUTH_BLOB,
            "real_objective":OBJECTIVE,
        },
        "root_identities":[
            {"canonical_id":rid,"display_alias":alias,"claim":text}
            for rid,alias,text in v2.ROOTS
        ],
        "certificate_slots":slots,
        "alias_policy":{
            "short_aliases_are_display_only":True,
            "short_aliases_have_zero_cross_artifact_authority":True,
            "cross_artifact_binding_requires_namespace_and_canonical_id":True,
        },
        "currently_proved_root_certificates":len(proved),
        "currently_open_root_certificates":3-len(proved),
        "r4_proof_closure":len(proved)==3,
        "active_claim":c,
        "accounting":{"terminal_credit_delta":0},
    }

class Tests(unittest.TestCase):
    def test_open_registry_passes_without_active_claim(self):
        o=v2.validate(registry(),current_mission_pointer=pointer(),current_mission_authority=authority(),current_mission_authority_blob_sha=AUTH_BLOB)
        self.assertTrue(o["pass"],o)
        self.assertEqual(len(o["open_root_ids"]),3)
        self.assertFalse(o["r4_proof_closure"])

    def test_stable_claim_and_one_proved_slot_pass(self):
        c=claim()
        o=v2.validate(registry(c,(v2.CERTIFICATE_ROOT_IDS[0],)),current_mission_pointer=pointer(),current_mission_authority=authority(),current_mission_authority_blob_sha=AUTH_BLOB)
        self.assertTrue(o["pass"],o)
        self.assertEqual(o["proved_root_ids"],[v2.CERTIFICATE_ROOT_IDS[0]])

    def test_pointer_bookkeeping_drift_does_not_stale_claim(self):
        c=claim(); p1=pointer(); p2=deepcopy(p1); p2["arbitrary_currentness"]={"n":999,"new":"field"}
        a=authority(); d=registry(c,(v2.CERTIFICATE_ROOT_IDS[0],))
        self.assertTrue(v2.validate(d,current_mission_pointer=p1,current_mission_authority=a,current_mission_authority_blob_sha=AUTH_BLOB)["pass"])
        self.assertTrue(v2.validate(d,current_mission_pointer=p2,current_mission_authority=a,current_mission_authority_blob_sha=AUTH_BLOB)["pass"])

    def test_old_mutable_pointer_blob_claim_fails(self):
        c=claim("6ab2147306a138f9ea327d8e19cb4a5bc76e89df")
        o=v2.validate(registry(c),current_mission_pointer=pointer(),current_mission_authority=authority(),current_mission_authority_blob_sha=AUTH_BLOB)
        self.assertFalse(o["pass"])
        self.assertTrue(any("MISSION_AUTHORITY_BINDING_STALE" in x for x in o["errors"]))

    def test_pointer_objective_drift_fails(self):
        p=pointer();p["real_objective"]="WEAKER"
        o=v2.validate(registry(),current_mission_pointer=p,current_mission_authority=authority(),current_mission_authority_blob_sha=AUTH_BLOB)
        self.assertFalse(o["pass"])
        self.assertIn("CURRENT_POINTER_OBJECTIVE_DRIFT",o["errors"])

    def test_wrong_claim_binding_in_certificate_fails(self):
        c=claim();d=registry(c,(v2.CERTIFICATE_ROOT_IDS[0],))
        d["certificate_slots"][0]["certificate"]["claim_binding"]["scope_sha256"]="4"*64
        o=v2.validate(d,current_mission_pointer=pointer(),current_mission_authority=authority(),current_mission_authority_blob_sha=AUTH_BLOB)
        self.assertFalse(o["pass"])
        self.assertTrue(any(x.startswith("PROVED_SLOT_CLAIM_BINDING_MISMATCH") for x in o["errors"]))

    def test_all_three_proved_closes_r4_proof_gate_only(self):
        c=claim();d=registry(c,tuple(v2.CERTIFICATE_ROOT_IDS))
        o=v2.validate(d,current_mission_pointer=pointer(),current_mission_authority=authority(),current_mission_authority_blob_sha=AUTH_BLOB)
        self.assertTrue(o["pass"],o)
        self.assertTrue(o["r4_proof_closure"])
        self.assertEqual(o["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
