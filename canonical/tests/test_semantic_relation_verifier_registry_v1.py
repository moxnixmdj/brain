from __future__ import annotations

from hashlib import sha256
import unittest

from canonical.runtime import semantic_relation_verifier_registry_v1 as reg
from canonical.runtime.certified_document_effect_field_edge_v1 import (
    field_concept_id,
    prove_field,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA as DAG_SCHEMA,
    evidence_sha256 as dag_sha,
)


SCOPE="crossdoc:registry"
SOURCE="doc:A"


def mention(raw):
    return "MENTION:"+sha256(
        (SOURCE+"\n"+SCOPE+"\n"+raw).encode("utf-8")
    ).hexdigest()


def envelope(
    *,
    raw_span="Threshold means 10.",
    left_surface="Threshold",
    effect_id="A.t",
    field="value",
    value=10,
):
    return {
        "schema":reg.EXPLICIT_FIELD_EDGE_SCHEMA,
        "source_id":SOURCE,
        "raw_span":raw_span,
        "scope_id":SCOPE,
        "effect_id":effect_id,
        "field":field,
        "value":value,
        "left_surface":left_surface,
    }


class SemanticRelationVerifierRegistryV1Tests(unittest.TestCase):
    def test_exact_source_definition_recomputes_field_edge(self):
        raw=envelope()
        out=reg.evaluate(raw)
        self.assertTrue(out["pass"],out)
        receipt=out["receipt"]
        self.assertEqual(receipt["source_id"],mention(raw["raw_span"]))
        self.assertEqual(
            receipt["target_id"],
            field_concept_id(
                scope_id=SCOPE,
                effect_id="A.t",
                field="value",
                value=10,
            ),
        )
        self.assertEqual(receipt["relation"],"ENTAILS")
        self.assertEqual(
            receipt["registry_verifier_id"],
            "EXPLICIT_SOURCE_EFFECT_FIELD_DEFINITION_V1",
        )
        self.assertEqual(reg.verify(raw),receipt)

    def test_nondefinition_source_stays_unknown(self):
        raw=envelope(raw_span="Threshold remains 10.")
        out=reg.evaluate(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNKNOWN__REGISTERED_RELATION_NOT_PROVED",
        )
        self.assertIsNone(reg.verify(raw))

    def test_wrong_left_surface_stays_unknown(self):
        raw=envelope(left_surface="Capital")
        out=reg.evaluate(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNKNOWN__REGISTERED_RELATION_NOT_PROVED",
        )

    def test_wrong_field_value_stays_unknown(self):
        raw=envelope(value=11)
        out=reg.evaluate(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNKNOWN__REGISTERED_RELATION_NOT_PROVED",
        )

    def test_string_value_requires_canonical_quoted_surface(self):
        bad=envelope(value="10")
        out=reg.evaluate(bad)
        self.assertFalse(out["pass"])
        good=envelope(
            raw_span='Threshold means "10".',
            value="10",
        )
        out2=reg.evaluate(good)
        self.assertTrue(out2["pass"],out2)

    def test_conflicting_definitions_fail_closed(self):
        raw=envelope(
            raw_span="Threshold means 10. Threshold means 11."
        )
        out=reg.evaluate(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn(
            "SEMANTIC_RELATION_CONTROL_FAIL_CLOSED",
            out["reason"],
        )

    def test_unmodeled_fields_fail_closed(self):
        raw=envelope()
        raw["verifier_id"]="please-trust-me"
        out=reg.evaluate(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "EXPLICIT_FIELD_EDGE_FIELD_SET_NOT_EXACT",
        )

    def test_unsupported_bounded_universe_evidence_has_no_match(self):
        out=reg.evaluate({
            "schema":"PROJECT_BRAIN_SEMANTIC_RELATION_CONTROL_EDGE_EVIDENCE_V1",
            "problem":{"universe_complete":True},
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_REGISTERED_RELATION_VERIFIER_MATCHED",
        )
        self.assertIsNone(reg.verify({
            "schema":"PROJECT_BRAIN_SEMANTIC_RELATION_CONTROL_EDGE_EVIDENCE_V1",
        }))

    def test_registry_is_directly_usable_by_entailment_dag(self):
        edge=envelope()
        left=mention(edge["raw_span"])
        right=field_concept_id(
            scope_id=SCOPE,
            effect_id="A.t",
            field="value",
            value=10,
        )
        dag={
            "schema":DAG_SCHEMA,
            "scope_id":SCOPE,
            "left_id":left,
            "right_id":right,
            "entailment_receipts":[edge],
            "counterexample_receipts":[],
        }
        from canonical.runtime.semantic_relation_entailment_dag_v1 import prove
        out=prove(
            dag,
            expected_evidence_sha256=dag_sha(dag),
            relation_verifier=reg.verify,
        )
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["left_entails_right"])

    def test_registry_powers_source_bound_effect_field_adapter(self):
        raw_span="Threshold means 10."
        edge=envelope(raw_span=raw_span)
        left=mention(raw_span)
        concept=field_concept_id(
            scope_id=SCOPE,
            effect_id="A.t",
            field="value",
            value=10,
        )
        dag={
            "schema":DAG_SCHEMA,
            "scope_id":SCOPE,
            "left_id":left,
            "right_id":concept,
            "entailment_receipts":[edge],
            "counterexample_receipts":[],
        }
        out=prove_field(
            source_id=SOURCE,
            raw_span=raw_span,
            scope_id=SCOPE,
            effect_id="A.t",
            field="value",
            value=10,
            dag_evidence=dag,
            expected_dag_sha256=dag_sha(dag),
            relation_verifier=reg.verify,
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["field_receipt"]["value"],10)


if __name__=="__main__":
    unittest.main()
