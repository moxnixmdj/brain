import hashlib
import json
import unittest

from canonical.runtime.bounded_authenticated_concept_universe_v1 import (
    AUTHORITY_SCHEMA,
    REGISTRY_SCHEMA,
)
from canonical.runtime.proof_carrying_domain_mapping_v1 import resolve


SCOPE = "finance:regulatory-capital:2026"
RAW = "loss-absorbing cushion"


def candidates():
    return [
        {
            "concept_id": "CCOB",
            "surface": "capital conservation buffer",
            "required_atoms": ["function.loss_absorption", "regime.going_concern"],
            "forbidden_atoms": ["regime.resolution_only"],
        },
        {
            "concept_id": "TLAC",
            "surface": "total loss-absorbing capacity",
            "required_atoms": ["function.loss_absorption", "regime.resolution"],
        },
    ]


def registry():
    return {
        "schema": REGISTRY_SCHEMA,
        "registry_id": "loss-absorption-registry-v1",
        "scope_id": SCOPE,
        "bounded_finite_registry": True,
        "concepts": [
            {
                "concept_id": "CCOB",
                "surfaces": ["capital conservation buffer", RAW],
                "attributes": {"domain": "prudential"},
                "terminal_signature_complete": True,
                "terminal_signature": {"action": "GOING_CONCERN_BUFFER"},
            },
            {
                "concept_id": "TLAC",
                "surfaces": ["total loss-absorbing capacity", RAW],
                "attributes": {"domain": "resolution"},
                "terminal_signature_complete": True,
                "terminal_signature": {"action": "RESOLUTION_CAPACITY"},
            },
        ],
        "observations": [
            {
                "observation_id": "CHECK_RESOLUTION_REGIME",
                "outcome_map_complete": True,
                "outcomes": {"CCOB": "NO", "TLAC": "YES"},
                "cost_units": 1,
            }
        ],
    }


