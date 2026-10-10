from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import rwa_capital_measurement_context_v1 as frame
from canonical.runtime import rwa_capital_measurement_truth_certificate_v1 as cert
from canonical.runtime import semantic_truth_dispatch_v1 as dispatch


TEXT="The capital ratio stood at 12.5% of RWA."
START=TEXT.index("capital ratio")
END=START+len("capital ratio")


def proved():
    return {
        "schema":frame.SCHEMA,
        "status":"PASS__RWA_REGULATORY_CAPITAL_MEASUREMENT_FRAME_AUTHENTICATED",
        "pass":True,
        "semantic_truth_authority":True,
        "measurement_basis_authority":True,
        "frame_authority":True,
        "semantic_frame_id":frame.FRAME_ID,
        "proved_atom_ids":list(frame.PROVED_ATOMS),
        "concept_identity_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }


def payload(target=frame.FRAME_ID,predicate_id="caller-supplied"):
    return {
        "truth_kind":cert.TRUTH_KIND,
        "predicate_id":predicate_id,
        "source_text":TEXT,
        "source_id":"doc:A",
        "start":START,
        "end":END,
        "target_frame_id":target,
    }


class Tests(unittest.TestCase):
    def test_certificate_true_for_recomputed_matching_frame(self):
        with patch.object(cert.frame,"resolve_occurrence",return_value=proved()):
            out=cert.evaluate(payload())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["predicate_truth"],"TRUE")
        self.assertTrue(out["semantic_frame_authority"])
        self.assertTrue(out["measurement_basis_authority"])
        self.assertFalse(out["concept_identity_authority"])
        self.assertFalse(out["requested_predicate_id_authority"])
        self.assertNotEqual(out["predicate_id"],"caller-supplied")

    def test_unresolved_frame_stays_unknown(self):
        unresolved={"status":"UNRESOLVED__NO_UNIQUE_RWA_MEASUREMENT_SIGNATURE","pass":False}
        with patch.object(cert.frame,"resolve_occurrence",return_value=unresolved):
            out=cert.evaluate(payload())
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"],"UNKNOWN")
        self.assertFalse(out["truthful_precommitment_observation"])

    def test_different_proved_frame_is_not_negation(self):
        other={**proved(),"semantic_frame_id":"FINANCE::OTHER_FRAME"}
        with patch.object(cert.frame,"resolve_occurrence",return_value=other):
            out=cert.evaluate(payload())
        self.assertFalse(out["pass"])
        self.assertEqual(out["predicate_truth"],"UNKNOWN")
        self.assertEqual(out["status"],"UNKNOWN__DIFFERENT_PROVED_MEASUREMENT_FRAME")

    def test_fail_closed_from_underlying_authority_propagates(self):
        with patch.object(cert.frame,"resolve_occurrence",return_value={"status":"FAIL_CLOSED","pass":False,"reason":"SOURCE_FAIL"}):
            out=cert.evaluate(payload())
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("RWA_MEASUREMENT_FRAME_AUTHORITY_FAIL_CLOSED",out["reason"])

    def test_unsupported_target_frame_fails_closed(self):
        out=cert.evaluate(payload(target="FINANCE::CET1_RATIO"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("TARGET_FRAME_UNSUPPORTED",out["reason"])

    def test_dispatch_routes_new_truth_kind_to_certificate(self):
        with patch.object(cert.frame,"resolve_occurrence",return_value=proved()):
            out=dispatch.evaluate(payload())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["predicate_truth"],"TRUE")
        self.assertEqual(out["target_frame_id"],frame.FRAME_ID)

    def test_dispatch_unknown_kind_still_fails_closed(self):
        out=dispatch.evaluate({"truth_kind":"RWA_CAPITAL_MEASUREMENT_FRAME_BOGUS"})
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("TRUTH_KIND_UNSUPPORTED",out["reason"])

    def test_predicate_id_is_bound_to_exact_source_bytes(self):
        a=cert.checked_predicate_id(
            source_id="doc:A",source_text=TEXT,start=START,end=END,
            target_frame_id=frame.FRAME_ID,
        )
        changed=TEXT.replace("12.5","12.6")
        b=cert.checked_predicate_id(
            source_id="doc:A",source_text=changed,start=START,end=END,
            target_frame_id=frame.FRAME_ID,
        )
        self.assertNotEqual(a,b)

    def test_no_policy_or_terminal_authority(self):
        with patch.object(cert.frame,"resolve_occurrence",return_value=proved()):
            out=cert.evaluate(payload())
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
