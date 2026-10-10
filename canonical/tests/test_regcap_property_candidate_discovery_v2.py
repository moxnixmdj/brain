from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime import mrel_necessary_property_authority_v1 as mrel
from canonical.runtime import regcap_property_candidate_discovery_v2 as discover


def request(prop):
    return {
        "schema": discover.REQUEST_SCHEMA,
        "scope_id": discover.SCOPE_ID,
        "property_id": prop,
    }


def result(concept, prop, passed=True, *, failed=False):
    if failed:
        return {"pass": False, "status": "FAIL_CLOSED", "reason": "forced"}
    if passed:
        return {
            "pass": True,
            "status": "PASS__PROPERTY_AUTHENTICATED",
            "edge_receipt": {
                "pass": True,
                "source_id": concept,
                "target_id": prop,
                "relation": "ENTAILS",
                "receipt_sha256": (concept + prop).encode().hex()[:64].ljust(64, "0"),
            },
        }
    return {
        "pass": False,
        "status": "UNKNOWN__PROPERTY_NOT_PROVED_IN_BOUND_SCOPE",
        "reason": None,
    }


class Tests(unittest.TestCase):
    def _run(self, prop, regcap_pass, mrel_pass):
        def regcap_verify(req, **_):
            return result(req["concept_id"], req["property_id"], req["concept_id"] in regcap_pass)

        def mrel_verify(req, **_):
            return result(req["concept_id"], req["property_id"], req["concept_id"] in mrel_pass)

        with patch.object(discover.regcap, "verify_property_request", side_effect=regcap_verify), patch.object(
            discover.mrel, "verify_property_request", side_effect=mrel_verify
        ):
            return discover.discover(request(prop))

    def test_loss_absorption_returns_four_bound_candidates(self):
        out = self._run(
            "DISPOSITION::LOSS_ABSORPTION",
            {regcap.CCOB, regcap.CCYB, regcap.TLAC},
            {mrel.MREL},
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["candidate_concept_ids"],
            sorted([regcap.CCOB, regcap.CCYB, regcap.TLAC, mrel.MREL]),
        )
        self.assertTrue(out["candidate_set_complete_relative_to_bound_inventory"])
        self.assertFalse(out["open_world_candidate_set_complete"])
        self.assertFalse(out["unique_identity_authorized"])

    def test_resolution_is_tlac_plus_mrel_not_false_singleton(self):
        out = self._run("REGIME::RESOLUTION", {regcap.TLAC}, {mrel.MREL})
        self.assertEqual(out["candidate_concept_ids"], sorted([regcap.TLAC, mrel.MREL]))
        self.assertEqual(out["status"], "OPEN__NON_UNIQUE_PROPERTY_CANDIDATES")

    def test_gsib_scope_can_be_single_candidate_but_not_identity(self):
        out = self._run("SCOPE::G_SIB", {regcap.TLAC}, set())
        self.assertEqual(out["candidate_concept_ids"], [regcap.TLAC])
        self.assertEqual(out["status"], "OPEN__SINGLE_PROPERTY_CANDIDATE_NOT_IDENTITY")
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["unique_identity_authorized"])

    def test_brrd_article_can_be_single_mrel_candidate_but_not_identity(self):
        out = self._run("LEGAL_FRAMEWORK::EU_BRRD_ARTICLE_45C", set(), {mrel.MREL})
        self.assertEqual(out["candidate_concept_ids"], [mrel.MREL])
        self.assertFalse(out["semantic_identity_authority"])
        self.assertFalse(out["unique_identity_authorized"])

    def test_mrel_authority_failure_does_not_silently_fall_back_to_three(self):
        def regcap_verify(req, **_):
            return result(req["concept_id"], req["property_id"], True)

        def mrel_verify(req, **_):
            return result(req["concept_id"], req["property_id"], failed=True)

        with patch.object(discover.regcap, "verify_property_request", side_effect=regcap_verify), patch.object(
            discover.mrel, "verify_property_request", side_effect=mrel_verify
        ):
            out = discover.discover(request("DISPOSITION::LOSS_ABSORPTION"))

        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertFalse(out["candidate_generation_authority"])

    def test_no_candidate_does_not_mean_nonexistence(self):
        out = self._run("PROPERTY::UNKNOWN", set(), set())
        self.assertFalse(out["pass"])
        self.assertFalse(out["no_candidate_means_nonexistence"])
        self.assertFalse(out["open_world_candidate_set_complete"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
