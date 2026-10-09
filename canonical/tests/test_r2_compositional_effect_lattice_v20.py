from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_semantic_lattice_v6 as l
from canonical.runtime import r2_cross_document_compositional_lattice_direct_adequacy_v1 as direct
from canonical.runtime import r2_direct_end_to_end_adequacy_v20 as v20

TEXT=(
    "The complete effect A.t on threshold defines it as 10, "
    "is unconditional, has no start date, has no end date, "
    "and supersedes nothing."
)

def case(text=TEXT):
    return {
        "schema":l.SCHEMA,
        "case_id":"v20",
        "source_documents":[{
            "document_id":"A","source_id":"A",
            "source_text":text,"claims":[],
        }],
        "query":{"target_id":"threshold","as_of":"2026-10-09","context":{}},
    }

def goal():
    return (
        "Using the semantic-edge cross-document effect lattice case at "
        "canonical/tmp/case.json, compute and independently verify the effective "
        "value and save it to canonical/tmp/out.json."
    )

def write_case(root,obj):
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True)
    (p/"case.json").write_text(json.dumps(obj),encoding="utf-8")

class Direct(unittest.TestCase):
    def test_one_sentence_matches_and_runs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write_case(root,case())
            pf=direct.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            out=direct.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],10)

    def test_unrecognized_prose_stays_open(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write_case(root,case("The threshold becomes 10."))
            pf=direct.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])
            self.assertEqual(pf["open_lattice_atoms"][0]["dimension"],"EFFECT_ID_INVENTORY")

    def test_postwrite_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write_case(root,case())
            op=root/"canonical/tmp/out.json"; op.write_text('{"old":true}\n')
            old=op.read_bytes(); original=direct.verifier.verify; calls={"n":0}
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

class Router(unittest.TestCase):
    def test_v20_selects_new_route_before_v19(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write_case(root,case())
            with patch.object(v20.v19,"preflight") as prior:
                out=v20.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["matched"],out)
            self.assertEqual(out["route_id"],direct.ROUTE_ID)
            prior.assert_not_called()

    def test_v20_preserves_open_case_without_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write_case(root,case("The threshold becomes 10."))
            with patch.object(v20.v19,"preflight") as prior:
                out=v20.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["matched"])
            self.assertTrue(out["direct_route_semantic_open"])
            prior.assert_not_called()

    def test_v20_delegates_unrelated(self):
        expected={"matched":False,"pass":False,"status":"V19"}
        with patch.object(v20.v19,"preflight",return_value=expected) as prior:
            out=v20.preflight({"task_id":"x","goal":"unrelated"})
        self.assertEqual(out,expected)
        prior.assert_called_once()

if __name__=="__main__":
    unittest.main()
