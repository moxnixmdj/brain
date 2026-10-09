import unittest
from unittest.mock import patch

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v2 as v2
from canonical.runtime import nyfed_loss_cushion_ccob_source_identity_v1 as identity
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap

RAW = "loss-absorbing cushion"

def open_result():
    return {
        "status": "OPEN__COMPOSED_SOURCE_MEANING_WITH_NON_UNIQUE_REGCAP_CANDIDATES",
        "pass": True,
        "candidate_concept_ids": [regcap.CCOB, regcap.CCYB, regcap.TLAC],
        "mapped_concept_id": None,
        "fully_semantically_bound": False,
        "opaque_remainder_required": True,
        "semantic_identity_authority": False,
        "terminal_authority": False,
    }

class Tests(unittest.TestCase):
    def test_exact_source_upgrades_to_ccob(self):
        with patch.object(v2.v1, "ground", return_value=open_result()), patch.object(
            v2.source_identity,
            "verify",
            return_value={"pass": True, "mapped_concept_id": regcap.CCOB},
        ):
            out = v2.ground(RAW, source_id=identity.SOURCE_ID, start=0, end=len(RAW))
        self.assertTrue(out["pass"])
        self.assertEqual(out["mapped_concept_id"], regcap.CCOB)
        self.assertTrue(out["fully_semantically_bound"])
        self.assertFalse(out["global_phrase_identity_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_other_source_stays_candidate_only(self):
        with patch.object(v2.v1, "ground", return_value=open_result()), patch.object(
            v2.source_identity,
            "verify",
        ) as mocked:
            out = v2.ground(RAW, source_id="doc:A", start=0, end=len(RAW))
        self.assertIsNone(out["mapped_concept_id"])
        self.assertFalse(out["fully_semantically_bound"])
        mocked.assert_not_called()

    def test_identity_failure_stays_candidate_only(self):
        with patch.object(v2.v1, "ground", return_value=open_result()), patch.object(
            v2.source_identity,
            "verify",
            return_value={"pass": False, "status": "FAIL_CLOSED"},
        ):
            out = v2.ground(RAW, source_id=identity.SOURCE_ID, start=0, end=len(RAW))
        self.assertIsNone(out["mapped_concept_id"])
        self.assertFalse(out["fully_semantically_bound"])
        self.assertTrue(out["source_specific_identity_attempted"])

    def test_v1_fail_closed_is_preserved(self):
        with patch.object(v2.v1, "ground", return_value={
            "status": "FAIL_CLOSED",
            "pass": False,
        }), patch.object(v2.source_identity, "verify") as mocked:
            out = v2.ground(RAW, source_id=identity.SOURCE_ID, start=0, end=len(RAW))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        mocked.assert_not_called()

if __name__ == "__main__":
    unittest.main()
