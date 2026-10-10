from __future__ import annotations

from hashlib import sha256
import json
import unittest

from canonical.runtime import cross_document_effect_field_discovery_lattice_v1 as d
from canonical.runtime import cross_document_effect_field_discovery_lattice_verify_v1 as dv
from canonical.runtime import cross_document_effect_semantic_lattice_v8 as l
from canonical.runtime.certified_document_effect_field_edge_v1 import field_concept_id
from canonical.runtime.brain_owned_bounded_semantic_relation_edge_authority_v1 import (
    SCHEMA as EDGE_SCHEMA,
    PROOF_CLASS,
)


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


def base_problem(*,missing=("value",)):
    natural="Threshold is ten."
    lines=["Effect IDs only for threshold: A.t."]
    all_fields={
        "effect_class":"DEFINE",
        "value":"10",
        "conditions":{},
        "valid_from":None,
        "valid_until":None,
        "supersedes":[],
    }
    for field,value in all_fields.items():
        if field in missing:
            continue
        lines.append("Effect field: "+canon({
            "effect_id":"A.t","field":field,"value":value,
        }))
    lines.append(natural)
    source="\n".join(lines)
    return {
        "schema":l.SCHEMA,
        "case_id":"discover-wrapper",
        "source_documents":[{
            "document_id":"A","source_id":"A","source_text":source,"claims":[],
        }],
        "query":{"target_id":"threshold","as_of":"2026-10-10","context":{}},
    }, natural, source


def request_for(source,natural,*,field="value",values=("10","11"),evidence=()):
    start=source.index(natural)
    return {
        "document_id":"A","effect_id":"A.t","field":field,
        "scope_id":"discover:wrapper",
        "candidate_spans":[[start,start+len(natural)]],
        "candidate_values":list(values),
        "relation_evidence_candidates":list(evidence),
    }


class DiscoveryLatticeTests(unittest.TestCase):
    def test_authenticated_discovery_closes_lattice_and_verifies(self):
        base,natural,source=base_problem()
        scope="discover:wrapper"
        left=mention("A",scope,natural)
        target=field_concept_id(
            scope_id=scope,effect_id="A.t",field="value",value="10"
        )
        problem={
            "schema":d.SCHEMA,
            "case_id":"discover-wrapper",
            "lattice_problem":base,
            "discovery_requests":[
                request_for(source,natural,evidence=[edge(left,target,scope)])
            ],
        }
        out=d.evaluate(problem)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")
        self.assertEqual(out["discovered_claim_count"],1)
        self.assertTrue(dv.verify(problem,out)["verified"])

    def test_unrequested_top_remains_open(self):
        base,natural,source=base_problem(missing=("value","conditions"))
        scope="discover:wrapper"
        left=mention("A",scope,natural)
        target=field_concept_id(
            scope_id=scope,effect_id="A.t",field="value",value="10"
        )
        problem={
            "schema":d.SCHEMA,
            "case_id":"discover-wrapper",
            "lattice_problem":base,
            "discovery_requests":[
                request_for(source,natural,evidence=[edge(left,target,scope)])
            ],
        }
        out=d.evaluate(problem)
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "OPEN__DISCOVERY_EXHAUSTED_WITH_SEMANTIC_TOP_REMAINING",
        )
        fields={x.get("field") for x in out["open_lattice_atoms"]}
        self.assertEqual(fields,{"conditions"})
        self.assertTrue(dv.verify(problem,out)["verified"])

    def test_request_not_bound_to_open_field_fails_closed(self):
        base,natural,source=base_problem()
        req=request_for(source,natural,field="effect_class",values=("DEFINE",))
        problem={
            "schema":d.SCHEMA,
            "case_id":"discover-wrapper",
            "lattice_problem":base,
            "discovery_requests":[req],
        }
        out=d.evaluate(problem)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("DISCOVERY_REQUEST_NOT_BOUND_TO_OPEN_FIELD_ATOM",out["reason"])

    def test_conflicting_authenticated_values_fail_closed(self):
        base,natural,source=base_problem()
        scope="discover:wrapper"
        left=mention("A",scope,natural)
        t10=field_concept_id(scope_id=scope,effect_id="A.t",field="value",value="10")
        t11=field_concept_id(scope_id=scope,effect_id="A.t",field="value",value="11")
        problem={
            "schema":d.SCHEMA,
            "case_id":"discover-wrapper",
            "lattice_problem":base,
            "discovery_requests":[request_for(
                source,natural,evidence=[edge(left,t10,scope),edge(left,t11,scope)]
            )],
        }
        out=d.evaluate(problem)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__DISCOVERY_CONFLICT_OR_INVALID",
        )
        self.assertTrue(dv.verify(problem,out)["verified"])


if __name__=="__main__":
    unittest.main()
