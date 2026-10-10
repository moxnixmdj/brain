from __future__ import annotations

from hashlib import sha256
import json
import unittest

from canonical.runtime import regcap_contextual_fact_compiler_v1 as ctx
from canonical.runtime.source_aligned_semantic_edge_authority_v1 import (
    CONCEPT_SEMANTICS_RECEIPT_SCHEMA,
    prove,
)

SCOPE = "REGCAP_CONTEXT_TEST_V1"


def atom(name):
    return {"op": "ATOM", "id": name}


def canon_sha(value):
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def concept_verifier(formula, concept_id):
    def verify(_receipt):
        return {
            "pass": True,
            "schema": CONCEPT_SEMANTICS_RECEIPT_SCHEMA,
            "scope_id": SCOPE,
            "concept_id": concept_id,
            "formula_sha256": canon_sha(formula),
            "definition_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
            "concept_semantics_authenticated": True,
            "formula_semantics_authenticated": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "a" * 64,
        }

    return verify


class Tests(unittest.TestCase):
    def test_system_wide_risk_release_full_clause(self):
        text = "The cushion is released when system-wide risk crystallises or dissipates."
        out = ctx.compile_facts(text, source_id="doc:A")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["family"], "SYSTEM_WIDE_RISK_RELEASE")
        self.assertEqual(out["fact_ids"], [ctx.RELEASE_FULL])
        self.assertFalse(out["concept_identity_authority"])

    def test_system_wide_risk_release_us_spelling(self):
        text = "This buffer is released when system-wide risk crystallizes or dissipates."
        out = ctx.compile_facts(text, source_id="doc:A")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["fact_ids"], [ctx.RELEASE_FULL])

    def test_system_wide_risk_dissipates_only_is_weaker_fact(self):
        text = "The cushion is released when system-wide risk dissipates."
        out = ctx.compile_facts(text, source_id="doc:A")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["fact_ids"], [ctx.RELEASE_DISSIPATES])
        self.assertNotIn(ctx.RELEASE_FULL, out["fact_ids"])

    def test_cet1_2_5_above_minimum_preserves_unknown_basis(self):
        text = "A 2.5% CET1 buffer above the regulatory minimum."
        out = ctx.compile_facts(text, source_id="doc:B")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["family"], "CET1_2_5_ABOVE_MINIMUM")
        self.assertIn(ctx.COMPOSITION_CET1, out["fact_ids"])
        self.assertIn(ctx.POSITION_ABOVE_MINIMUM, out["fact_ids"])
        self.assertIn(ctx.VALUE_2_5_UNKNOWN_BASIS, out["fact_ids"])
        self.assertFalse(out["numeric_basis_complete"])

    def test_tlac_resolution_bundle_uk_spelling(self):
        text = (
            "Loss-absorbing and recapitalisation capacity available in resolution "
            "for a G-SIB."
        )
        out = ctx.compile_facts(text, source_id="doc:C")
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["family"], "LOSS_RECAP_RESOLUTION_GSIB")
        self.assertEqual(
            set(out["fact_ids"]),
            {
                ctx.LOSS_ABSORPTION,
                ctx.LOSS_ABSORPTION_DISPOSITION,
                ctx.RECAPITALISATION,
                ctx.RESOLUTION,
                ctx.G_SIB,
            },
        )

    def test_tlac_resolution_bundle_us_spelling(self):
        text = (
            "The resource provides loss-absorbing and recapitalization capacity "
            "available in resolution for a G-SIB."
        )
        out = ctx.compile_facts(text, source_id="doc:C")
        self.assertTrue(out["pass"], out)
        self.assertIn(ctx.RECAPITALISATION, out["fact_ids"])

    def test_fsb_failure_clause(self):
        text = (
            "If a G-SIB fails it has sufficient loss-absorbing and "
            "recapitalisation capacity available in resolution."
        )
        out = ctx.compile_facts(text, source_id="doc:C")
        self.assertTrue(out["pass"], out)
        self.assertIn(ctx.G_SIB, out["fact_ids"])
        self.assertIn(ctx.RESOLUTION, out["fact_ids"])

    def test_negated_release_clause_is_unresolved(self):
        text = "The cushion is not released when system-wide risk dissipates."
        out = ctx.compile_facts(text, source_id="doc:A")
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__OUTSIDE_BOUNDED_CONTEXTUAL_GRAMMAR",
        )

    def test_attributed_claim_is_unresolved(self):
        text = (
            "Analysts claim the cushion is released when system-wide risk "
            "dissipates."
        )
        out = ctx.compile_facts(text, source_id="doc:A")
        self.assertFalse(out["pass"])

    def test_quoted_clause_is_unresolved(self):
        text = '"The cushion is released when system-wide risk dissipates."'
        out = ctx.compile_facts(text, source_id="doc:A")
        self.assertFalse(out["pass"])

    def test_missing_resolution_does_not_mint_resolution_fact(self):
        text = "Loss-absorbing and recapitalisation capacity for a G-SIB."
        out = ctx.compile_facts(text, source_id="doc:C")
        self.assertFalse(out["pass"])

    def test_2_5_without_cet1_is_unresolved(self):
        text = "A 2.5% buffer above the regulatory minimum."
        out = ctx.compile_facts(text, source_id="doc:B")
        self.assertFalse(out["pass"])

    def test_source_proof_recomputes_requested_subset(self):
        text = (
            "Loss-absorbing and recapitalisation capacity available in resolution "
            "for a G-SIB."
        )
        out = ctx.verify_proof(
            text,
            source_id="doc:C",
            claims=[{
                "claim_id": "resolution",
                "kind": ctx.CLAIM_KIND,
                "fact_ids": [ctx.RESOLUTION, ctx.G_SIB],
            }],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED", out)
        self.assertEqual(
            out["proved_constraints"],
            [atom(ctx.RESOLUTION), atom(ctx.G_SIB)],
        )
        self.assertFalse(out["concept_identity_authority"])

    def test_source_proof_rejects_unproved_fact(self):
        text = "The cushion is released when system-wide risk dissipates."
        out = ctx.verify_proof(
            text,
            source_id="doc:A",
            claims=[{
                "claim_id": "fake",
                "kind": ctx.CLAIM_KIND,
                "fact_ids": [ctx.RESOLUTION],
            }],
        )
        self.assertEqual(out["status"], "PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"], [])

    def test_existing_edge_authority_consumes_verified_context_fact(self):
        text = "The cushion is released when system-wide risk dissipates."
        formula = atom(ctx.RELEASE_DISSIPATES)
        out = prove(
            text,
            source_id="doc:A",
            scope_id=SCOPE,
            target_concept_id="CONTEXT::SYSTEM_WIDE_RISK_RELEASE_RULE",
            direction="SOURCE_TO_TARGET",
            source_claims=[{
                "claim_id": "release",
                "kind": ctx.CLAIM_KIND,
                "fact_ids": [ctx.RELEASE_DISSIPATES],
            }],
            target_formula=formula,
            concept_semantics_receipt={"candidate": True},
            concept_semantics_verifier=concept_verifier(
                formula,
                "CONTEXT::SYSTEM_WIDE_RISK_RELEASE_RULE",
            ),
            source_proof_verifier=ctx.verify_proof,
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_edge_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_context_fact_never_grants_concept_identity_or_negative_authority(self):
        out = ctx.compile_facts(
            "A 2.5% CET1 buffer above the regulatory minimum.",
            source_id="doc:B",
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["concept_identity_authority"])
        self.assertFalse(out["negative_fact_authority"])
        self.assertFalse(out["candidate_universe_complete"])
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
