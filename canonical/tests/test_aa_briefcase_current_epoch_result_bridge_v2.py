import unittest
from canonical.runtime.aa_briefcase_current_epoch_result_bridge_v2 import BridgeError,PREDICATES,compile_current_epoch_bridge

def target():
    return {"schema":"PROJECT_BRAIN_AA_BRIEFCASE_OPUS55_CURRENT_OWNER_TARGET_V1","target":{"benchmark":"AA-Briefcase v1.1","model":"Claude Opus 5.5 (Max, Default Fallback)","current_owner_elo":1807,"observed_date":"2026-10-07"},"epoch_rule":{"current_epoch_minimum_opus55_target_elo":1807}}

def result(**o):
    x={"schema":"X","status":"VERIFIED_COMPARABLE_BRAIN_SCORE","independent_or_owner_verified":True,"benchmark":"AA-Briefcase v1.1","model":"Claude Opus 5.5 (Max, Default Fallback)","unit":"Elo","brain_score":1807,"subject_sha256":"a"*64,"matched_current_owner_epoch":True,"target_observed_date":"2026-10-07","opus55_reference_score":1807}; x.update(o); return x

class T(unittest.TestCase):
    def test_pass(self):
        out=compile_current_epoch_bridge(target(),result()); self.assertEqual(out["predicate_results"],{p:True for p in PREDICATES}); self.assertEqual(out["opus55_reference_score"],1807.0); self.assertTrue(out["historical_1822_predicate_ids_preserved"]); self.assertFalse(out["historical_epoch_rewritten"])
    def test_below(self): self.assertFalse(any(compile_current_epoch_bridge(target(),result(brain_score=1806.9))["predicate_results"].values()))
    def test_stale_epoch(self):
        with self.assertRaisesRegex(BridgeError,"RESULT_TARGET_DATE_MISMATCH"): compile_current_epoch_bridge(target(),result(target_observed_date="2026-09-22"))
    def test_unverified(self):
        with self.assertRaisesRegex(BridgeError,"RESULT_NOT_INDEPENDENT_OR_OWNER_VERIFIED"): compile_current_epoch_bridge(target(),result(independent_or_owner_verified=False))
    def test_reference_drift(self):
        with self.assertRaisesRegex(BridgeError,"RESULT_REFERENCE_MISMATCH"): compile_current_epoch_bridge(target(),result(opus55_reference_score=1808))
    def test_target_drift(self):
        x=target(); x["epoch_rule"]["current_epoch_minimum_opus55_target_elo"]=1808
        with self.assertRaisesRegex(BridgeError,"TARGET_EPOCH_REFERENCE_DRIFT"): compile_current_epoch_bridge(x,result())
