from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_semantic_lattice_v1 as l
from canonical.runtime.certified_document_effect_relation_v1 import parse_effect_relations
from canonical.runtime import r2_cross_document_effect_semantic_lattice_direct_adequacy_v1 as d
from canonical.runtime import r2_direct_end_to_end_adequacy_v13 as v13

def relation(e): return "Effect relation: "+json.dumps(e,sort_keys=True,separators=(",",":"))
def define(eid,v): return {"conditions":{},"effect_class":"DEFINE","effect_id":eid,"supersedes":[],"target_id":"threshold","valid_from":None,"valid_until":None,"value":v}
def problem(*,closed):
    lines=["Effect IDs only for threshold: A.t."]; claims=[{"claim_id":"inv","kind":"CERTIFIED_EFFECT_ID_INVENTORY","target_id":"threshold","effect_ids":["A.t"]}]
    if closed:
        line=relation(define("A.t","10")); lines.append(line)
        parsed=parse_effect_relations(line,source="A")["relations"][0]["effect"]
        claims.append({"claim_id":"rel","kind":"CERTIFIED_DOCUMENT_EFFECT_RELATION","effect":{k:v for k,v in parsed.items() if k!="source_locator"}})
    return {"schema":l.SCHEMA,"case_id":"r","source_documents":[{"document_id":"A","source_id":"A","source_text":"\n".join(lines),"claims":claims}],"query":{"target_id":"threshold","as_of":"2026-10-09","context":{}}}
def goal(): return "Using the cross-document effect semantic lattice case at canonical/tmp/lattice.json, compute and independently verify the effective value and save it to canonical/tmp/out.json."
def write(root,obj):
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True); (p/"lattice.json").write_text(json.dumps(obj))

class Router(unittest.TestCase):
    def test_selects_v13(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,problem(closed=True))
            with patch.object(v13.v12,"preflight") as prior:
                out=v13.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["matched"]); self.assertEqual(out["route_id"],d.ROUTE_ID); prior.assert_not_called()

    def test_open_top_does_not_fall_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,problem(closed=False))
            with patch.object(v13.v12,"preflight") as prior:
                out=v13.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["matched"]); self.assertTrue(out["direct_route_semantic_open"]); prior.assert_not_called()

    def test_unrelated_delegates(self):
        expected={"matched":False,"pass":False,"status":"V12"}
        with patch.object(v13.v12,"preflight",return_value=expected) as prior:
            out=v13.preflight({"task_id":"x","goal":"unrelated"})
        self.assertEqual(out,expected); prior.assert_called_once()

if __name__=="__main__": unittest.main()
