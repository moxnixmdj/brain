from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_semantic_lattice_v2 as l
from canonical.runtime import r2_cross_document_effect_field_lattice_direct_adequacy_v1 as d


def field_line(eid,field,value):
    return "Effect field: "+json.dumps(
        {"effect_id":eid,"field":field,"value":value},
        sort_keys=True,separators=(",",":"),
    )


def source(eid,value,*,omit=()):
    effect={
        "effect_class":"DEFINE",
        "value":value,
        "conditions":{},
        "valid_from":None,
        "valid_until":None,
        "supersedes":[],
    }
    lines=["Effect IDs only for threshold: "+eid+"."]
    for field in (
        "effect_class","value","conditions",
        "valid_from","valid_until","supersedes",
    ):
        if field not in set(omit):
            lines.append(field_line(eid,field,effect[field]))
    return "\n".join(lines)


def case(text):
    return {
        "schema":l.SCHEMA,
        "case_id":"route",
        "source_documents":[{
            "document_id":"A","source_id":"A",
            "source_text":text,"claims":[],
        }],
        "query":{"target_id":"threshold","as_of":"2026-10-09","context":{}},
    }


def goal():
    return (
        "Using the cross-document effect field lattice case at "
        "canonical/tmp/fields.json, compute and independently verify the "
        "effective value and save it to canonical/tmp/out.json."
    )


def write(root,obj):
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True)
    (p/"fields.json").write_text(json.dumps(obj),encoding="utf-8")


class R2CrossDocumentEffectFieldLatticeDirectTests(unittest.TestCase):
    def test_closed_fields_match_and_run(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,case(source("A.t","10")))
            pf=d.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"10")
            self.assertTrue(out["source_immutability_verified"])

    def test_single_missing_field_is_open_with_exact_obligation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,case(source("A.t","10",omit={"supersedes"})))
            pf=d.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])
            atom=pf["open_lattice_atoms"][0]
            self.assertEqual(atom["dimension"],"DOCUMENT_EFFECT_FIELD")
            self.assertEqual(atom["field"],"supersedes")
            self.assertEqual(
                pf["next_proof_obligations"][0]["kind"],
                "PROVE_DOCUMENT_EFFECT_FIELD",
            )

    def test_old_v13_goal_wording_does_not_match(self):
        request={
            "task_id":"x",
            "goal":(
                "Using the cross-document effect semantic lattice case at "
                "canonical/tmp/fields.json, compute and independently verify "
                "the effective value and save it to canonical/tmp/out.json."
            ),
        }
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,case(source("A.t","10")))
            pf=d.preflight(request,repo_root=root)
            self.assertFalse(pf["matched"])
            self.assertEqual(pf["status"],"NOT_APPLICABLE")

    def test_postwrite_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write(root,case(source("A.t","10")))
            op=root/"canonical/tmp/out.json"; op.write_text('{"old":true}\n')
            old=op.read_bytes()
            original=d.verifier.verify
            calls={"n":0}
            def injected(problem,result):
                calls["n"]+=1
                if calls["n"]>=3:
                    return {"verified":False,"errors":["forced"]}
                return original(problem,result)
            with patch.object(d.verifier,"verify",side_effect=injected):
                out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(op.read_bytes(),old)


if __name__=="__main__":
    unittest.main()
