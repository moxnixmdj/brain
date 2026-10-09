from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_semantic_lattice_v5 as l
from canonical.runtime.certified_document_effect_field_edge_v1 import field_concept_id
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA,
    evidence_sha256,
)
from canonical.runtime.brain_owned_bounded_semantic_relation_edge_authority_v1 import (
    SCHEMA as EDGE_SCHEMA,
    PROOF_CLASS,
)
from canonical.runtime import (
    r2_cross_document_semantic_registry_lattice_direct_adequacy_v1 as direct,
)
from canonical.runtime import r2_direct_end_to_end_adequacy_v18 as v18


def canon(v):
    return json.dumps(
        v,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False,
    )


def field_line(eid,field,value):
    return "Effect field: "+canon({
        "effect_id":eid,"field":field,"value":value,
    })


def mention(source,scope,raw):
    return "MENTION:"+sha256(
        (source+"\n"+scope+"\n"+raw).encode("utf-8")
    ).hexdigest()


def source_without_value():
    return "\n".join([
        "Effect IDs only for threshold: A.t.",
        field_line("A.t","effect_class","DEFINE"),
        field_line("A.t","conditions",{}),
        field_line("A.t","valid_from",None),
        field_line("A.t","valid_until",None),
        field_line("A.t","supersedes",[]),
        "Threshold is ten.",
    ])


def case(*,unsupported=False):
    source=source_without_value()
    scope="crossdoc:v18"
    raw="Threshold is ten."
    start=source.index(raw)
    concept=field_concept_id(
        scope_id=scope,effect_id="A.t",field="value",value="10"
    )
    left=mention("A",scope,raw)
    declaration="\n".join([
        "Semantic universe: "+canon({
            "members":["a","b"],"scope_id":scope,
        }),
        "Semantic extension: "+canon({
            "concept_id":left,"members":["a"],"scope_id":scope,
        }),
        "Semantic extension: "+canon({
            "concept_id":concept,"members":["a","b"],"scope_id":scope,
        }),
    ])
    edge={
        "schema":EDGE_SCHEMA,
        "proof_class":"MODEL_GUESS" if unsupported else PROOF_CLASS,
        "scope_id":scope,
        "source_id":left,
        "target_id":concept,
        "relation":"ENTAILS",
        "bounded_extension_source":{
            "source_id":"decl","scope_id":scope,
            "source_text":declaration,
        },
    }
    dag={
        "schema":EVIDENCE_SCHEMA,
        "scope_id":scope,
        "left_id":left,
        "right_id":concept,
        "entailment_receipts":[edge],
        "counterexample_receipts":[],
    }
    claim={
        "claim_id":"edge.value",
        "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE",
        "scope_id":scope,
        "effect_id":"A.t",
        "field":"value",
        "value":"10",
        "source_span_chars":[start,start+len(raw)],
        "dag_evidence":dag,
        "expected_dag_sha256":evidence_sha256(dag),
    }
    return {
        "schema":l.SCHEMA,
        "case_id":"v18",
        "source_documents":[{
            "document_id":"A","source_id":"A",
            "source_text":source,"claims":[claim],
        }],
        "query":{
            "target_id":"threshold",
            "as_of":"2026-10-09",
            "context":{},
        },
    }


def goal():
    return (
        "Using the semantic-edge cross-document effect lattice case at "
        "canonical/tmp/case.json, compute and independently verify the effective "
        "value and save it to canonical/tmp/out.json."
    )


def write_case(root,obj):
    p=root/"canonical/tmp"
    p.mkdir(parents=True,exist_ok=True)
    (p/"case.json").write_text(json.dumps(obj),encoding="utf-8")


class DirectRouteTests(unittest.TestCase):
    def test_registry_backed_case_matches_and_runs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_case(root,case())
            pf=direct.preflight(
                {"task_id":"x","goal":goal()},repo_root=root
            )
            self.assertTrue(pf["matched"],pf)
            out=direct.run(
                {"task_id":"x","goal":goal()},repo_root=root
            )
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"10")
            self.assertTrue(out["source_immutability_verified"])

    def test_unsupported_edge_class_stays_semantically_open(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_case(root,case(unsupported=True))
            pf=direct.preflight(
                {"task_id":"x","goal":goal()},repo_root=root
            )
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])
            atoms=[
                x for x in pf["open_lattice_atoms"]
                if x.get("dimension")=="DOCUMENT_EFFECT_FIELD"
            ]
            self.assertEqual(len(atoms),1)
            self.assertEqual(atoms[0]["field"],"value")

    def test_postwrite_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_case(root,case())
            op=root/"canonical/tmp/out.json"
            op.write_text('{"old":true}\n',encoding="utf-8")
            old=op.read_bytes()
            original=direct.verifier.verify
            calls={"n":0}

            def injected(problem,result):
                calls["n"]+=1
                if calls["n"]>=3:
                    return {"verified":False,"errors":["forced"]}
                return original(problem,result)

            with patch.object(direct.verifier,"verify",side_effect=injected):
                out=direct.run(
                    {"task_id":"x","goal":goal()},repo_root=root
                )
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(op.read_bytes(),old)


class RouterTests(unittest.TestCase):
    def test_v18_selects_registry_route_before_v17(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_case(root,case())
            with patch.object(v18.v17,"preflight") as prior:
                out=v18.preflight(
                    {"task_id":"x","goal":goal()},repo_root=root
                )
            self.assertTrue(out["matched"],out)
            self.assertEqual(out["route_id"],direct.ROUTE_ID)
            prior.assert_not_called()

    def test_v18_preserves_open_registry_case_without_v17_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_case(root,case(unsupported=True))
            with patch.object(v18.v17,"preflight") as prior:
                out=v18.preflight(
                    {"task_id":"x","goal":goal()},repo_root=root
                )
            self.assertFalse(out["matched"])
            self.assertTrue(out["direct_route_semantic_open"])
            prior.assert_not_called()

    def test_v18_delegates_unrelated_request_to_v17(self):
        request={"task_id":"x","goal":"Do something unrelated."}
        expected={"matched":False,"pass":False,"status":"V17_FALLBACK"}
        with patch.object(
            v18.v17,"preflight",return_value=expected
        ) as prior:
            out=v18.preflight(request)
        self.assertEqual(out,expected)
        prior.assert_called_once()


if __name__=="__main__":
    unittest.main()
