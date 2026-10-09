import hashlib,json,unittest
from canonical.runtime.semantic_hypothesis_completeness_v1 import (
    CLOSURE,UNIVERSE_SCHEMA,compile_universe,
)
from canonical.runtime.semantic_ambiguity_control_v1 import decide

def sha(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def universe(signatures=None,observations=None):
    signatures=signatures or [("a",{"action":"SAME"}),("b",{"action":"SAME"})]
    return {
        "schema":UNIVERSE_SCHEMA,
        "universe_id":"u1",
        "scope_id":"finance:bounded-source",
        "closure_statement":CLOSURE,
        "terminal_signature_keys":["action"],
        "interpretations":[{"world_id":wid,"terminal_signature":sig} for wid,sig in signatures],
        "observations":observations or [],
    }

class Tests(unittest.TestCase):
    def test_closed_manifest_compiles_complete_frontier(self):
        u=universe()
        out=compile_universe(u,expected_manifest_sha256=sha(u))
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["frontier_problem"]["hypothesis_set_complete"])
        self.assertEqual(len(out["frontier_problem"]["worlds"]),2)
        self.assertEqual(out["completeness_authority"],"SOURCE_BOUND_CLOSED_ENUMERATION")
        self.assertFalse(out["global_semantic_completeness_claimed"])

    def test_manifest_digest_drift_fails_closed(self):
        out=compile_universe(universe(),expected_manifest_sha256="0"*64)
        self.assertFalse(out["pass"])
        self.assertIn("MANIFEST_SHA256_MISMATCH",out["reason"])

    def test_terminal_signature_key_set_must_be_complete(self):
        u=universe()
        u["interpretations"][1]["terminal_signature"]={"other":"SAME"}
        out=compile_universe(u,expected_manifest_sha256=sha(u))
        self.assertFalse(out["pass"])
        self.assertIn("TERMINAL_SIGNATURE_INCOMPLETE",out["reason"])

    def test_observation_outcome_domain_must_cover_all_worlds(self):
        u=universe(observations=[{"observation_id":"x","cost_units":1,"outcomes":{"a":"A"}}])
        out=compile_universe(u,expected_manifest_sha256=sha(u))
        self.assertFalse(out["pass"])
        self.assertIn("OBSERVATION_DOMAIN_INCOMPLETE",out["reason"])

    def test_manifest_path_skips_irrelevant_disambiguation(self):
        u=universe()
        out=decide({
            "ambiguity_owner":"USER_INTENT",
            "closed_hypothesis_universe":u,
            "expected_manifest_sha256":sha(u),
        })
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["action"],"CONTINUE_WITHOUT_DISAMBIGUATION")

    def test_manifest_path_finds_minimum_discriminator(self):
        u=universe(
            signatures=[("a",{"action":"A"}),("b",{"action":"B"})],
            observations=[{"observation_id":"cheap","cost_units":1,"outcomes":{"a":"x","b":"y"}}],
        )
        out=decide({
            "ambiguity_owner":"EXTERNAL_WORLD",
            "closed_hypothesis_universe":u,
            "expected_manifest_sha256":sha(u),
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["action"],"ACQUIRE_MINIMUM_TERMINALLY_RELEVANT_DISCRIMINATOR")
        self.assertEqual(out["next_observation_id"],"cheap")

    def test_manifest_distinct_user_intent_without_separator_asks_minimally(self):
        u=universe(signatures=[("a",{"action":"A"}),("b",{"action":"B"})])
        out=decide({
            "ambiguity_owner":"USER_INTENT",
            "closed_hypothesis_universe":u,
            "expected_manifest_sha256":sha(u),
        })
        self.assertFalse(out["pass"])
        self.assertTrue(out["ask_user_required"])
        self.assertEqual(out["action"],"ASK_USER_MINIMUM_CLARIFICATION")

    def test_direct_and_manifest_authorities_conflict(self):
        u=universe()
        out=decide({
            "ambiguity_owner":"USER_INTENT",
            "closed_hypothesis_universe":u,
            "expected_manifest_sha256":sha(u),
            "hypothesis_set_complete":True,
            "worlds":[],
            "observations":[],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED__AMBIGUITY_COMPLETENESS_AUTHORITY_CONFLICT")

if __name__=="__main__":
    unittest.main(verbosity=2)
