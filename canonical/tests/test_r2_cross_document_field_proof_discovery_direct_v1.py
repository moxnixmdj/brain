from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_field_discovery_lattice_v1 as dl
from canonical.runtime import cross_document_effect_semantic_lattice_v8 as l
from canonical.runtime.certified_document_effect_field_edge_v1 import field_concept_id
from canonical.runtime.brain_owned_bounded_semantic_relation_edge_authority_v1 import (
    SCHEMA as EDGE_SCHEMA,
    PROOF_CLASS,
)
from canonical.runtime import r2_cross_document_field_proof_discovery_direct_adequacy_v1 as d


def canon(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def mention(source,scope,raw):
    return "MENTION:"+sha256((source+"\n"+scope+"\n"+raw).encode()).hexdigest()


def edge(source_id,target_id,scope):
    decl="\n".join([
        "Semantic universe: "+canon({"members":["a","b"],"scope_id":scope}),
        "Semantic extension: "+canon({"concept_id":source_id,"members":["a"],"scope_id":scope}),
        "Semantic extension: "+canon({"concept_id":target_id,"members":["a","b"],"scope_id":scope}),
    ])
    return {
        "schema":EDGE_SCHEMA,"proof_class":PROOF_CLASS,"scope_id":scope,
        "source_id":source_id,"target_id":target_id,"relation":"ENTAILS",
        "bounded_extension_source":{"source_id":"decl","scope_id":scope,"source_text":decl},
    }


def case(*,leave_conditions_open=False):
    natural="Threshold is ten."
    lines=["Effect IDs only for threshold: A.t."]
    fields={
        "effect_class":"DEFINE",
        "conditions":{},
        "valid_from":None,
        "valid_until":None,
        "supersedes":[],
    }
    for field,value in fields.items():
        if leave_conditions_open and field=="conditions":
            continue
        lines.append("Effect field: "+canon({
            "effect_id":"A.t","field":field,"value":value,
        }))
    lines.append(natural)
    source="\n".join(lines)
    start=source.index(natural)
    scope="discover:route"
    left=mention("A",scope,natural)
    target=field_concept_id(
        scope_id=scope,effect_id="A.t",field="value",value="10"
    )
    lattice={
        "schema":l.SCHEMA,
        "case_id":"route",
        "source_documents":[{
            "document_id":"A","source_id":"A","source_text":source,"claims":[],
        }],
        "query":{"target_id":"threshold","as_of":"2026-10-10","context":{}},
    }
    return {
        "schema":dl.SCHEMA,
        "case_id":"route",
        "lattice_problem":lattice,
        "discovery_requests":[{
            "document_id":"A","effect_id":"A.t","field":"value",
            "scope_id":scope,
            "candidate_spans":[[start,start+len(natural)]],
            "candidate_values":["10","11"],
            "relation_evidence_candidates":[edge(left,target,scope)],
        }],
    }


def goal():
    return (
        "Using the authenticated field-discovery cross-document lattice case at "
        "canonical/tmp/case.json, compute and independently verify the effective "
        "value and save it to canonical/tmp/out.json."
    )


def write_case(root:Path,obj):
    p=root/"canonical/tmp"
    p.mkdir(parents=True,exist_ok=True)
    (p/"case.json").write_text(json.dumps(obj),encoding="utf-8")


class DirectRouteTests(unittest.TestCase):
    def test_preflight_is_pure_and_closed_case_runs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_case(root,case())
            outpath=root/"canonical/tmp/out.json"
            pf=d.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertFalse(outpath.exists())
            out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"10")
            self.assertEqual(out["discovered_claim_count"],1)
            self.assertTrue(out["source_immutability_verified"])
            self.assertTrue(outpath.is_file())

    def test_semantic_open_case_does_not_execute_or_create_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_case(root,case(leave_conditions_open=True))
            outpath=root/"canonical/tmp/out.json"
            pf=d.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])
            fields={x.get("field") for x in pf["open_lattice_atoms"]}
            self.assertEqual(fields,{"conditions"})
            self.assertFalse(outpath.exists())
            out=d.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["pass"])
            self.assertFalse(outpath.exists())

    def test_postwrite_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_case(root,case())
            op=root/"canonical/tmp/out.json"
            op.write_text('{"old":true}\n',encoding="utf-8")
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

    def test_nonmatching_goal_has_no_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            out=d.preflight(
                {"task_id":"x","goal":"Analyze these documents."},
                repo_root=root,
            )
            self.assertFalse(out["matched"])
            self.assertEqual(out["status"],"NOT_APPLICABLE")


if __name__=="__main__":
    unittest.main()
