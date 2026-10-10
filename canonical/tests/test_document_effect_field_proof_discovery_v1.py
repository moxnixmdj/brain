from __future__ import annotations

from hashlib import sha256
import json
import unittest

from canonical.runtime.document_effect_field_proof_discovery_v1 import (
    SCHEMA,
    discover,
)
from canonical.runtime.certified_document_effect_field_edge_v1 import (
    field_concept_id,
)
from canonical.runtime.brain_owned_bounded_semantic_relation_edge_authority_v1 import (
    SCHEMA as EDGE_SCHEMA,
    PROOF_CLASS,
)
from canonical.runtime.cross_document_effect_semantic_lattice_v8 import (
    SCHEMA as LATTICE_SCHEMA,
    evaluate as evaluate_lattice,
)


def canon(v):
    return json.dumps(
        v,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False,
    )


def mention(source,scope,raw):
    return "MENTION:"+sha256(
        (source+"\n"+scope+"\n"+raw).encode("utf-8")
    ).hexdigest()


def bounded_edge(*,source_id,target_id,scope,members_source=("a",),members_target=("a","b")):
    declaration="\n".join([
        "Semantic universe: "+canon({
            "members":["a","b"],"scope_id":scope,
        }),
        "Semantic extension: "+canon({
            "concept_id":source_id,
            "members":list(members_source),
            "scope_id":scope,
        }),
        "Semantic extension: "+canon({
            "concept_id":target_id,
            "members":list(members_target),
            "scope_id":scope,
        }),
    ])
    return {
        "schema":EDGE_SCHEMA,
        "proof_class":PROOF_CLASS,
        "scope_id":scope,
        "source_id":source_id,
        "target_id":target_id,
        "relation":"ENTAILS",
        "bounded_extension_source":{
            "source_id":"decl",
            "scope_id":scope,
            "source_text":declaration,
        },
    }


def discovery_case(*,values=("10","11"),evidence=()):
    source="Threshold is ten."
    scope="discover:test"
    return {
        "schema":SCHEMA,
        "source_id":"A",
        "source_text":source,
        "scope_id":scope,
        "effect_id":"A.t",
        "field":"value",
        "candidate_spans":[[0,len(source)]],
        "candidate_values":list(values),
        "relation_evidence_candidates":list(evidence),
    }


class DocumentEffectFieldProofDiscoveryV1Tests(unittest.TestCase):
    def test_one_authenticated_value_is_discovered(self):
        source="Threshold is ten."
        scope="discover:test"
        left=mention("A",scope,source)
        concept=field_concept_id(
            scope_id=scope,effect_id="A.t",field="value",value="10"
        )
        edge=bounded_edge(
            source_id=left,target_id=concept,scope=scope
        )
        out=discover(discovery_case(evidence=[edge]))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["value"],"10")
        self.assertEqual(
            out["claim"]["kind"],
            "CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE",
        )
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["search_authority"])

    def test_unsupported_evidence_leaves_field_open(self):
        bad={
            "schema":EDGE_SCHEMA,
            "proof_class":"MODEL_GUESS",
        }
        out=discover(discovery_case(evidence=[bad]))
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "OPEN__NO_AUTHENTICATED_FIELD_PROOF_DISCOVERED",
        )
        self.assertEqual(out["authenticated_relation_evidence_count"],0)

    def test_two_different_proved_values_fail_closed(self):
        source="Threshold is ten."
        scope="discover:test"
        left=mention("A",scope,source)
        e10=bounded_edge(
            source_id=left,
            target_id=field_concept_id(
                scope_id=scope,effect_id="A.t",field="value",value="10"
            ),
            scope=scope,
        )
        e11=bounded_edge(
            source_id=left,
            target_id=field_concept_id(
                scope_id=scope,effect_id="A.t",field="value",value="11"
            ),
            scope=scope,
        )
        out=discover(discovery_case(evidence=[e10,e11]))
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__MULTIPLE_PROVED_FIELD_VALUES",
        )
        self.assertEqual(set(out["proved_values"]),{"10","11"})

    def test_same_value_multiple_proofs_selects_deterministically(self):
        source="Threshold is ten."
        scope="discover:test"
        left=mention("A",scope,source)
        target=field_concept_id(
            scope_id=scope,effect_id="A.t",field="value",value="10"
        )
        short=bounded_edge(
            source_id=left,target_id=target,scope=scope
        )
        long=bounded_edge(
            source_id=left,target_id=target,scope=scope,
            members_source=("a","b"),members_target=("a","b"),
        )
        out=discover(discovery_case(values=("10",),evidence=[long,short]))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["value"],"10")
        self.assertEqual(out["proved_candidate_count"],2)

    def test_invalid_candidate_value_does_not_gain_authority(self):
        problem=discovery_case(values=(object(),),evidence=[])
        out=discover(problem)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_discovered_claim_closes_existing_v8_lattice(self):
        natural="Threshold is ten."
        scope="discover:test"
        source="\n".join([
            "Effect IDs only for threshold: A.t.",
            'Effect field: {"effect_id":"A.t","field":"effect_class","value":"DEFINE"}',
            'Effect field: {"effect_id":"A.t","field":"conditions","value":{}}',
            'Effect field: {"effect_id":"A.t","field":"valid_from","value":null}',
            'Effect field: {"effect_id":"A.t","field":"valid_until","value":null}',
            'Effect field: {"effect_id":"A.t","field":"supersedes","value":[]}',
            natural,
        ])
        start=source.index(natural)
        left=mention("A",scope,natural)
        target=field_concept_id(
            scope_id=scope,effect_id="A.t",field="value",value="10"
        )
        edge=bounded_edge(
            source_id=left,target_id=target,scope=scope
        )
        found=discover({
            "schema":SCHEMA,
            "source_id":"A",
            "source_text":source,
            "scope_id":scope,
            "effect_id":"A.t",
            "field":"value",
            "candidate_spans":[[start,start+len(natural)]],
            "candidate_values":["10","11"],
            "relation_evidence_candidates":[edge],
        })
        self.assertTrue(found["pass"],found)

        problem={
            "schema":LATTICE_SCHEMA,
            "case_id":"discover-lattice",
            "source_documents":[{
                "document_id":"A",
                "source_id":"A",
                "source_text":source,
                "claims":[found["claim"]],
            }],
            "query":{
                "target_id":"threshold",
                "as_of":"2026-10-10",
                "context":{},
            },
        }
        out=evaluate_lattice(problem)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")


if __name__=="__main__":
    unittest.main()
