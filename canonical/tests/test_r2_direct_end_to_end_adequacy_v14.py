from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_dimension_lattice_v1 as l
from canonical.runtime import r2_cross_document_effect_dimension_lattice_direct_adequacy_v1 as d
from canonical.runtime import r2_direct_end_to_end_adequacy_v14 as v14

def j(v): return json.dumps(v,sort_keys=True,separators=(",",":"))
def doc(closed=True):
    lines=["Effect IDs only for threshold: A.t."]
    claims=[{"claim_id":"inv","kind":"CERTIFIED_EFFECT_ID_INVENTORY","target_id":"threshold","effect_ids":["A.t"]}]
    rows=[
        ("effect_class","Effect A.t class: DEFINE.","DEFINE"),
        ("value",'Effect A.t value JSON: "10".',"10"),
        ("conditions","Effect A.t conditions JSON: {}.",{}),
        ("valid_from","Effect A.t valid from: none.",None),
        ("valid_until","Effect A.t valid until: none.",None),
        ("supersedes","Effect A.t supersedes: none.",[]),
    ]
    for i,(dim,text,val) in enumerate(rows):
        if not closed and dim=="value": continue
        lines.append(text)
        claims.append({"claim_id":f"d{i}","kind":"CERTIFIED_DOCUMENT_EFFECT_DIMENSION","effect_id":"A.t","dimension":dim,"value":val})
    return {"document_id":"A","source_id":"A","source_text":"\n".join(lines),"claims":claims}
def problem(closed=True): return {"schema":l.SCHEMA,"case_id":"r14","source_documents":[doc(closed)],"query":{"target_id":"threshold","as_of":"2026-10-09","context":{}}}
def goal(): return "Using the cross-document effect dimension lattice case at canonical/tmp/case.json, compute and independently verify the effective value and save it to canonical/tmp/out.json."
def write(root,obj):
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True); (p/"case.json").write_text(json.dumps(obj))

class Router(unittest.TestCase):
    def test_v14_selects_dimension_lattice_before_v13(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,problem(True))
            with patch.object(v14.v13,"preflight") as prior:
                out=v14.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["matched"],out); self.assertEqual(out["route_id"],d.ROUTE_ID); prior.assert_not_called()
    def test_open_dimension_top_does_not_fall_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,problem(False))
            with patch.object(v14.v13,"preflight") as prior:
                out=v14.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["matched"]); self.assertTrue(out["direct_route_semantic_open"]); prior.assert_not_called()
    def test_unrelated_request_delegates_to_v13(self):
        expected={"matched":False,"pass":False,"status":"V13"}
        with patch.object(v14.v13,"preflight",return_value=expected) as prior:
            out=v14.preflight({"task_id":"x","goal":"unrelated"})
        self.assertEqual(out,expected); prior.assert_called_once()

if __name__=="__main__": unittest.main()
