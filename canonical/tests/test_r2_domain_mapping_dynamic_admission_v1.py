from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_semantic_lattice_v8 as lattice
from canonical.runtime.certified_document_effect_field_edge_v1 import field_concept_id
from canonical.runtime.semantic_relation_entailment_dag_v1 import EVIDENCE_SCHEMA,evidence_sha256
from canonical.runtime import brain_owned_domain_mapping_relation_edge_authority_v1 as domain
from canonical.runtime import r2_cross_document_semantic_registry_v3_lattice_direct_adequacy_v1 as direct
from canonical.runtime import r2_direct_live_admission_v1 as live

def canon(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def field_line(eid,field,value):
    return "Effect field: "+canon({"effect_id":eid,"field":field,"value":value})

def mention(source,scope,raw):
    return "MENTION:"+sha256((source+"\n"+scope+"\n"+raw).encode()).hexdigest()

def source_text():
    return "\n".join([
        "Effect IDs only for threshold: A.t.",
        field_line("A.t","effect_class","DEFINE"),
        field_line("A.t","conditions",{}),
        field_line("A.t","valid_from",None),
        field_line("A.t","valid_until",None),
        field_line("A.t","supersedes",[]),
        "Loss-absorbing cushion means capital conservation buffer.",
    ])

def case(*,model_only=False):
    source=source_text()
    scope="crossdoc:domain-dynamic"
    raw="Loss-absorbing cushion"
    start=source.index(raw)
    concept=field_concept_id(scope_id=scope,effect_id="A.t",field="value",value="CCOB")
    left=mention("A",scope,raw)
    relation_problem={"required_relation":"LEFT_ENTAILS_RIGHT"}
    if model_only:
        relation_problem["candidate_relations"]=[{"relation":"SIMILAR","score":0.999,"source":"embedding"}]
    else:
        relation_problem["explicit_definition_sources"]=[{
            "source_id":"A","scope_id":scope,
            "source_text":"Loss-absorbing cushion means capital conservation buffer.",
        }]
    edge={
        "schema":domain.SCHEMA,
        "proof_class":domain.PROOF_CLASS,
        "scope_id":scope,
        "source_id":left,
        "target_id":concept,
        "relation":"ENTAILS",
        "domain_mapping_source":{
            "source_id":"A","raw_span":raw,
            "candidate_concepts":[{
                "concept_id":concept,
                "surface":"capital conservation buffer",
                "required_atoms":[],"forbidden_atoms":[],
            }],
            "evidence":[],
            "candidate_semantic_atoms":[],
            "relation_problems":{concept:relation_problem},
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
        "claim_id":"edge.value.domain",
        "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE",
        "scope_id":scope,
        "effect_id":"A.t",
        "field":"value",
        "value":"CCOB",
        "source_span_chars":[start,start+len(raw)],
        "dag_evidence":dag,
        "expected_dag_sha256":evidence_sha256(dag),
    }
    return {
        "schema":lattice.SCHEMA,
        "case_id":"domain-dynamic",
        "source_documents":[{
            "document_id":"A","source_id":"A",
            "source_text":source,"claims":[claim],
        }],
        "query":{"target_id":"threshold","as_of":"2026-10-09","context":{}},
    }

def goal():
    return (
        "Using the domain-mapped semantic-edge cross-document effect lattice case at "
        "canonical/tmp/case.json, compute and independently verify the effective "
        "value and save it to canonical/tmp/out.json."
    )

def write_case(root,obj):
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True)
    (p/"case.json").write_text(json.dumps(obj),encoding="utf-8")

def dyn_row():
    return {
        "route_id":direct.ROUTE_ID,
        "runtime_path":"canonical/runtime/r2_cross_document_semantic_registry_v3_lattice_direct_adequacy_v1.py",
        "runtime_git_blob_sha":"0"*40,
        "preflight_callable":"preflight",
        "run_callable":"run",
        "verification_path":"canonical/verification/fake.json",
        "verification_git_blob_sha":"1"*40,
        "selection_class":"UNIQUE_MATCH_REQUIRED",
        "active":True,
        "automatic_live_admission":True,
    }

class DirectRouteTests(unittest.TestCase):
    def test_domain_mapping_edge_closes_value(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write_case(root,case())
            out=direct.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"CCOB")

    def test_similarity_only_stays_top(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write_case(root,case(model_only=True))
            out=direct.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["matched"],out)
            self.assertTrue(out["direct_route_semantic_open"])
            atoms=[x for x in out["open_lattice_atoms"] if x.get("dimension")=="DOCUMENT_EFFECT_FIELD"]
            self.assertEqual(len(atoms),1)
            self.assertEqual(atoms[0]["field"],"value")

    def test_postwrite_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write_case(root,case())
            op=root/"canonical/tmp/out.json"; op.write_text('{"old":true}\n')
            old=op.read_bytes()
            original=direct.verifier.verify; calls={"n":0}
            def injected(problem,result,**kwargs):
                calls["n"]+=1
                if calls["n"]>=3: return {"verified":False,"errors":["forced"]}
                return original(problem,result,**kwargs)
            with patch.object(direct.verifier,"verify",side_effect=injected):
                out=direct.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(op.read_bytes(),old)

class DynamicLiveTests(unittest.TestCase):
    def test_unique_dynamic_match_selected_when_legacy_idle(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write_case(root,case())
            row=dyn_row()
            with patch.object(live,"_dynamic_rows",return_value=[row]), \
                 patch.object(live.legacy,"preflight",return_value={"matched":False,"status":"NO"}):
                out=live.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(out["matched"],out)
            self.assertEqual(out["route_id"],direct.ROUTE_ID)

    def test_dynamic_open_state_fails_closed_before_legacy(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write_case(root,case(model_only=True))
            row=dyn_row()
            with patch.object(live,"_dynamic_rows",return_value=[row]), \
                 patch.object(live.legacy,"preflight") as legacy:
                out=live.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertEqual(
                out["status"],
                "FAIL_CLOSED__DYNAMIC_SEMANTIC_OPEN_REQUIRES_PRECEDENCE_AUTHORITY",
            )
            legacy.assert_not_called()


    def test_preflight_is_pure_no_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write_case(root,case())
            out_path=root/"canonical/tmp/out.json"
            self.assertFalse(out_path.exists())
            pf=direct.preflight({"task_id":"x","goal":goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertFalse(out_path.exists())

    def test_raw_acceptance_drift_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); write_case(root,case())
            op=root/"canonical/tmp/out.json"; op.write_text('{"old":true}\\n')
            old=op.read_bytes()
            first=direct._contract(goal())
            second=deepcopy(first)
            second["acceptance_contract"]["required_obligation_ids"]=list(
                second["acceptance_contract"]["required_obligation_ids"]
            )+["FAKE-DRIFT"]
            with patch.object(direct,"_contract",side_effect=[first,second]):
                out=direct.run({"task_id":"x","goal":goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertIn("RAW_ACCEPTANCE_SET_DRIFT",out["reason"])
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(op.read_bytes(),old)

    def test_matched_dynamic_failure_never_falls_through_to_legacy(self):
        row=dyn_row()
        failure={
            "pass":False,
            "matched":True,
            "route_id":direct.ROUTE_ID,
            "status":"OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY",
        }
        with patch.object(live,"preflight",return_value={
                 "matched":True,"route_id":direct.ROUTE_ID,"status":"MATCHED"
             }), \
             patch.object(live,"_dynamic_rows",return_value=[row]), \
             patch.object(live,"_resolve_callable",return_value=lambda *a,**k: failure), \
             patch.object(live.legacy,"run") as legacy:
            out=live.run({"task_id":"x","goal":goal()})
        self.assertEqual(out,failure)
        legacy.assert_not_called()

if __name__=="__main__":
    unittest.main()
