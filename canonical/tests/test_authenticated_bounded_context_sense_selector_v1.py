from __future__ import annotations
import unittest

from canonical.runtime import authenticated_bounded_context_sense_selector_v1 as s

SCOPE="TEST_SCOPE"
CANDS=["C1","C2","C3"]

def candidate_verifier(req):
    return {
        "pass":True,
        "status":"PASS",
        "scope_id":SCOPE,
        "candidate_ids":list(CANDS),
        "candidate_universe_complete":True,
        "authority_sha256":"c"*64,
    }

def matrix_verifier(req):
    return {
        "pass":True,
        "status":"PASS",
        "scope_id":SCOPE,
        "semantic_truth_authority":True,
        "candidate_domain":list(CANDS),
        "outcome_maps_complete_relative_to_matrix_domain":True,
        "matrix_sha256":"m"*64,
        "observations":[
            {
                "observation_id":"O1",
                "cost_units":1,
                "outcomes":{"C1":"A","C2":"B","C3":"B"},
            },
            {
                "observation_id":"O2",
                "cost_units":2,
                "outcomes":{"C1":"X","C2":"Y","C3":"Z"},
            },
        ],
    }

def observation_verifier(req):
    oid=req.get("observation_id")
    if oid=="O1" and req.get("evidence")=="verified-A":
        return {
            "pass":True,"status":"PASS","scope_id":SCOPE,
            "semantic_truth_authority":True,
            "observation_id":"O1","observed_outcome":"A",
            "authority_sha256":"o1"*32,
        }
    if oid=="O1" and req.get("evidence")=="verified-B":
        return {
            "pass":True,"status":"PASS","scope_id":SCOPE,
            "semantic_truth_authority":True,
            "observation_id":"O1","observed_outcome":"B",
            "authority_sha256":"o1"*32,
        }
    if oid=="O2" and req.get("evidence")=="verified-Y":
        return {
            "pass":True,"status":"PASS","scope_id":SCOPE,
            "semantic_truth_authority":True,
            "observation_id":"O2","observed_outcome":"Y",
            "authority_sha256":"o2"*32,
        }
    return {
        "pass":False,"status":"OPEN__UNVERIFIED",
        "scope_id":SCOPE,"semantic_truth_authority":False,
    }

def resolve(obs=(),cand=candidate_verifier,mat=matrix_verifier,ov=observation_verifier):
    return s.resolve(
        candidate_universe_request={"ignored":"caller"},
        candidate_universe_verifier=cand,
        discriminator_matrix_request={"ignored":"caller"},
        discriminator_matrix_verifier=mat,
        observation_requests=list(obs),
        observation_verifier=ov,
    )

class Tests(unittest.TestCase):
    def test_verified_observation_can_select_unique_candidate(self):
        out=resolve([{"observation_id":"O1","evidence":"verified-A"}])
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["selected_candidate_id"],"C1")
        self.assertTrue(out["candidate_universe_complete"])
        self.assertTrue(out["bounded_selection_authority"])
        self.assertTrue(out["semantic_identity_authority"])
        self.assertFalse(out["global_identity_authority"])
        self.assertFalse(out["open_world_candidate_set_complete"])

    def test_without_observation_returns_minimum_next_discriminator(self):
        out=resolve()
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "OPEN__MINIMUM_AUTHENTICATED_CONTEXT_DISCRIMINATOR_REQUIRED",
        )
        self.assertEqual(out["next_observation_id"],"O2")
        self.assertEqual(out["minimum_worst_case_cost_units"],2.0)

    def test_partial_observation_then_returns_remaining_minimum_discriminator(self):
        out=resolve([{"observation_id":"O1","evidence":"verified-B"}])
        self.assertFalse(out["pass"],out)
        self.assertEqual(set(out["surviving_candidate_ids"]),{"C2","C3"})
        self.assertEqual(out["next_observation_id"],"O2")

    def test_unverified_forged_observation_never_narrows(self):
        out=resolve([{
            "observation_id":"O1",
            "evidence":"forged",
            "observed_outcome":"A",
            "semantic_truth_authority":True,
        }])
        self.assertFalse(out["pass"],out)
        self.assertEqual(set(out["surviving_candidate_ids"]),set(CANDS))
        self.assertEqual(out["next_observation_id"],"O2")

    def test_incomplete_candidate_universe_fails_closed(self):
        def bad(req):
            row=candidate_verifier(req)
            row["candidate_universe_complete"]=False
            return row
        out=resolve(cand=bad)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("CANDIDATE_UNIVERSE_COMPLETENESS_UNPROVED",out["reason"])

    def test_matrix_domain_mismatch_fails_closed(self):
        def bad(req):
            row=matrix_verifier(req)
            row["candidate_domain"]=["C1","C2"]
            row["observations"]=[
                {"observation_id":"O1","outcomes":{"C1":"A","C2":"B"}}
            ]
            return row
        out=resolve(mat=bad)
        self.assertFalse(out["pass"])
        self.assertIn("MATRIX_DOMAIN_MISMATCH",out["reason"])

    def test_matrix_scope_mismatch_fails_closed(self):
        def bad(req):
            row=matrix_verifier(req); row["scope_id"]="OTHER"; return row
        out=resolve(mat=bad)
        self.assertFalse(out["pass"])
        self.assertIn("MATRIX_SCOPE_MISMATCH",out["reason"])

    def test_observation_scope_mismatch_fails_closed(self):
        def bad(req):
            row=observation_verifier(req)
            if row.get("pass") is True: row["scope_id"]="OTHER"
            return row
        out=resolve([{"observation_id":"O1","evidence":"verified-A"}],ov=bad)
        self.assertFalse(out["pass"])
        self.assertIn("OBSERVATION_SCOPE_MISMATCH",out["reason"])

    def test_conflicting_verified_observations_fail_closed(self):
        def conflict(req):
            if req["observation_id"]=="O1":
                return {
                    "pass":True,"status":"PASS","scope_id":SCOPE,
                    "semantic_truth_authority":True,
                    "observation_id":"O1","observed_outcome":"A",
                    "authority_sha256":"1"*64,
                }
            return {
                "pass":True,"status":"PASS","scope_id":SCOPE,
                "semantic_truth_authority":True,
                "observation_id":"O2","observed_outcome":"Y",
                "authority_sha256":"2"*64,
            }
        out=resolve(
            [{"observation_id":"O1"},{"observation_id":"O2"}],
            ov=conflict,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("AUTHENTICATED_OBSERVATIONS_CONTRADICT",out["reason"])

    def test_no_open_world_or_terminal_authority(self):
        out=resolve([{"observation_id":"O1","evidence":"verified-A"}])
        self.assertTrue(out["pass"])
        self.assertFalse(out["global_identity_authority"])
        self.assertFalse(out["open_world_candidate_set_complete"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
