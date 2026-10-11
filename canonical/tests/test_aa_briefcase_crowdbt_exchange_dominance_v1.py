from __future__ import annotations

import unittest

from canonical.runtime import aa_briefcase_crowdbt_exchange_dominance_v1 as ex


def base():
    return {
        "fixed_quality_crowd_bt_eq5": True,
        "same_epoch_same_scorer": True,
        "all_brain_opus_incident_non_direct_comparisons_bijectively_matched": True,
        "no_unmatched_brain_or_opus_incident_comparisons": True,
        "comparison_roles_normalized_to_candidate_win": True,
        "brain_opus_symmetric_regularization": True,
        "matched_comparisons": [
            {
                "opponent": "Model-X",
                "judge": "Judge-1",
                "judge_quality": 0.8,
                "brain_outcome": 1.0,
                "opus_outcome": 0.5,
            },
            {
                "opponent": "Model-Y",
                "judge": "Judge-2",
                "judge_quality": 0.9,
                "brain_outcome": 0.5,
                "opus_outcome": 0.5,
            },
        ],
        "direct_brain_opus_comparisons": [],
        "same_fit_opus_rating_lower_bound": 1822.0,
    }


class AACrowdBTExchangeDominanceV1Tests(unittest.TestCase):
    def test_strict_matched_advantage_plus_1822_floor_closes_numeric_implication(self):
        out = ex.verify_exchange_dominance(base())
        self.assertTrue(out["brain_rating_strictly_greater_than_opus_in_same_bound_fit"])
        self.assertTrue(out["aa_briefcase_ge_1822_implied"])
        self.assertFalse(out["terminal_authority"])

    def test_relative_order_without_same_fit_floor_does_not_claim_1822(self):
        cert = base()
        cert["same_fit_opus_rating_lower_bound"] = None
        out = ex.verify_exchange_dominance(cert)
        self.assertTrue(out["brain_rating_strictly_greater_than_opus_in_same_bound_fit"])
        self.assertFalse(out["aa_briefcase_ge_1822_implied"])

    def test_brain_worse_row_rejected(self):
        cert = base()
        cert["matched_comparisons"][0]["brain_outcome"] = 0.0
        with self.assertRaisesRegex(ex.ExchangeError, "BRAIN_OUTCOME_WORSE"):
            ex.verify_exchange_dominance(cert)

    def test_eta_below_half_rejected(self):
        cert = base()
        cert["matched_comparisons"][0]["judge_quality"] = 0.49
        with self.assertRaisesRegex(ex.ExchangeError, "JUDGE_QUALITY_BELOW_HALF"):
            ex.verify_exchange_dominance(cert)

    def test_all_ties_have_no_strict_order_certificate(self):
        cert = base()
        for row in cert["matched_comparisons"]:
            row["brain_outcome"] = row["opus_outcome"] = 0.5
        with self.assertRaisesRegex(ex.ExchangeError, "NO_STRICT_INFORMATIVE_BRAIN_ADVANTAGE"):
            ex.verify_exchange_dominance(cert)

    def test_strict_advantage_at_eta_half_is_not_informative(self):
        cert = base()
        cert["matched_comparisons"] = [
            {
                "opponent": "Model-X",
                "judge": "Judge-1",
                "judge_quality": 0.5,
                "brain_outcome": 1.0,
                "opus_outcome": 0.0,
            }
        ]
        with self.assertRaisesRegex(ex.ExchangeError, "NO_STRICT_INFORMATIVE_BRAIN_ADVANTAGE"):
            ex.verify_exchange_dominance(cert)

    def test_unmatched_incident_schedule_rejected(self):
        cert = base()
        cert["no_unmatched_brain_or_opus_incident_comparisons"] = False
        with self.assertRaisesRegex(
            ex.ExchangeError,
            "NO_UNMATCHED_BRAIN_OR_OPUS_INCIDENT_COMPARISONS_NOT_PROVED",
        ):
            ex.verify_exchange_dominance(cert)

    def test_direct_win_can_supply_strict_information(self):
        cert = base()
        cert["matched_comparisons"] = [
            {
                "opponent": "Model-X",
                "judge": "Judge-1",
                "judge_quality": 0.8,
                "brain_outcome": 0.5,
                "opus_outcome": 0.5,
            }
        ]
        cert["direct_brain_opus_comparisons"] = [
            {
                "judge": "Judge-3",
                "judge_quality": 0.9,
                "brain_outcome": 1.0,
            }
        ]
        out = ex.verify_exchange_dominance(cert)
        self.assertTrue(out["brain_rating_strictly_greater_than_opus_in_same_bound_fit"])

    def test_direct_loss_rejected(self):
        cert = base()
        cert["direct_brain_opus_comparisons"] = [
            {
                "judge": "Judge-3",
                "judge_quality": 0.9,
                "brain_outcome": 0.0,
            }
        ]
        with self.assertRaisesRegex(ex.ExchangeError, "DIRECT_0_BRAIN_LOSES"):
            ex.verify_exchange_dominance(cert)


if __name__ == "__main__":
    unittest.main(verbosity=2)
