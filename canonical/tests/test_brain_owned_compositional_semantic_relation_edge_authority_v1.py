from __future__ import annotations

import json
import unittest

from canonical.runtime.bounded_participial_disposition_v1 import SEMANTIC_ATOM
from canonical.runtime.source_aligned_semantic_edge_authority_v1 import (
    EVIDENCE_SCHEMA,
    RECEIPT_SCHEMA,
)
from canonical.runtime.brain_owned_concept_semantics_authority_v1 import (
    EVIDENCE_SCHEMA as CONCEPT_EVIDENCE_SCHEMA,
)
from canonical.runtime import (
    brain_owned_compositional_semantic_relation_edge_authority_v1 as authority,
)


RAW="loss-absorbing cushion"
SOURCE="doc:A"
SCOPE="finance:regcap:2026"
TARGET="LOSS_ABSORPTION_DISPOSITION"


def canon(v):
    return json.dumps(
        v,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False,
    )


def formula(atom=SEMANTIC_ATOM):
    return {"op":"ATOM","id":atom}


def concept_source(f=None):
    f=f or formula()
    return "Concept semantics: "+canon({
        "concept_id":TARGET,
        "formula":f,
        "scope_id":SCOPE,
    })


def evidence(*,direction="SOURCE_TO_TARGET",target_formula=None,declared_formula=None):
    target_formula=target_formula or formula()
    declared_formula=declared_formula or target_formula
    return {
        "schema":EVIDENCE_SCHEMA,
        "raw_span":RAW,
        "source_id":SOURCE,
        "scope_id":SCOPE,
        "target_concept_id":TARGET,
        "direction":direction,
        "source_claims":[{
            "claim_id":"participial",
            "kind":"CERTIFIED_PARTICIPIAL_DISPOSITION",
            "start":0,
            "end":len(RAW),
        }],
        "target_formula":target_formula,
        "concept_semantics_receipt":{
            "schema":CONCEPT_EVIDENCE_SCHEMA,
            "scope_id":SCOPE,
            "concept_id":TARGET,
            "formula":declared_formula,
            "source":{
                "source_id":"concept-doc",
                "scope_id":SCOPE,
                "source_text":concept_source(declared_formula),
            },
        },
    }


class Tests(unittest.TestCase):
    def test_participial_source_composes_to_semantic_concept(self):
        raw=evidence()
        self.assertTrue(authority.supports(raw))
        out=authority.verify(raw)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["schema"],RECEIPT_SCHEMA)
        self.assertEqual(out["relation"],"ENTAILS")
        self.assertTrue(out["source_id"].startswith("MENTION:"))
        self.assertEqual(out["target_id"],TARGET)
        self.assertEqual(
            out["proof_class"],
            "COMPOSITIONAL_SOURCE_TO_CONCEPT",
        )

    def test_target_formula_mismatch_does_not_prove_edge(self):
        raw=evidence(
            target_formula=formula(),
            declared_formula=formula("OTHER"),
        )
        out=authority.verify(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"COMPOSITIONAL_ENTAILMENT_NOT_PROVED")

    def test_unrecognized_source_primitive_does_not_prove_edge(self):
        raw=evidence()
        raw["raw_span"]="ordinary cushion"
        raw["source_claims"][0]["end"]=len("ordinary cushion")
        out=authority.verify(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"COMPOSITIONAL_ENTAILMENT_NOT_PROVED")

    def test_reverse_direction_is_unsupported(self):
        raw=evidence(direction="TARGET_TO_SOURCE")
        self.assertFalse(authority.supports(raw))
        out=authority.verify(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "DIRECTION_UNSUPPORTED_WITHOUT_SOURCE_COMPLETENESS_AUTHORITY",
        )


if __name__=="__main__":
    unittest.main()
