from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import regcap_facet_role_projection_v1 as proj
from canonical.runtime import regcap_facet_role_truth_certificate_v1 as cert
from canonical.runtime import source_aligned_regcap_context_proof_v1 as context
from canonical.runtime import semantic_truth_dispatch_v1 as dispatch


CCOB = (
    "a 2.5% buffer comprised of Common Equity Tier 1 (CET1) "
    "above the regulatory minimum capital requirement"
)
CCYB = "the buffer is released when system-wide risk crystallises or dissipates"
TLAC = (
    "loss-absorbing and recapitalisation capacity available in resolution "
    "for a failing G-SIB"
)


def truth_payload(text, kind, role):
    return {
        "truth_kind": cert.TRUTH_KIND,
        "predicate_id": "caller-label",
        "source_text": text,
        "source_id": "doc:A",
        "start": 0,
        "end": len(text),
        "context_kind": kind,
        "target_facet_role": role,
    }


class Tests(unittest.TestCase):
    def test_ccob_structure_projects_three_distinct_roles(self):
        out = proj.project(
            CCOB,
            source_id="doc:A",
            start=0,
            end=len(CCOB),
            context_kind=context.CCOB_KIND,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            set(out["facet_roles"]),
            {
                proj.ROLE_QUANTIFIED_LEVEL,
                proj.ROLE_COMPOSITION,
                proj.ROLE_POSITION,
            },
        )
        self.assertTrue(out["frame_level_projection"])
        self.assertFalse(out["single_facet_reference_authority"])
        self.assertFalse(out["concept_identity_authority"])

    def test_ccyb_release_projects_transition_role(self):
        out = proj.project(
            CCYB,
            source_id="doc:A",
            start=0,
            end=len(CCYB),
            context_kind=context.CCYB_KIND,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["facet_roles"], [proj.ROLE_TRANSITION])
        self.assertFalse(out["frame_level_projection"])

    def test_tlac_context_preserves_function_regime_and_subject_scope(self):
        out = proj.project(
            TLAC,
            source_id="doc:A",
            start=0,
            end=len(TLAC),
            context_kind=context.TLAC_KIND,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            set(out["facet_roles"]),
            {
                proj.ROLE_FUNCTION,
                proj.ROLE_REGIME,
                proj.ROLE_SUBJECT_SCOPE,
            },
        )
        self.assertEqual(
            set(out["facet_role_support"][proj.ROLE_FUNCTION]),
            {context.ATOM_LOSS, context.ATOM_RECAP},
        )
        self.assertTrue(out["frame_level_projection"])

    def test_uncertified_context_remains_unresolved(self):
        text = "the buffer changed"
        out = proj.project(
            text,
            source_id="doc:A",
            start=0,
            end=len(text),
            context_kind=context.CCOB_KIND,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__BOUND_CONTEXT_NOT_CERTIFIED",
        )

    def test_truth_certificate_proves_projected_role_true(self):
        out = cert.evaluate(
            truth_payload(CCOB, context.CCOB_KIND, proj.ROLE_COMPOSITION)
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["predicate_truth"], "TRUE")
        self.assertTrue(out["facet_role_authority"])
        self.assertFalse(out["single_facet_reference_authority"])

    def test_unprojected_role_is_unknown_not_false(self):
        out = cert.evaluate(
            truth_payload(CCYB, context.CCYB_KIND, proj.ROLE_COMPOSITION)
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"], "UNKNOWN")
        self.assertIn("ABSENCE_IS_NOT_NEGATION", out["reason"])

    def test_unsupported_role_fails_closed(self):
        out = cert.evaluate(
            truth_payload(CCOB, context.CCOB_KIND, "FACET_ROLE::MAGIC")
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("TARGET_FACET_ROLE_UNSUPPORTED", out["reason"])

    def test_dispatcher_routes_regcap_facet_role(self):
        expected = {"pass": True, "predicate_truth": "TRUE"}
        with patch.object(
            dispatch,
            "evaluate_regcap_facet_role",
            return_value=expected,
        ) as fn:
            out = dispatch.evaluate({
                "truth_kind": "REGCAP_FACET_ROLE",
                "predicate_id": "x",
            })
        self.assertEqual(out, expected)
        fn.assert_called_once()

    def test_true_role_grants_no_single_facet_or_terminal_authority(self):
        out = cert.evaluate(
            truth_payload(TLAC, context.TLAC_KIND, proj.ROLE_REGIME)
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["single_facet_reference_authority"])
        self.assertFalse(out["concept_identity_authority"])
        self.assertFalse(out["global_identity_authority"])
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
