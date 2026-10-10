from __future__ import annotations

import unittest

from canonical.runtime import regcap_contextual_resolution_v1 as resolver
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap


def fake_projection(pack):
    return {
        "pass": True,
        "receipt": {
            "fragment_ids": sorted(
                str(row["fragment_id"]) for row in pack.get("fragments", [])
            ),
            "receipt_sha256": "a" * 64,
        },
        "source_fragment_authority": True,
        "terminal_authority": False,
    }


def completeness_verifier(scope_id, candidate_ids):
    def verify(_receipt):
        return {
            "pass": True,
            "schema": resolver.COMPLETENESS_SCHEMA,
            "scope_id": scope_id,
            "candidate_ids": list(candidate_ids),
            "candidate_set_complete": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "b" * 64,
        }
    return verify


class Tests(unittest.TestCase):
    def test_releasability_selects_ccyb_only_with_complete_three_way_set(self):
        text = "The cushion is the only designated releasable buffer in the Basel Framework."
        candidates = [regcap.CCOB, regcap.CCYB, regcap.TLAC]
        out = resolver.resolve(
            text,
            start=0,
            end=len(text),
            task_scope_id="task:1",
            candidate_ids=candidates,
            candidate_completeness_receipt={"candidate": True},
            candidate_completeness_verifier=completeness_verifier("task:1", candidates),
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], regcap.CCYB)
        self.assertTrue(out["candidate_universe_complete"])
        self.assertTrue(out["concept_identity_authority"])

    def test_same_observation_does_not_select_without_candidate_completeness(self):
        text = "The cushion is the only designated releasable buffer in the Basel Framework."
        candidates = [regcap.CCOB, regcap.CCYB, regcap.TLAC]
        out = resolver.resolve(
            text,
            start=0,
            end=len(text),
            task_scope_id="task:1",
            candidate_ids=candidates,
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__CANDIDATE_SET_COMPLETENESS_REQUIRED")
        self.assertEqual(out["matching_candidates"], [regcap.CCYB])
        self.assertFalse(out["concept_identity_authority"])

    def test_framework_class_with_three_way_complete_set_remains_ambiguous(self):
        text = (
            "The buffer is an additional layer of capital above the regulatory "
            "minimums and must be met with CET1."
        )
        candidates = [regcap.CCOB, regcap.CCYB, regcap.TLAC]
        out = resolver.resolve(
            text,
            start=0,
            end=len(text),
            task_scope_id="task:2",
            candidate_ids=candidates,
            candidate_completeness_receipt={"candidate": True},
            candidate_completeness_verifier=completeness_verifier("task:2", candidates),
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "UNRESOLVED__AUTHENTICATED_OBSERVATION_NOT_UNIQUE_WITHIN_COMPLETE_CANDIDATE_SET",
        )
        self.assertEqual(set(out["matching_candidates"]), {regcap.CCOB, regcap.CCYB})
        self.assertTrue(out["candidate_universe_complete"])
        self.assertFalse(out["concept_identity_authority"])

    def test_framework_class_selects_ccob_in_complete_ccob_tlac_task(self):
        text = (
            "The buffer is an additional layer of capital above regulatory "
            "minimum and is met with CET1."
        )
        candidates = [regcap.CCOB, regcap.TLAC]
        out = resolver.resolve(
            text,
            start=0,
            end=len(text),
            task_scope_id="task:3",
            candidate_ids=candidates,
            candidate_completeness_receipt={"candidate": True},
            candidate_completeness_verifier=completeness_verifier("task:3", candidates),
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], regcap.CCOB)

    def test_separate_tlac_requirement_selects_tlac(self):
        text = (
            "The requirement is a separate minimum total loss-absorbing capacity "
            "requirement alongside minimum regulatory capital requirements."
        )
        candidates = [regcap.CCOB, regcap.CCYB, regcap.TLAC]
        out = resolver.resolve(
            text,
            start=0,
            end=len(text),
            task_scope_id="task:4",
            candidate_ids=candidates,
            candidate_completeness_receipt={"candidate": True},
            candidate_completeness_verifier=completeness_verifier("task:4", candidates),
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_concept_id"], regcap.TLAC)

    def test_forged_candidate_completeness_binding_is_rejected(self):
        text = "The cushion is the only designated releasable buffer in the Basel Framework."
        candidates = [regcap.CCOB, regcap.CCYB, regcap.TLAC]
        out = resolver.resolve(
            text,
            start=0,
            end=len(text),
            task_scope_id="task:5",
            candidate_ids=candidates,
            candidate_completeness_receipt={"candidate": True},
            candidate_completeness_verifier=completeness_verifier(
                "wrong-scope", candidates
            ),
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__CANDIDATE_SET_COMPLETENESS_REQUIRED")
        self.assertIn("CANDIDATE_COMPLETENESS_BINDING_INVALID", out["candidate_completeness_error"])

    def test_candidate_order_is_part_of_completeness_binding(self):
        text = "The cushion is the only designated releasable buffer in the Basel Framework."
        candidates = [regcap.CCOB, regcap.CCYB, regcap.TLAC]
        reversed_ids = list(reversed(candidates))
        out = resolver.resolve(
            text,
            start=0,
            end=len(text),
            task_scope_id="task:6",
            candidate_ids=candidates,
            candidate_completeness_receipt={"candidate": True},
            candidate_completeness_verifier=completeness_verifier(
                "task:6", reversed_ids
            ),
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__CANDIDATE_SET_COMPLETENESS_REQUIRED")

    def test_outside_matrix_candidate_fails_closed(self):
        text = "The cushion is the only designated releasable buffer in the Basel Framework."
        out = resolver.resolve(
            text,
            start=0,
            end=len(text),
            task_scope_id="task:7",
            candidate_ids=[regcap.CCYB, "REGCAP::MREL"],
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "CANDIDATE_OUTSIDE_MATRIX_DOMAIN")

    def test_insufficient_context_stays_unresolved_even_with_complete_candidates(self):
        text = "The cushion is released when system-wide risk dissipates."
        candidates = [regcap.CCOB, regcap.CCYB, regcap.TLAC]
        out = resolver.resolve(
            text,
            start=0,
            end=len(text),
            task_scope_id="task:8",
            candidate_ids=candidates,
            candidate_completeness_receipt={"candidate": True},
            candidate_completeness_verifier=completeness_verifier("task:8", candidates),
            projection_verifier=fake_projection,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_CERTIFIED_CONTEXTUAL_OBSERVATION",
        )

    def test_no_terminal_authority_even_when_concept_resolved(self):
        text = "The cushion is the only designated releasable buffer in the Basel Framework."
        candidates = [regcap.CCOB, regcap.CCYB, regcap.TLAC]
        out = resolver.resolve(
            text,
            start=0,
            end=len(text),
            task_scope_id="task:9",
            candidate_ids=candidates,
            candidate_completeness_receipt={"candidate": True},
            candidate_completeness_verifier=completeness_verifier("task:9", candidates),
            projection_verifier=fake_projection,
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
