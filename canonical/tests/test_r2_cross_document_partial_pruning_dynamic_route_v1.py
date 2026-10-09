from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_semantic_lattice_v8 as v8
from canonical.runtime import r2_cross_document_semantic_registry_v3_lattice_direct_adequacy_v1 as direct


def field_line(eid,field,value):
    return "Effect field: "+json.dumps(
        {"effect_id":eid,"field":field,"value":value},
        sort_keys=True,separators=(",",":"),ensure_ascii=False,
    )


def source(partial_fields):
    rows=[
        "Effect IDs only for threshold: A.active, A.partial.",
        field_line("A.active","effect_class","DEFINE"),
        field_line("A.active","value","10"),
        field_line("A.active","conditions",{}),
        field_line("A.active","valid_from",None),
        field_line("A.active","valid_until",None),
        field_line("A.active","supersedes",[]),
    ]
    for field,value in partial_fields.items():
        rows.append(field_line("A.partial",field,value))
    return "\n".join(rows)


def case(partial_fields):
    return {
        "schema":v8.SCHEMA,
        "case_id":"partial-route",
        "source_documents":[{
            "document_id":"A",
            "source_id":"A",
            "source_text":source(partial_fields),
            "claims":[],
        }],
        "query":{"target_id":"threshold","as_of":"2026-10-09","context":{}},
    }


def goal():
    return (
        "Using the domain-mapped semantic-edge cross-document effect lattice case at "
        "canonical/tmp/case.json, compute and independently verify the effective "
        "value and save it to canonical/tmp/out.json."
    )


def write(root,obj):
    p=root/"canonical/tmp"
    p.mkdir(parents=True,exist_ok=True)
    (p/"case.json").write_text(json.dumps(obj),encoding="utf-8")


class DynamicRoutePartialPruningV9Tests(unittest.TestCase):
    def test_future_partial_effect_closes_existing_route(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write(root,case({"valid_from":"2027-01-01"}))
            out=direct.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"10")

    def test_partial_effect_that_may_apply_stays_semantic_open(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write(root,case({"valid_from":"2020-01-01"}))
            out=direct.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["matched"],out)
            self.assertTrue(out["direct_route_semantic_open"])
            atoms=[
                x for x in out["open_lattice_atoms"]
                if x.get("effect_id")=="A.partial"
            ]
            self.assertGreater(len(atoms),0)

    def test_preflight_remains_pure(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write(root,case({"valid_until":"2026-01-01"}))
            target=root/"canonical/tmp/out.json"
            self.assertFalse(target.exists())
            out=direct.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["matched"],out)
            self.assertFalse(target.exists())

    def test_v9_independent_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write(root,case({"valid_from":"2027-01-01"}))
            target=root/"canonical/tmp/out.json"
            target.write_text('{"old":true}\n',encoding="utf-8")
            old=target.read_bytes()
            original=direct.verifier.verify
            calls={"n":0}
            def injected(problem,result,**kwargs):
                calls["n"]+=1
                if calls["n"]>=3:
                    return {"verified":False,"errors":["forced"]}
                return original(problem,result,**kwargs)
            with patch.object(direct.verifier,"verify",side_effect=injected):
                out=direct.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(target.read_bytes(),old)


if __name__=="__main__":
    unittest.main()
