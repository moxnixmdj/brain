from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime.certified_document_effect_field_edge_v1 import field_concept_id
from canonical.runtime.semantic_relation_entailment_dag_v1 import EVIDENCE_SCHEMA, evidence_sha256
from canonical.runtime.brain_owned_natural_subsumption_closure_edge_authority_v1 import (
    SCHEMA as EDGE_SCHEMA, PROOF_CLASS,
)
from canonical.runtime.cross_document_effect_semantic_lattice_v9 import SCHEMA as LATTICE_SCHEMA
from canonical.runtime import r2_cross_document_natural_entailment_lattice_direct_adequacy_v1 as route


def _field_line(effect_id,field,value):
    payload={"effect_id":effect_id,"field":field,"value":value}
    return "Effect field: "+json.dumps(payload,sort_keys=True,separators=(",",":"))


def _goal():
    return (
        "Using the natural-entailment semantic-edge cross-document effect lattice case at "
        "canonical/tmp/case.json, compute and independently verify the effective value "
        "and save it to canonical/tmp/out.json."
    )


def _problem():
    source_id="doc"
    scope="finance"
    effect_id="E1"
    raw_span="capital_requirement"
    value="12"

    lines=[
        "Effect IDs only for threshold: E1.",
        _field_line(effect_id,"effect_class","DEFINE"),
        raw_span,
        _field_line(effect_id,"conditions",{}),
        _field_line(effect_id,"valid_from",None),
        _field_line(effect_id,"valid_until",None),
        _field_line(effect_id,"supersedes",[]),
    ]
    source_text="\n".join(lines)
    start=source_text.index(raw_span)
    end=start+len(raw_span)

    mention="MENTION:"+sha256(
        (source_id+"\n"+scope+"\n"+raw_span).encode("utf-8")
    ).hexdigest()
    concept=field_concept_id(
        scope_id=scope,
        effect_id=effect_id,
        field="value",
        value=value,
    )
    middle="normalized_threshold_value"
    natural_source=(
        f"In scope {scope}, every {mention} is a {middle}.\n"
        f"In scope {scope}, every {middle} is a {concept}."
    )
    relation_evidence={
        "schema":EDGE_SCHEMA,
        "proof_class":PROOF_CLASS,
        "scope_id":scope,
        "source_id":mention,
        "target_id":concept,
        "relation":"ENTAILS",
        "natural_subsumption_source":{
            "source_id":"relation-doc",
            "source_text":natural_source,
        },
    }
    dag={
        "schema":EVIDENCE_SCHEMA,
        "scope_id":scope,
        "left_id":mention,
        "right_id":concept,
        "entailment_receipts":[relation_evidence],
        "counterexample_receipts":[],
    }

    claims=[
        {
            "claim_id":"inventory",
            "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
            "target_id":"threshold",
            "effect_ids":[effect_id],
        },
        {
            "claim_id":"class",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            "effect_id":effect_id,"field":"effect_class","value":"DEFINE",
        },
        {
            "claim_id":"conditions",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            "effect_id":effect_id,"field":"conditions","value":{},
        },
        {
            "claim_id":"valid_from",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            "effect_id":effect_id,"field":"valid_from","value":None,
        },
        {
            "claim_id":"valid_until",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            "effect_id":effect_id,"field":"valid_until","value":None,
        },
        {
            "claim_id":"supersedes",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            "effect_id":effect_id,"field":"supersedes","value":[],
        },
        {
            "claim_id":"value-edge",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE",
            "scope_id":scope,
            "effect_id":effect_id,
            "field":"value",
            "value":value,
            "source_span_chars":[start,end],
            "dag_evidence":dag,
            "expected_dag_sha256":evidence_sha256(dag),
        },
    ]
    return {
        "schema":LATTICE_SCHEMA,
        "case_id":"natural-load-bearing",
        "source_documents":[{
            "document_id":"D",
            "source_id":source_id,
            "source_text":source_text,
            "claims":claims,
        }],
        "query":{
            "target_id":"threshold",
            "as_of":"2026-10-10",
            "context":{},
        },
    }


class Tests(unittest.TestCase):
    def test_natural_nonexplicit_value_edge_closes_lattice(self):
        result=route.producer.evaluate(_problem())
        self.assertTrue(result["pass"],result)
        self.assertEqual(result["effective_value"],"12")
        receipts=result["proof_receipts"][0]["accepted_claims"]
        edge=[
            row for row in receipts
            if row.get("effect_id")=="E1"
            and row.get("field")=="value"
        ]
        self.assertEqual(len(edge),1,result)
        self.assertEqual(
            edge[0].get("proof_primitive"),
            "SEMANTIC_ENTAILMENT_DAG_FIELD_EDGE_V1",
        )

    def test_direct_route_transaction_closes_same_case(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"canonical/tmp"
            p.mkdir(parents=True)
            (p/"case.json").write_text(json.dumps(_problem()),encoding="utf-8")
            out=route.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"12")
            self.assertTrue(out["source_immutability_verified"])
            self.assertTrue((p/"out.json").is_file())


    def test_preflight_is_pure_and_creates_no_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"canonical/tmp"
            p.mkdir(parents=True)
            (p/"case.json").write_text(json.dumps(_problem()),encoding="utf-8")
            out=route.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(out["matched"],out)
            self.assertFalse((p/"out.json").exists())

    def test_unrelated_goal_has_no_scope(self):
        with tempfile.TemporaryDirectory() as td:
            out=route.preflight(
                {"task_id":"x","goal":"Analyze this unrelated request."},
                repo_root=Path(td),
            )
            self.assertFalse(out["matched"])
            self.assertEqual(out["status"],"NOT_APPLICABLE")

    def test_postwrite_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"canonical/tmp"
            p.mkdir(parents=True)
            (p/"case.json").write_text(json.dumps(_problem()),encoding="utf-8")
            outp=p/"out.json"
            outp.write_text('{"old":true}\n',encoding="utf-8")
            old=outp.read_bytes()
            original=route.verifier.verify
            calls={"n":0}
            def injected(problem,result):
                calls["n"]+=1
                if calls["n"]>=3:
                    return {"verified":False,"errors":["forced"]}
                return original(problem,result)
            with patch.object(route.verifier,"verify",side_effect=injected):
                out=route.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(outp.read_bytes(),old)

    def test_raw_acceptance_drift_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"canonical/tmp"
            p.mkdir(parents=True)
            (p/"case.json").write_text(json.dumps(_problem()),encoding="utf-8")
            original=route._contract
            calls={"n":0}
            def drift(goal):
                calls["n"]+=1
                out=original(goal)
                if calls["n"]>=3:
                    changed=json.loads(json.dumps(out))
                    changed["acceptance_contract"]["required_obligation_ids"]=[
                        "DRIFTED"
                    ]
                    return changed
                return out
            with patch.object(route,"_contract",side_effect=drift):
                out=route.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertFalse((p/"out.json").exists())


if __name__=="__main__":
    unittest.main()
