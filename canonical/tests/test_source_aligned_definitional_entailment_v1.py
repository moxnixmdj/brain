from __future__ import annotations

import hashlib
import json
import unittest

from canonical.runtime import semantic_relation_control_v1
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA as DAG_EVIDENCE_SCHEMA,
    evidence_sha256 as dag_evidence_sha256,
)
from canonical.runtime.source_aligned_definitional_entailment_v1 import (
    CONCEPT_DEFINITION_AUTHORITY_SCHEMA,
    SOURCE_ATOM_AUTHORITY_SCHEMA,
    SOURCE_COMPLETENESS_AUTHORITY_SCHEMA,
    RELATION_EDGE_AUTHORITY_SCHEMA,
    definition_sha256,
    prove,
    verify_relation_edge,
)


RAW = (
    "The cushion is composed entirely of CET1, sits above the minimum capital "
    "requirement, and absorbs losses while the bank remains a going concern."
)
SOURCE_ID = "doc:A"
SCOPE = "finance:regulatory-capital:2026"
LEFT = "mention:loss-absorbing-cushion"
RIGHT = "CCOB"


def source_atom_verifier(receipt):
    atom = receipt["atom_id"]
    return {
        "pass": True,
        "schema": SOURCE_ATOM_AUTHORITY_SCHEMA,
        "source_id": SOURCE_ID,
        "scope_id": SCOPE,
        "raw_span_sha256": hashlib.sha256(RAW.encode()).hexdigest(),
        "atom_id": atom,
        "source_semantics_authenticated": True,
        "verification_authority_mutated": False,
        "receipt_sha256": hashlib.sha256(("source:" + atom).encode()).hexdigest(),
    }


def concept_definition():
    return {
        "scope_id": SCOPE,
        "concept_id": RIGHT,
        "definition_kind": "EXACT_CONJUNCTION",
        "definition_atoms": [
            "composition.CET1",
            "position.above_minimum",
            "function.loss_absorption",
            "regime.going_concern",
        ],
    }


def concept_definition_verifier(receipt):
    definition = concept_definition()
    return {
        "pass": True,
        "schema": CONCEPT_DEFINITION_AUTHORITY_SCHEMA,
        **definition,
        "definition_sha256": definition_sha256(definition),
        "definition_semantics_authenticated": True,
        "verification_authority_mutated": False,
        "receipt_sha256": "a" * 64,
    }


def source_completeness_verifier(receipt):
    atoms = sorted(receipt["source_atom_ids"])
    payload = {
        "source_id": SOURCE_ID,
        "scope_id": SCOPE,
        "raw_span_sha256": hashlib.sha256(RAW.encode()).hexdigest(),
        "source_atom_ids": atoms,
    }
    return {
        "pass": True,
        "schema": SOURCE_COMPLETENESS_AUTHORITY_SCHEMA,
        **payload,
        "source_atom_set_sha256": hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "exact_conjunctive_source_semantics_complete": True,
        "verification_authority_mutated": False,
        "receipt_sha256": "b" * 64,
    }


def atom_receipts(*atoms):
    return [{"atom_id": atom} for atom in atoms]


