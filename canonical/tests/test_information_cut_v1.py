from __future__ import annotations
import unittest
from canonical.runtime.terminal_information_cut_compiler_v1 import SCHEMA,compile_cut
H="a"*40
def row(i,c,r=0,v=1,k="EXISTING_PROOF_REUSE"):
    return {"id":i,"action_class":k,"covers":c,
      "cost":{"new_reality_units":r,"capability_acquisition_units":0,"verification_units":v},
      "feasibility_receipt":{"path":"canonical/verification/"+i+".json","git_blob_sha":H,"status":"INDEPENDENT_PUBLIC_RUNNER_PASS","independent":True}}
class T(unittest.TestCase):
    def test_one_shared_observation_beats_three(self):
        d={"schema":SCHEMA,"primitive_facts":["P1","P2","P3"],"actions":[row("S1",["P1"],1,k="SAFE_OBSERVATION"),row("S2",["P2"],1,k="SAFE_OBSERVATION"),row("S3",["P3"],1,k="SAFE_OBSERVATION"),row("ONE",["P1","P2","P3"],1,k="SAFE_OBSERVATION")]}
        o=compile_cut(d); self.assertEqual(o["selected_actions"],["ONE"]); self.assertEqual(o["objective"]["new_reality_units"],1)
    def test_zero_reality_precedes_observation(self):
        d={"schema":SCHEMA,"primitive_facts":["P1"],"actions":[row("OBS",["P1"],1,k="SAFE_OBSERVATION"),row("PROOF",["P1"],0,2,k="UNIVERSAL_THEOREM")]}
        self.assertEqual(compile_cut(d)["selected_actions"],["PROOF"])
    def test_missing_fact_stays_open(self):
        o=compile_cut({"schema":SCHEMA,"primitive_facts":["P1","P2"],"actions":[row("A",["P1"])]})
        self.assertFalse(o["complete_cover"]); self.assertEqual(o["uncovered_facts"],["P2"])
    def test_unverified_evidence_fails_closed(self):
        a=row("A",["P1"]); a["feasibility_receipt"]["independent"]=False
        self.assertEqual(compile_cut({"schema":SCHEMA,"primitive_facts":["P1"],"actions":[a]})["status"],"FAIL_CLOSED")
    def test_tie_is_deterministic(self):
        d={"schema":SCHEMA,"primitive_facts":["P1"],"actions":[row("B",["P1"]),row("A",["P1"])]}
        self.assertEqual(compile_cut(d)["selected_actions"],["A"])
if __name__=="__main__": unittest.main(verbosity=2)
