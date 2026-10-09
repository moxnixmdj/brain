from __future__ import annotations

import hashlib
import json
import unittest

from canonical.runtime import semantic_relation_control_v1
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA as DAG_EVIDENCE_SCHEMA,
    evidence_sha256 as dag_evidence_sha256,
)
from canonical.runtime.authenticated_source_phrase_atom_bridge_v1 import (
    AUTHORITY_SCHEMA,
    LEXICON_SCHEMA,
    lexicon_sha256,
    resolve,
    verify_source_atom_receipt,
)
from canonical.runtime.source_aligned_definitional_entailment_v1 import (
    CONCEPT_DEFINITION_AUTHORITY_SCHEMA,
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


def lexicon():
    return {
        "schema": LEXICON_SCHEMA,
        "lexicon_id": "finance-capital-atoms-v1",
        "scope_id": SCOPE,
        "bounded_finite_lexicon": True,
        "entries": [
            {
                "entry_id": "composition-cet1",
                "surfaces": ["composed entirely of CET1"],
                "atom_id": "composition.CET1",
            },
            {
                "entry_id": "above-minimum",
                "surfaces": ["above the minimum capital requirement"],
                "atom_id": "position.above_minimum",
            },
            {
                "entry_id": "loss-absorption",
                "surfaces": ["absorbs losses"],
                "atom_id": "function.loss_absorption",
            },
            {
                "entry_id": "going-concern",
                "surfaces": ["going concern"],
                "atom_id": "regime.going_concern",
            },
        ],
    }


def authority_verifier_for(value):
    digest = lexicon_sha256(value)

    def verify(_receipt):
        return {
            "pass": True,
            "schema": AUTHORITY_SCHEMA,
            "lexicon_id": value["lexicon_id"],
            "scope_id": value["scope_id"],
            "lexicon_sha256": digest,
            "surface_to_atom_semantics_authenticated": True,
            "lexicon_scope_authenticated": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "a" * 64,
        }

    return verify


def concept_definition():
    return {
        "scope_id": SCOPE,
        "concept_id": "CCOB",
        "definition_kind": "EXACT_CONJUNCTION",
        "definition_atoms": [
            "composition.CET1",
            "position.above_minimum",
            "function.loss_absorption",
            "regime.going_concern",
        ],
    }


def concept_definition_verifier(_receipt):
    value = concept_definition()
    return {
        "pass": True,
        "schema": CONCEPT_DEFINITION_AUTHORITY_SCHEMA,
        **value,
        "definition_sha256": definition_sha256(value),
        "definition_semantics_authenticated": True,
        "verification_authority_mutated": False,
        "receipt_sha256": "b" * 64,
    }


class Tests(unittest.TestCase):
    def test_exact_authenticated_phrases_emit_source_atoms(self):
        value = lexicon()
        out = resolve(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            lexicon=value,
            authority_receipt={"candidate": True},
            authority_verifier=authority_verifier_for(value),
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            set(out["proved_atom_ids"]),
            {
                "composition.CET1",
                "position.above_minimum",
                "function.loss_absorption",
                "regime.going_concern",
            },
        )
        self.assertEqual(len(out["source_atom_receipts"]), 4)
        self.assertTrue(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_unauthenticated_lexicon_cannot_mint_atoms(self):
        out = resolve(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            lexicon=lexicon(),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__AUTHENTICATED_PHRASE_LEXICON_REQUIRED",
        )
        self.assertEqual(out["proved_atom_ids"], [])
        self.assertFalse(out["semantic_truth_authority"])

    def test_unknown_phrase_remains_unresolved_not_negative(self):
        value = lexicon()
        out = resolve(
            raw_span="The cushion is substantial.",
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            lexicon=value,
            authority_receipt={"candidate": True},
            authority_verifier=authority_verifier_for(value),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "UNRESOLVED__NO_AUTHENTICATED_PHRASE_MATCH")
        self.assertEqual(out["proved_atom_ids"], [])
        self.assertFalse(out["absence_proves_negative"])

    def test_surface_does_not_match_inside_larger_word(self):
        value = {
            "schema": LEXICON_SCHEMA,
            "lexicon_id": "boundary-v1",
            "scope_id": SCOPE,
            "bounded_finite_lexicon": True,
            "entries": [
                {
                    "entry_id": "loss",
                    "surfaces": ["loss"],
                    "atom_id": "token.loss",
                }
            ],
        }
        out = resolve(
            raw_span="The glossless token is unrelated.",
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            lexicon=value,
            authority_receipt={"candidate": True},
            authority_verifier=authority_verifier_for(value),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["proved_atom_ids"], [])

    def test_conflicting_surface_to_atom_mapping_fails_closed(self):
        value = lexicon()
        value["entries"].append(
            {
                "entry_id": "bad-collision",
                "surfaces": ["absorbs losses"],
                "atom_id": "different.meaning",
            }
        )
        out = resolve(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            lexicon=value,
            authority_receipt={"candidate": True},
            authority_verifier=authority_verifier_for(value),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("SURFACE_SEMANTIC_COLLISION", out["reason"])

    def test_wrong_authority_scope_fails_closed(self):
        value = lexicon()

        def wrong(_receipt):
            out = authority_verifier_for(value)({}) 
            out["scope_id"] = "wrong"
            return out

        out = resolve(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            lexicon=value,
            authority_receipt={"candidate": True},
            authority_verifier=wrong,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED__PHRASE_LEXICON_AUTHORITY_INVALID")

    def test_source_atom_receipt_reverification_detects_tamper(self):
        value = lexicon()
        out = resolve(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            lexicon=value,
            authority_receipt={"candidate": True},
            authority_verifier=authority_verifier_for(value),
        )
        receipt = dict(out["source_atom_receipts"][0])
        receipt["atom_id"] = "tampered.atom"
        checked = verify_source_atom_receipt(
            receipt,
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            lexicon=value,
            authority_receipt={"candidate": True},
            authority_verifier=authority_verifier_for(value),
        )
        self.assertFalse(checked["pass"])

    def test_phrase_atoms_feed_nonexplicit_concept_entailment(self):
        value = lexicon()
        bridge = resolve(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            lexicon=value,
            authority_receipt={"candidate": True},
            authority_verifier=authority_verifier_for(value),
        )
        self.assertTrue(bridge["pass"], bridge)

        def atom_verifier(receipt):
            return verify_source_atom_receipt(
                receipt,
                raw_span=RAW,
                source_id=SOURCE_ID,
                scope_id=SCOPE,
                lexicon=value,
                authority_receipt={"candidate": True},
                authority_verifier=authority_verifier_for(value),
            )

        relation = prove(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            left_id="mention:loss-absorbing-cushion",
            right_id="CCOB",
            source_atom_receipts=bridge["source_atom_receipts"],
            source_atom_verifier=atom_verifier,
            concept_definition_receipt={"candidate": True},
            concept_definition_verifier=concept_definition_verifier,
        )
        self.assertTrue(relation["pass"], relation)
        self.assertTrue(relation["left_entails_right"])
        self.assertEqual(
            relation["strongest_proved_relation"],
            "LEFT_ENTAILS_RIGHT",
        )

    def test_full_phrase_to_relation_controller_chain(self):
        value = lexicon()
        bridge = resolve(
            raw_span=RAW,
            source_id=SOURCE_ID,
            scope_id=SCOPE,
            lexicon=value,
            authority_receipt={"candidate": True},
            authority_verifier=authority_verifier_for(value),
        )

        def atom_verifier(receipt):
            return verify_source_atom_receipt(
                receipt,
                raw_span=RAW,
                source_id=SOURCE_ID,
                scope_id=SCOPE,
                lexicon=value,
                authority_receipt={"candidate": True},
                authority_verifier=authority_verifier_for(value),
            )

        edge = {
            "relation": "ENTAILS",
            "source_id": "mention:loss-absorbing-cushion",
            "target_id": "CCOB",
            "scope_id": SCOPE,
            "raw_span": RAW,
            "raw_source_id": SOURCE_ID,
            "source_atom_receipts": bridge["source_atom_receipts"],
            "concept_definition_receipt": {"candidate": True},
        }

        def edge_verifier(receipt):
            return verify_relation_edge(
                receipt,
                source_atom_verifier=atom_verifier,
                concept_definition_verifier=concept_definition_verifier,
            )

        dag = {
            "schema": DAG_EVIDENCE_SCHEMA,
            "scope_id": SCOPE,
            "left_id": edge["source_id"],
            "right_id": edge["target_id"],
            "entailment_receipts": [edge],
            "counterexample_receipts": [],
        }
        out = semantic_relation_control_v1.resolve(
            {
                "left_id": edge["source_id"],
                "right_id": edge["target_id"],
                "left_surface": "loss-absorbing cushion",
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
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
