import unittest

from canonical.runtime.gdpval_evaluation_law_information_cut_v1 import (
    verify_countermodel,
)

H = "a" * 64


def base():
    return {
        "public_observation_class": {
            "current_owner_contract_bound": True,
            "exact_current_preference_relation_bound": False,
            "observation_digest_sha256": H,
        },
        "worlds": {
            "left": {
                "public_observation_digest_sha256": H,
                "consistent_with_all_bound_public_facts": True,
                "owner_outcome": "BRAIN_WIN",
            },
            "right": {
                "public_observation_digest_sha256": H,
                "consistent_with_all_bound_public_facts": True,
                "owner_outcome": "OPUS_WIN",
            },
        },
        "separator": {
            "already_bound": False,
            "public_metadata_only": False,
        },
    }


class GDPValEvaluationLawInformationCutV1Tests(unittest.TestCase):
    def test_two_world_countermodel_proves_public_nonidentifiability(self):
        out = verify_countermodel(base())
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["public_information_alone_entails_brain_noninferiority"])
        self.assertTrue(out["target_relation_differs"])
        self.assertEqual(out["gdpval_credit_delta"], 0)

    def test_tie_vs_opus_also_flips_noninferiority(self):
        m = base()
        m["worlds"]["left"]["owner_outcome"] = "TIE"
        out = verify_countermodel(m)
        self.assertTrue(out["pass"], out)

    def test_same_outcome_is_not_a_countermodel(self):
        m = base()
        m["worlds"]["right"]["owner_outcome"] = "BRAIN_WIN"
        out = verify_countermodel(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "TARGET_RELATION_DOES_NOT_DIFFER_BETWEEN_WORLDS")

    def test_observation_difference_breaks_indistinguishability(self):
        m = base()
        m["worlds"]["right"]["public_observation_digest_sha256"] = "b" * 64
        out = verify_countermodel(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "WORLD_PUBLIC_OBSERVATIONS_NOT_IDENTICAL")

    def test_world_must_be_compatible_with_all_bound_public_facts(self):
        m = base()
        m["worlds"]["right"]["consistent_with_all_bound_public_facts"] = False
        out = verify_countermodel(m)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "WORLD_NOT_PROVED_COMPATIBLE_WITH_BOUND_PUBLIC_FACTS",
        )

    def test_metadata_only_cannot_be_called_separator(self):
        m = base()
        m["separator"]["public_metadata_only"] = True
        out = verify_countermodel(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SEPARATOR_STATE_MUST_EXPLICITLY_REJECT_METADATA_ONLY")

    def test_bound_decisive_separator_demotes_countermodel_to_rerun(self):
        m = base()
        m["separator"] = {
            "already_bound": True,
            "public_metadata_only": False,
            "proof_class": "AUTHENTIC_CURRENT_OWNER_PAIRWISE_OUTCOME",
            "evidence_sha256": H,
        }
        out = verify_countermodel(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "COUNTERMODEL_ALREADY_SEPARATED__RERUN_TARGET_PROOF")

    def test_unknown_bound_separator_class_fails_closed(self):
        m = base()
        m["separator"] = {
            "already_bound": True,
            "public_metadata_only": False,
            "proof_class": "MORE_METADATA",
            "evidence_sha256": H,
        }
        out = verify_countermodel(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "BOUND_SEPARATOR_CLASS_NOT_DECISIVE")

    def test_exact_relation_must_still_be_unbound_for_this_countermodel(self):
        m = base()
        m["public_observation_class"]["exact_current_preference_relation_bound"] = True
        out = verify_countermodel(m)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "COUNTERMODEL_REQUIRES_CURRENT_RELATION_TO_REMAIN_UNBOUND",
        )

    def test_invalid_outcome_rejected(self):
        m = base()
        m["worlds"]["left"]["owner_outcome"] = "UNKNOWN"
        out = verify_countermodel(m)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "WORLD_OWNER_OUTCOME_INVALID")


if __name__ == "__main__":
    unittest.main()