def registry_verifier_for(reg):
    normalized = {
        "schema": REGISTRY_SCHEMA,
        "registry_id": reg["registry_id"],
        "scope_id": reg["scope_id"],
        "bounded_finite_registry": True,
        "concepts": [
            {
                "concept_id": c["concept_id"],
                "surfaces": sorted(
                    {" ".join(x.strip().split()).casefold() for x in c["surfaces"]}
                ),
                "attributes": dict(c.get("attributes", {})),
                "terminal_signature": dict(c["terminal_signature"]),
            }
            for c in reg["concepts"]
        ],
        "observations": [
            {
                "observation_id": o["observation_id"],
                "outcome_map_complete": True,
                "outcomes": dict(o["outcomes"]),
                "cost_units": float(o["cost_units"]),
            }
            for o in reg["observations"]
        ],
    }
    digest = hashlib.sha256(
        json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()

    def verify(_receipt):
        return {
            "pass": True,
            "schema": AUTHORITY_SCHEMA,
            "registry_sha256": digest,
            "registry_id": reg["registry_id"],
            "scope_id": reg["scope_id"],
            "scope_completeness_authenticated": True,
            "concept_semantics_authenticated": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "a" * 64,
        }

    return verify


def completeness_verifier(source_id, raw_span):
    digest = hashlib.sha256(raw_span.encode()).hexdigest()

    def verify(_receipt):
        return {
            "pass": True,
            "independent_verified": True,
            "source_id": source_id,
            "raw_span_sha256": digest,
            "decision_relevant_semantics_complete": True,
            "verification_authority_mutated": False,
        }

    return verify


class Tests(unittest.TestCase):
    def test_naked_phrase_does_not_force_leaf_mapping(self):
        out = resolve(
            RAW,
            source_id="doc:A",
            scope_id=SCOPE,
            candidate_concepts=candidates(),
            proved_semantic_atoms=["function.loss_absorption"],
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "COMPOSED")
        self.assertTrue(out["opaque_remainder_required"])
        self.assertFalse(out["fully_semantically_bound"])
        self.assertEqual(set(out["surviving_candidates"]), {"CCOB", "TLAC"})

    def test_missing_resolution_is_unknown_not_refutation(self):
        out = resolve(
            RAW,
            source_id="doc:A",
            scope_id=SCOPE,
            candidate_concepts=candidates(),
            evidence=[
                {"atom": "function.loss_absorption", "state": "SUPPORTED"},
            ],
        )
        self.assertIn("TLAC", out["surviving_candidates"])
        tlac = next(
            row for row in out["candidate_evaluations"]
            if row["concept_id"] == "TLAC"
        )
        self.assertIn("regime.resolution", tlac["contract"]["unresolved_atoms"])
        self.assertFalse(tlac["contract"]["contract_refuted"])

    def test_explicit_definition_can_prove_scoped_identity(self):
        out = resolve(
            RAW,
            source_id="doc:A",
            scope_id=SCOPE,
            candidate_concepts=candidates(),
            relation_problems={
                "CCOB": {
                    "required_relation": "SEMANTIC_IDENTITY",
                    "explicit_definition_sources": [
                        {
                            "source_id": "doc:A",
                            "scope_id": SCOPE,
                            "source_text": (
                                "Loss-absorbing cushion means capital conservation buffer."
                            ),
                        }
                    ],
                }
            },
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["status"], "VERIFIED_EXACT")
        self.assertEqual(out["verified_mapping"]["concept_id"], "CCOB")
        self.assertTrue(out["semantic_truth_authority"])
        self.assertTrue(out["opaque_remainder_required"])

    def test_exact_mapping_only_drops_opaque_remainder_with_independent_completeness(self):
        out = resolve(
            RAW,
            source_id="doc:A",
            scope_id=SCOPE,
            candidate_concepts=candidates(),
            relation_problems={
                "CCOB": {
                    "required_relation": "SEMANTIC_IDENTITY",
                    "explicit_definition_sources": [
                        {
                            "source_id": "doc:A",
                            "scope_id": SCOPE,
                            "source_text": (
                                "Loss-absorbing cushion means capital conservation buffer."
                            ),
                        }
                    ],
                }
            },
            source_semantics_completeness_receipt={"candidate": True},
            source_semantics_completeness_verifier=completeness_verifier(
                "doc:A", RAW
            ),
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["fully_semantically_bound"])
        self.assertFalse(out["opaque_remainder_required"])

    def test_lexical_or_model_candidate_cannot_mint_synonymy(self):
        out = resolve(
            RAW,
            source_id="doc:A",
            scope_id=SCOPE,
            candidate_concepts=candidates(),
            proved_semantic_atoms=[
                "embedding.nearest=CCOB",
                "model.guess=CCOB",
            ],
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "COMPOSED")
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["candidate_relations_are_authority"])

    def test_same_terminal_behavior_does_not_prove_semantic_identity(self):
        preliminary = resolve(
            RAW,
            source_id="doc:A",
            scope_id=SCOPE,
            candidate_concepts=candidates(),
        )
        mention_id = preliminary["mention_id"]
        out = resolve(
            RAW,
            source_id="doc:A",
            scope_id=SCOPE,
            candidate_concepts=candidates(),
            relation_problems={
                "CCOB": {
                    "required_relation": "SEMANTIC_IDENTITY",
                    "terminal_signature_rows": [
                        {
                            "raw_id": mention_id,
                            "signature_complete": True,
                            "terminal_signature": {"action": "SAME"},
                        },
                        {
                            "raw_id": "CCOB",
                            "signature_complete": True,
                            "terminal_signature": {"action": "SAME"},
                        },
                    ],
                }
            },
        )
        self.assertFalse(out["pass"], out)
        relation = next(
            row for row in out["candidate_evaluations"]
            if row["concept_id"] == "CCOB"
        )["relation_result"]
        self.assertFalse(relation["pass"])
        self.assertIn(
            relation["status"],
            {
                "FAIL_CLOSED__TERMINAL_SIGNATURE_AUTHORITY_INVALID",
                "OPEN__REQUIRED_RELATION_UNPROVED",
                "OPEN__REQUIRED_SEMANTIC_RELATION_NOT_PROVED",
            },
        )
        self.assertIsNone(out["verified_mapping"])
        self.assertFalse(out["semantic_truth_authority"])

    def test_authenticated_registry_preserves_all_ambiguous_candidates_and_discriminator(self):
        reg = registry()
        out = resolve(
            RAW,
            source_id="doc:A",
            scope_id=SCOPE,
            candidate_concepts=candidates(),
            registry=reg,
            registry_authority_receipt={"candidate": True},
            registry_authority_verifier=registry_verifier_for(reg),
        )
        self.assertEqual(set(out["surviving_candidates"]), {"CCOB", "TLAC"})
        self.assertEqual(out["next_discriminator"], "CHECK_RESOLUTION_REGIME")
        self.assertFalse(out["pass"])

    def test_registry_without_authority_never_mints_global_completeness(self):
        reg = registry()
        out = resolve(
            RAW,
            source_id="doc:A",
            scope_id=SCOPE,
            candidate_concepts=candidates(),
            registry=reg,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["registry_result"]["status"],
            "OPEN__AUTHENTICATED_REGISTRY_SCOPE_COMPLETENESS_REQUIRED",
        )
        self.assertTrue(out["opaque_remainder_required"])

    def test_required_atom_refutation_rejects_only_that_candidate(self):
        out = resolve(
            RAW,
            source_id="doc:A",
            scope_id=SCOPE,
            candidate_concepts=candidates(),
            evidence=[
                {"atom": "regime.resolution", "state": "REFUTED"},
            ],
        )
        self.assertNotIn("TLAC", out["surviving_candidates"])
        self.assertIn("CCOB", out["surviving_candidates"])
        self.assertTrue(
            any(
                row["concept_id"] == "TLAC"
                and row["reason"] == "EVIDENCE_CONTRACT_REFUTED"
                for row in out["rejected_candidates"]
            )
        )

    def test_fail_closed_on_relation_scope_rebinding_attempt(self):
        out = resolve(
            RAW,
            source_id="doc:A",
            scope_id=SCOPE,
            candidate_concepts=candidates(),
            relation_problems={
                "CCOB": {
                    "scope_id": "wrong-scope",
                    "required_relation": "SEMANTIC_IDENTITY",
                }
            },
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("RELATION_SCOPE_MISMATCH", out["reason"])

    def test_no_terminal_authority_even_for_verified_mapping(self):
        out = resolve(
            RAW,
            source_id="doc:A",
            scope_id=SCOPE,
            candidate_concepts=candidates(),
            relation_problems={
                "CCOB": {
                    "required_relation": "SEMANTIC_IDENTITY",
                    "explicit_definition_sources": [
                        {
                            "source_id": "doc:A",
                            "scope_id": SCOPE,
                            "source_text": (
                                "Loss-absorbing cushion means capital conservation buffer."
                            ),
                        }
                    ],
                }
            },
        )
        self.assertTrue(out["pass"])
        self.assertFalse(out["terminal_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
