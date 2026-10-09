from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_dimension_lattice_v1 as l
from canonical.runtime import r2_cross_document_effect_dimension_lattice_direct_adequacy_v1 as d

def j(v): return json.dumps(v,sort_keys=True,separators=(",",":"))
def line(eid,dim,val):
    if dim=="effect_class": return f"Effect {eid} class: {val}."
    if dim=="value": return f"Effect {eid} value JSON: {j(val)}."
    if dim=="conditions": return f"Effect {eid} conditions JSON: {j(val)}."
    if dim=="valid_from": return f"Effect {eid} valid from: {val if val is not None else 'none'}."
    if dim=="valid_until": return f"Effect {eid} valid until: {val if val is not None else 'none'}."
    if dim=="supersedes": return f"Effect {eid} supersedes: {', '.join(val) if val else 'none'}."
    raise AssertionError(dim)
def dims(value="10"): return {"effect_class":"DEFINE","value":value,"conditions":{},"valid_from":None,"valid_until":None,"supersedes":[]}
def doc(*,partial=False):
    lines=["Effect IDs only for threshold: A.t."]
    claims=[{"claim_id":"inv","kind":"CERTIFIED_EFFECT_ID_INVENTORY","target_id":"threshold","effect_ids":["A.t"]}]
    for i,(dim,val) in enumerate(dims().items()):
        if partial and dim=="value": continue
        lines.append(line("A.t",dim,val))
        claims.append({"claim_id":f"d{i}","kind":"CERTIFIED_DOCUMENT_EFFECT_DIMENSION","effect_id":"A.t","dimension":dim,"value":val})
    return {"document_id":"A","source_id":"A","source_text":"\n".join(lines),"claims":claims}
def case(*,partial=False): return {"schema":l.SCHEMA,"case_id":"v14","source_documents":[doc(partial=partial)],"query":{"target_id":"threshold","as_of":"2026-10-09","context":{}}}
def goal(): return "Using the cross-document effect dimension lattice case at canonical/tmp/case.json, compute and independently verify the effective value and save it to canonical/tmp/out.json."
def write(root,obj):
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True); (p/"case.json").write_text(json.dumps(obj))

class Direct(unittest.TestCase):
    def test_closed_case_runs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,case())
            out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["pass"],out); self.assertEqual(out["effective_value"],"10")
    def test_source_explicit_autofill_runs_without_caller_claims(self):
        obj=case()
        obj["source_documents"][0]["claims"]=[]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,obj)
            out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"10")

    def test_partial_case_returns_exact_top_dimension(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,case(partial=True))
            out=d.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["matched"],out)
            self.assertEqual(out["open_lattice_atoms"][0]["dimension"],"value")
            self.assertFalse(out["query_relative_effect_semantics_finite"])
    def test_postwrite_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,case())
            op=root/"canonical/tmp/out.json"; op.write_text('{"old":true}\n'); old=op.read_bytes()
            orig=d.verifier.verify; calls={"n":0}
            def injected(problem,result):
                calls["n"]+=1
                if calls["n"]>=3: return {"verified":False,"errors":["forced"]}
                return orig(problem,result)
            with patch.object(d.verifier,"verify",side_effect=injected):
                out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["pass"]); self.assertTrue(out["rollback_complete"]); self.assertEqual(op.read_bytes(),old)
    def test_unrelated_goal_has_no_scope(self):
        out=d.preflight({"task_id":"x","goal":"unrelated"})
        self.assertFalse(out["matched"]); self.assertEqual(out["status"],"NOT_APPLICABLE")

if __name__=="__main__": unittest.main()
