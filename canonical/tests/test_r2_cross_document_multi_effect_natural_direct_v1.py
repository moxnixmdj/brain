from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_semantic_lattice_v9 as lattice
from canonical.runtime import r2_cross_document_multi_effect_natural_direct_adequacy_v1 as direct

def source(full=True):
    lines=[
        "The complete effects on threshold are A.t, B.t, and C.t.",
        "Effect A.t on threshold defines it as \"10\", is unconditional, has no start date, has no end date, and supersedes nothing.",
        "Effect B.t on threshold replaces it with \"12\", is unconditional, is valid from 2026-07-01, has no end date, and supersedes A.t.",
        "Effect C.t on threshold creates an exception for it with value \"8\", applies when {\"small\":true}, is valid from 2026-07-01, has no end date, and supersedes B.t.",
    ]
    return "\n".join(lines if full else lines[:-1])

def problem(*,small=True,full=True):
    return {
        "schema":lattice.SCHEMA,
        "case_id":"route",
        "source_documents":[{
            "document_id":"D","source_id":"D",
            "source_text":source(full=full),"claims":[],
        }],
        "query":{
            "target_id":"threshold",
            "as_of":"2026-08-01",
            "context":{"small":small},
        },
    }

def goal():
    return (
        "Using the multi-effect natural cross-document lattice case at "
        "canonical/tmp/case.json, compute and independently verify the "
        "effective value and save it to canonical/tmp/out.json."
    )

def write(root:Path,obj):
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True)
    (p/"case.json").write_text(json.dumps(obj),encoding="utf-8")

class MultiEffectNaturalDirectRouteTests(unittest.TestCase):
    def test_exception_case_executes_to_8(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,problem(small=True))
            pf=direct.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            out=direct.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"8")
            self.assertTrue(out["source_immutability_verified"])

    def test_nonexception_case_executes_to_12(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,problem(small=False))
            out=direct.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"12")

    def test_incomplete_declared_effect_set_stays_open(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,problem(full=False))
            pf=direct.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])

    def test_postwrite_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,problem())
            op=root/"canonical/tmp/out.json"; op.write_text('{"old":true}\n')
            old=op.read_bytes()
            original=direct.verifier.verify
            calls={"n":0}
            def injected(problem,result):
                calls["n"]+=1
                if calls["n"]>=3:
                    return {"verified":False,"errors":["forced"]}
                return original(problem,result)
            with patch.object(direct.verifier,"verify",side_effect=injected):
                out=direct.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(op.read_bytes(),old)

    def test_unrelated_goal_is_not_applicable(self):
        with tempfile.TemporaryDirectory() as td:
            out=direct.preflight({"task_id":"x","goal":"unrelated"},repo_root=Path(td))
            self.assertFalse(out["matched"])
            self.assertEqual(out["status"],"NOT_APPLICABLE")

if __name__=="__main__":
    unittest.main()
