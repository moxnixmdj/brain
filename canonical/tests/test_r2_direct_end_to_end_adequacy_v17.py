from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_semantic_lattice_v4 as lattice
from canonical.runtime.certified_document_effect_field_edge_v1 import field_concept_id
from canonical.runtime.semantic_relation_entailment_dag_v1 import EVIDENCE_SCHEMA, evidence_sha256
from canonical.runtime.brain_owned_semantic_relation_edge_authority_v1 import SCHEMA as EDGE_SCHEMA, PROOF_CLASS
from canonical.runtime import r2_cross_document_semantic_edge_lattice_direct_adequacy_v1 as direct
from canonical.runtime import r2_direct_end_to_end_adequacy_v17 as v17


def field_line(eid,field,value):
    return "Effect field: "+json.dumps(
        {"effect_id":eid,"field":field,"value":value},
        sort_keys=True,separators=(",",":"),ensure_ascii=False,
    )


def mention_id(source_id,scope_id,raw_span):
    return "MENTION:"+sha256(
        (source_id+"\n"+scope_id+"\n"+raw_span).encode("utf-8")
    ).hexdigest()


def case(*,supported=True):
    source_id="A"
    scope="crossdoc:v17"
    raw="Threshold amount"
    target_surface="A.t value 10"
    lines=[
        "Effect IDs only for threshold: A.t.",
        field_line("A.t","effect_class","DEFINE"),
        field_line("A.t","conditions",{}),
        field_line("A.t","valid_from",None),
        field_line("A.t","valid_until",None),
        field_line("A.t","supersedes",[]),
        raw+" means "+target_surface+".",
    ]
    source="\n".join(lines)
    concept=field_concept_id(
        scope_id=scope,effect_id="A.t",field="value",value="10"
    )
    left=mention_id(source_id,scope,raw)
    if supported:
        receipt={
            "schema":EDGE_SCHEMA,
            "proof_class":PROOF_CLASS,
            "scope_id":scope,
            "source_id":left,
            "target_id":concept,
            "source_surface":raw,
            "target_surface":target_surface,
            "relation":"ENTAILS",
            "explicit_definition_sources":[{
                "source_id":"definition:A",
                "scope_id":scope,
                "source_text":raw+" means "+target_surface+".",
            }],
        }
    else:
        receipt={"kind":"legacy-edge"}
    dag={
        "schema":EVIDENCE_SCHEMA,
        "scope_id":scope,
        "left_id":left,
        "right_id":concept,
        "entailment_receipts":[receipt],
        "counterexample_receipts":[],
    }
    start=source.index(raw)
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
        "schema":lattice.SCHEMA,
        "case_id":"edge-direct",
        "source_documents":[{
            "document_id":"A",
            "source_id":source_id,
            "source_text":source,
            "claims":[claim],
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
        "canonical/tmp/edge.json, compute and independently verify the effective "
        "value and save it to canonical/tmp/out.json."
    )


def write(root:Path,obj):
    p=root/"canonical/tmp"
    p.mkdir(parents=True,exist_ok=True)
    (p/"edge.json").write_text(json.dumps(obj),encoding="utf-8")


class SemanticEdgeDirectTests(unittest.TestCase):
    def test_brain_owned_edge_closes_route_without_external_verifier(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write(root,case(supported=True))
            pf=direct.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            out=direct.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"10")
            self.assertTrue(out["query_relative_effect_semantics_finite"])

    def test_unsupported_edge_stays_open(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write(root,case(supported=False))
            pf=direct.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])
            atoms=[
                x for x in pf["open_lattice_atoms"]
                if x.get("field")=="value"
            ]
            self.assertEqual(len(atoms),1)

    def test_v17_selects_edge_route_before_v16(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write(root,case(supported=True))
            with patch.object(v17.v16,"preflight") as prior:
                pf=v17.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertEqual(pf["route_id"],direct.ROUTE_ID)
            prior.assert_not_called()

    def test_v17_delegates_unrelated_request(self):
        expected={"matched":False,"pass":False,"status":"V16_FALLBACK"}
        with patch.object(v17.v16,"preflight",return_value=expected) as prior:
            out=v17.preflight({"task_id":"x","goal":"unrelated"})
        self.assertEqual(out,expected)
        prior.assert_called_once()


if __name__=="__main__":
    unittest.main()
