from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_semantic_lattice_v1 as l
from canonical.runtime.certified_document_effect_relation_v1 import parse_effect_relations
from canonical.runtime import r2_cross_document_effect_semantic_lattice_direct_adequacy_v1 as d

def rel(e): return "Effect relation: "+json.dumps(e,sort_keys=True,separators=(",",":"))
def define(eid,v): return {"conditions":{},"effect_class":"DEFINE","effect_id":eid,"supersedes":[],"target_id":"threshold","valid_from":None,"valid_until":None,"value":v}
def doc(did,ids=None,effects=None):
    effects=effects or []; lines=[]; claims=[]
    if ids is not None:
        lines.append("Effect IDs only for threshold: "+", ".join(ids)+".")
        claims.append({"claim_id":did+".inv","kind":"CERTIFIED_EFFECT_ID_INVENTORY","target_id":"threshold","effect_ids":list(ids)})
    for i,e in enumerate(effects):
        line=rel(e); lines.append(line)
        parsed=parse_effect_relations(line,source=did)["relations"][0]["effect"]
        claims.append({"claim_id":did+f".r{i}","kind":"CERTIFIED_DOCUMENT_EFFECT_RELATION","effect":{k:v for k,v in parsed.items() if k!="source_locator"}})
    return {"document_id":did,"source_id":did,"source_text":"\n".join(lines) or "Unstructured prose.","claims":claims}
def case(*docs): return {"schema":l.SCHEMA,"case_id":"d","source_documents":list(docs),"query":{"target_id":"threshold","as_of":"2026-10-09","context":{}}}
def goal(): return "Using the cross-document effect semantic lattice case at canonical/tmp/lattice.json, compute and independently verify the effective value and save it to canonical/tmp/out.json."
def write(root,obj):
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True); (p/"lattice.json").write_text(json.dumps(obj))

class Direct(unittest.TestCase):
    def test_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,case(doc("A",["A.t"],[define("A.t","10")])))
            out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["pass"],out); self.assertEqual(out["effective_value"],"10")

    def test_inventory_top(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,case(doc("A",None,[])))
            out=d.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["matched"]); self.assertEqual(out["open_lattice_atoms"][0]["dimension"],"EFFECT_ID_INVENTORY")

    def test_relation_top(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,case(doc("A",["A.t"],[])))
            out=d.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["matched"]); self.assertEqual(out["open_lattice_atoms"][0]["effect_id"],"A.t")

    def test_rollback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,case(doc("A",["A.t"],[define("A.t","10")])))
            op=root/"canonical/tmp/out.json"; op.write_text('{"old":true}\n'); old=op.read_bytes()
            orig=d.verifier.verify; calls={"n":0}
            def injected(problem,result):
                calls["n"]+=1
                if calls["n"]>=3: return {"verified":False,"errors":["forced"]}
                return orig(problem,result)
            with patch.object(d.verifier,"verify",side_effect=injected):
                out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["pass"]); self.assertTrue(out["rollback_complete"]); self.assertEqual(op.read_bytes(),old)

if __name__=="__main__": unittest.main()
