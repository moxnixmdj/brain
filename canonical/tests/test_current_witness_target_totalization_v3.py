from __future__ import annotations
import copy,json
from pathlib import Path
from canonical.runtime.current_witness_target_totalization_v3 import (
 ROOT,TARGETS,TARGET_VERIFY,WITNESSES,EVIDENCE,ROOT3,blob,totalize)

def load(p): return json.loads(p.read_text())
def run(td=None,tv=None,wd=None,ev=None,r3=None):
 evv=ev if ev is not None else load(EVIDENCE)
 return totalize(td if td is not None else load(TARGETS),
   tv if tv is not None else load(TARGET_VERIFY),
   wd if wd is not None else load(WITNESSES),
   evv,r3 if r3 is not None else load(ROOT3),
   evidence_blob_sha=blob(EVIDENCE))

def test_current_8x14_surface_zero_direct_reuse():
 o=run(); assert o["pass"] is True,o
 assert o["target_count"]==8 and o["witness_count"]==14 and o["pair_count"]==112
 assert o["target_atom_occurrence_count"]==37 and o["target_metric_occurrence_count"]==7
 assert o["closed_target_count"]==0 and o["residual_target_count"]==8

def test_invented_semantic_credit_fails_closed():
 w=load(WITNESSES); w=copy.deepcopy(w)
 w["witnesses"][0]["semantic_implications"]=["invented"]
 o=run(wd=w); assert o["pass"] is False
 assert "CURRENT_WITNESS_NORMALIZATION_INVALID" in o["errors"]

def test_invented_metric_credit_fails_closed():
 w=load(WITNESSES); w=copy.deepcopy(w)
 w["witnesses"][0]["normalized_metric_bounds"]={"x":1}
 o=run(wd=w); assert o["pass"] is False

def test_proved_target_reentry_fails_closed():
 ev=load(EVIDENCE); ev=copy.deepcopy(ev)
 ev["claims"].append({"predicate_id":"IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS","state":"PROVED",
   "proof_kind":"fake","independent_or_objective":True,"scope_complete":True})
 o=run(ev=ev); assert o["pass"] is False

if __name__=="__main__":
 test_current_8x14_surface_zero_direct_reuse()
 test_invented_semantic_credit_fails_closed()
 test_invented_metric_credit_fails_closed()
 test_proved_target_reentry_fails_closed()
 print("test_current_witness_target_totalization_v3: PASS")