class Tests(unittest.TestCase):
    def test_nonexplicit_source_properties_prove_left_entails_concept(self):
        definition = concept_definition()
        out = prove(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            left_id=LEFT,
            right_id=RIGHT,
            source_atom_receipts=atom_receipts(*definition["definition_atoms"]),
            source_atom_verifier=source_atom_verifier,
            concept_definition_receipt={"candidate": True},
            concept_definition_verifier=concept_definition_verifier,
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["left_entails_right"])
        self.assertFalse(out["right_entails_left"])
        self.assertEqual(out["strongest_proved_relation"], "LEFT_ENTAILS_RIGHT")
        self.assertFalse(out["source_semantics_complete"])

    def test_missing_required_atom_stays_unknown_not_false(self):
        definition = concept_definition()
        out = prove(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            left_id=LEFT,
            right_id=RIGHT,
            source_atom_receipts=atom_receipts(*definition["definition_atoms"][:-1]),
            source_atom_verifier=source_atom_verifier,
            concept_definition_receipt={"candidate": True},
            concept_definition_verifier=concept_definition_verifier,
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["left_entails_right"])
        self.assertFalse(out["left_entails_right_disproved"])
        self.assertEqual(out["strongest_proved_relation"], "UNKNOWN")
        self.assertEqual(out["missing_target_atoms"], ["regime.going_concern"])

    def test_exact_source_completeness_plus_equal_atoms_proves_equivalence(self):
        definition = concept_definition()
        receipts = atom_receipts(*definition["definition_atoms"])
        out = prove(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            left_id=LEFT,
            right_id=RIGHT,
            source_atom_receipts=receipts,
            source_atom_verifier=source_atom_verifier,
            concept_definition_receipt={"candidate": True},
            concept_definition_verifier=concept_definition_verifier,
            source_completeness_receipt={
                "source_atom_ids": definition["definition_atoms"],
            },
            source_completeness_verifier=source_completeness_verifier,
        )
        self.assertTrue(out["logical_equivalence_in_scope"], out)
        self.assertEqual(
            out["strongest_proved_relation"],
            "LOGICAL_EQUIVALENCE_IN_SCOPE",
        )

    def test_complete_source_with_extra_property_is_narrower_than_concept(self):
        definition = concept_definition()
        source_atoms = definition["definition_atoms"] + ["institution.bank_only"]
        out = prove(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            left_id=LEFT,
            right_id=RIGHT,
            source_atom_receipts=atom_receipts(*source_atoms),
            source_atom_verifier=source_atom_verifier,
            concept_definition_receipt={"candidate": True},
            concept_definition_verifier=concept_definition_verifier,
            source_completeness_receipt={"source_atom_ids": source_atoms},
            source_completeness_verifier=source_completeness_verifier,
        )
        self.assertTrue(out["left_entails_right"])
        self.assertFalse(out["right_entails_left"])
        self.assertEqual(out["source_only_atoms"], ["institution.bank_only"])

    def test_unverified_source_atom_receipt_fails_closed(self):
        def bad(_receipt):
            return {
                "pass": True,
                "schema": SOURCE_ATOM_AUTHORITY_SCHEMA,
                "source_id": "wrong",
                "scope_id": SCOPE,
                "raw_span_sha256": hashlib.sha256(RAW.encode()).hexdigest(),
                "atom_id": "composition.CET1",
                "source_semantics_authenticated": True,
                "verification_authority_mutated": False,
                "receipt_sha256": "c" * 64,
            }

        out = prove(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            left_id=LEFT,
            right_id=RIGHT,
            source_atom_receipts=[{"atom_id": "composition.CET1"}],
            source_atom_verifier=bad,
            concept_definition_receipt={"candidate": True},
            concept_definition_verifier=concept_definition_verifier,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("SOURCE_ATOM_RECEIPT_BINDING_INVALID", out["reason"])

    def test_wrong_scope_concept_definition_fails_closed(self):
        def bad_definition(_receipt):
            definition = concept_definition()
            definition["scope_id"] = "wrong"
            return {
                "pass": True,
                "schema": CONCEPT_DEFINITION_AUTHORITY_SCHEMA,
                **definition,
                "definition_sha256": definition_sha256(definition),
                "definition_semantics_authenticated": True,
                "verification_authority_mutated": False,
                "receipt_sha256": "d" * 64,
            }

        out = prove(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            left_id=LEFT,
            right_id=RIGHT,
            source_atom_receipts=[],
            source_atom_verifier=source_atom_verifier,
            concept_definition_receipt={"candidate": True},
            concept_definition_verifier=bad_definition,
        )
        self.assertFalse(out["pass"])
        self.assertIn("CONCEPT_DEFINITION_BINDING_INVALID", out["reason"])

    def test_source_completeness_cannot_claim_unproved_atom(self):
        definition = concept_definition()
        proved = definition["definition_atoms"][:-1]
        out = prove(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            left_id=LEFT,
            right_id=RIGHT,
            source_atom_receipts=atom_receipts(*proved),
            source_atom_verifier=source_atom_verifier,
            concept_definition_receipt={"candidate": True},
            concept_definition_verifier=concept_definition_verifier,
            source_completeness_receipt={
                "source_atom_ids": definition["definition_atoms"],
            },
            source_completeness_verifier=source_completeness_verifier,
        )
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_COMPLETENESS_CONTAINS_UNPROVED_ATOMS", out["reason"])

    def test_entails_edge_receipt_is_compatible_with_relation_dag_contract(self):
        definition = concept_definition()
        out = verify_relation_edge(
            {
                "relation": "ENTAILS",
                "source_id": LEFT,
                "target_id": RIGHT,
                "scope_id": SCOPE,
                "raw_span": RAW,
                "raw_source_id": SOURCE_ID,
                "source_atom_receipts": atom_receipts(*definition["definition_atoms"]),
                "concept_definition_receipt": {"candidate": True},
            },
            source_atom_verifier=source_atom_verifier,
            concept_definition_verifier=concept_definition_verifier,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["schema"], RELATION_EDGE_AUTHORITY_SCHEMA)
        self.assertEqual(out["relation"], "ENTAILS")
        self.assertEqual(out["source_id"], LEFT)
        self.assertEqual(out["target_id"], RIGHT)
        self.assertTrue(out["source_semantics_authenticated"])
        self.assertTrue(out["target_semantics_authenticated"])
        self.assertTrue(out["relation_semantics_authenticated"])
        self.assertEqual(len(out["evidence_sha256"]), 64)
        self.assertEqual(len(out["receipt_sha256"]), 64)

    def test_not_entails_edge_requires_complete_source_countermodel(self):
        definition = concept_definition()
        proved = definition["definition_atoms"][:-1]
        out = verify_relation_edge(
            {
                "relation": "NOT_ENTAILS",
                "source_id": LEFT,
                "target_id": RIGHT,
                "scope_id": SCOPE,
                "raw_span": RAW,
                "raw_source_id": SOURCE_ID,
                "source_atom_receipts": atom_receipts(*proved),
                "concept_definition_receipt": {"candidate": True},
                "source_completeness_receipt": {"source_atom_ids": proved},
            },
            source_atom_verifier=source_atom_verifier,
            concept_definition_verifier=concept_definition_verifier,
            source_completeness_verifier=source_completeness_verifier,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["relation"], "NOT_ENTAILS")

    def test_not_entails_edge_without_source_completeness_is_not_authorized(self):
        definition = concept_definition()
        proved = definition["definition_atoms"][:-1]
        out = verify_relation_edge(
            {
                "relation": "NOT_ENTAILS",
                "source_id": LEFT,
                "target_id": RIGHT,
                "scope_id": SCOPE,
                "raw_span": RAW,
                "raw_source_id": SOURCE_ID,
                "source_atom_receipts": atom_receipts(*proved),
                "concept_definition_receipt": {"candidate": True},
            },
            source_atom_verifier=source_atom_verifier,
            concept_definition_verifier=concept_definition_verifier,
        )
        self.assertFalse(out["pass"])
        self.assertIn("RELATION_NOT_PROVED", out["reason"])

    def test_existing_semantic_relation_controller_accepts_definitional_edge(self):
        definition = concept_definition()
        edge = {
            "relation": "ENTAILS",
            "source_id": LEFT,
            "target_id": RIGHT,
            "scope_id": SCOPE,
            "raw_span": RAW,
            "raw_source_id": SOURCE_ID,
            "source_atom_receipts": atom_receipts(*definition["definition_atoms"]),
            "concept_definition_receipt": {"candidate": True},
        }
        dag = {
            "schema": DAG_EVIDENCE_SCHEMA,
            "scope_id": SCOPE,
            "left_id": LEFT,
            "right_id": RIGHT,
            "entailment_receipts": [edge],
            "counterexample_receipts": [],
        }

        def edge_verifier(receipt):
            return verify_relation_edge(
                receipt,
                source_atom_verifier=source_atom_verifier,
                concept_definition_verifier=concept_definition_verifier,
            )

        out = semantic_relation_control_v1.resolve(
            {
                "left_id": LEFT,
                "right_id": RIGHT,
                "left_surface": RAW,
                "right_surface": "capital conservation buffer",
                "scope_id": SCOPE,
                "required_relation": "LEFT_ENTAILS_RIGHT",
                "entailment_dag_evidence": dag,
                "expected_entailment_dag_sha256": dag_evidence_sha256(dag),
            },
            relation_edge_verifier=edge_verifier,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "LEFT_ENTAILS_RIGHT")
        self.assertTrue(out["proved_facts"]["left_entails_right"])
        self.assertFalse(out["terminal_authority"])

    def test_no_terminal_or_acceptance_authority(self):
        definition = concept_definition()
        out = prove(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            left_id=LEFT,
            right_id=RIGHT,
            source_atom_receipts=atom_receipts(*definition["definition_atoms"]),
            source_atom_verifier=source_atom_verifier,
            concept_definition_receipt={"candidate": True},
            concept_definition_verifier=concept_definition_verifier,
        )
        self.assertFalse(out["terminal_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
