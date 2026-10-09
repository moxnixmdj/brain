from __future__ import annotations

from hashlib import sha256
import unittest

from canonical.runtime import semantic_relation_verifier_registry_v1 as reg
from canonical.runtime.bounded_semantic_relation_proof_v1 import (
    EVIDENCE_SCHEMA as BOUNDED_SCHEMA,
    evidence_sha256 as bounded_sha,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA as DAG_SCHEMA,
    evidence_sha256 as dag_sha,
)
from canonical.runtime.certified_document_effect_field_edge_v1 import (
    field_concept_id,
    prove_field,
)


SCOPE="crossdoc:registry"


def bounded(left_id,right_id,left_members,right_members):
    return {
        "schema":BOUNDED_SCHEMA,
        "scope_id":SCOPE,
        "left_id":left_id,
        "right_id":right_id,
        "universe_complete":True,
        "left_extension_complete":True,
        "right_extension_complete":True,
        "universe":["a","b","c"],
        "left_members":list(left_members),
        "right_members":list(right_members),
    }


def envelope(
    left_id,
    right_id,
    *,
    relation="ENTAILS",
    left_members=("a",),
    right_members=("a","b"),
):
    e=bounded(left_id,right_id,left_members,right_members)
    problem={
        "left_id":left_id,
        "right_id":right_id,
        "left_surface":left_id,
        "right_surface":right_id,
        "scope_id":SCOPE,
        "required_relation":"LEFT_ENTAILS_RIGHT",
        "bounded_extension_evidence":e,
        "expected_bounded_extension_sha256":bounded_sha(e),
    }
    return {
        "schema":reg.CONTROL_EDGE_EVIDENCE_SCHEMA,
        "relation":relation,
        "problem":problem,
        "expected_problem_sha256":reg.evidence_sha256(problem),
    }


def mention(source,scope,raw):
    return "MENTION:"+sha256(
        (source+"\n"+scope+"\n"+raw).encode("utf-8")
    ).hexdigest()


class SemanticRelationVerifierRegistryV1Tests(unittest.TestCase):
    def test_bounded_left_subset_recomputes_entailment_receipt(self):
        raw=envelope("L","R")
        out=reg.evaluate(raw)
        self.assertTrue(out["pass"],out)
        receipt=out["receipt"]
        self.assertEqual(receipt["relation"],"ENTAILS")
        self.assertEqual(receipt["source_id"],"L")
        self.assertEqual(receipt["target_id"],"R")
        self.assertEqual(
            receipt["registry_verifier_id"],
            "SEMANTIC_RELATION_CONTROL_EDGE_V1",
        )
        self.assertFalse(receipt.get("terminal_authority",False))
        self.assertEqual(reg.verify(raw),receipt)

    def test_bounded_counterexample_recomputes_not_entails_receipt(self):
        raw=envelope(
            "L","R",
            relation="NOT_ENTAILS",
            left_members=("a","b"),
            right_members=("a",),
        )
        out=reg.evaluate(raw)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["receipt"]["relation"],"NOT_ENTAILS")
        self.assertTrue(
            out["control_result"]["required_relation_disproved"]
        )

    def test_unproved_relation_returns_no_authority(self):
        raw=envelope(
            "L","R",
            relation="ENTAILS",
            left_members=("a","b"),
            right_members=("b","c"),
        )
        out=reg.evaluate(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNKNOWN__REGISTERED_RELATION_NOT_PROVED",
        )
        self.assertIsNone(reg.verify(raw))

    def test_problem_content_address_drift_fails_closed(self):
        raw=envelope("L","R")
        raw["problem"]["left_surface"]="changed"
        out=reg.evaluate(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "CONTROL_PROBLEM_CONTENT_ADDRESS_MISMATCH",
        )
        self.assertIsNone(reg.verify(raw))

    def test_callback_dependent_relation_control_branch_is_forbidden(self):
        raw=envelope("L","R")
        raw["problem"]["entailment_dag_evidence"]={"candidate":True}
        raw["problem"]["expected_entailment_dag_sha256"]="0"*64
        raw["expected_problem_sha256"]=reg.evidence_sha256(raw["problem"])
        out=reg.evaluate(raw)
        self.assertFalse(out["pass"])
        self.assertIn(
            "CONTROL_PROBLEM_REQUIRES_EXTERNAL_VERIFIER",
            out["reason"],
        )

    def test_candidate_similarity_cannot_mint_registry_edge(self):
        raw=envelope(
            "L","R",
            left_members=("a",),
            right_members=("b",),
        )
        raw["problem"]["candidate_relations"]=[
            {"relation":"SIMILAR","score":0.9999}
        ]
        raw["expected_problem_sha256"]=reg.evidence_sha256(raw["problem"])
        out=reg.evaluate(raw)
        self.assertFalse(out["pass"])
        self.assertIsNone(reg.verify(raw))

    def test_unsupported_schema_has_no_registry_match(self):
        out=reg.evaluate({"schema":"UNKNOWN"})
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_REGISTERED_RELATION_VERIFIER_MATCHED",
        )
        self.assertIsNone(reg.verify({"schema":"UNKNOWN"}))

    def test_registry_is_directly_usable_by_entailment_dag(self):
        left="L"
        right="R"
        edge=envelope(left,right)
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

    def test_registry_can_power_source_bound_effect_field_adapter(self):
        source="doc:A"
        raw_span="Threshold is ten."
        left=mention(source,SCOPE,raw_span)
        concept=field_concept_id(
            scope_id=SCOPE,
            effect_id="A.t",
            field="value",
            value="10",
        )
        edge=envelope(left,concept)
        dag={
            "schema":DAG_SCHEMA,
            "scope_id":SCOPE,
            "left_id":left,
            "right_id":concept,
            "entailment_receipts":[edge],
            "counterexample_receipts":[],
        }
        out=prove_field(
            source_id=source,
            raw_span=raw_span,
            scope_id=SCOPE,
            effect_id="A.t",
            field="value",
            value="10",
            dag_evidence=dag,
            expected_dag_sha256=dag_sha(dag),
            relation_verifier=reg.verify,
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(
            out["field_receipt"]["value"],
            "10",
        )


if __name__=="__main__":
    unittest.main()
