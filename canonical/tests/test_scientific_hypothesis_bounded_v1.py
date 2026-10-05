from __future__ import annotations

import math
import unittest

from canonical.runtime.scientific_hypothesis_bounded_v1 import (
    HypothesisKernelError,
    formulate_and_rank,
    generate_hypotheses,
)


OBS=[{"variable":"growth","direction":1}]
MECH=[
    {"id":"nutrient","target":"growth","predicted_direction":1,"hypothesis":"Nutrient availability increases growth."},
    {"id":"temperature","target":"growth","predicted_direction":1,"hypothesis":"Higher temperature in the tested range increases growth."},
    {"id":"inhibitor","target":"growth","predicted_direction":-1,"hypothesis":"The inhibitor increases growth."},
]


class ScientificHypothesisBoundedTests(unittest.TestCase):
    def test_generates_only_mechanisms_matching_observed_anomaly(self):
        rows=generate_hypotheses(observations=OBS,mechanisms=MECH)
        self.assertEqual([x["hypothesis_id"] for x in rows],["nutrient","temperature"])
        self.assertTrue(all(x["falsifiable"] for x in rows))

    def test_perfect_binary_test_has_one_bit_information_gain(self):
        out=formulate_and_rank(
            observations=OBS,
            mechanisms=MECH[:2],
            priors={"nutrient":0.5,"temperature":0.5},
            tests=[{
                "id":"assay","cost":1.0,"feasible":True,
                "likelihoods":{
                    "nutrient":{"positive":1.0,"negative":0.0},
                    "temperature":{"positive":0.0,"negative":1.0},
                },
            }],
            max_test_cost=1.0,
        )
        self.assertEqual(out["status"],"BOUNDED_HYPOTHESIS_AND_TEST_SELECTED")
        self.assertEqual(out["selected_test"]["test_id"],"assay")
        self.assertAlmostEqual(out["selected_test"]["expected_information_gain_bits"],1.0,places=12)
        self.assertEqual(out["persistent_learned_bytes"],0)

    def test_nondiscriminating_test_does_not_claim_resolution(self):
        out=formulate_and_rank(
            observations=OBS,
            mechanisms=MECH[:2],
            priors={"nutrient":0.5,"temperature":0.5},
            tests=[{
                "id":"useless","cost":1.0,"feasible":True,
                "likelihoods":{
                    "nutrient":{"positive":0.5,"negative":0.5},
                    "temperature":{"positive":0.5,"negative":0.5},
                },
            }],
            max_test_cost=1.0,
        )
        self.assertEqual(out["status"],"UNRESOLVED_NO_DISCRIMINATING_FEASIBLE_TEST")
        self.assertIsNone(out["selected_test"])

    def test_cost_budget_filters_expensive_test(self):
        out=formulate_and_rank(
            observations=OBS,
            mechanisms=MECH[:2],
            priors={"nutrient":0.5,"temperature":0.5},
            tests=[{
                "id":"expensive","cost":5.0,"feasible":True,
                "likelihoods":{
                    "nutrient":{"yes":1.0,"no":0.0},
                    "temperature":{"yes":0.0,"no":1.0},
                },
            }],
            max_test_cost=1.0,
        )
        self.assertEqual(out["status"],"UNRESOLVED_NO_DISCRIMINATING_FEASIBLE_TEST")

    def test_prefers_information_gain_per_cost(self):
        out=formulate_and_rank(
            observations=OBS,
            mechanisms=MECH[:2],
            priors={"nutrient":0.5,"temperature":0.5},
            tests=[
                {
                    "id":"perfect-expensive","cost":4.0,"feasible":True,
                    "likelihoods":{
                        "nutrient":{"yes":1.0,"no":0.0},
                        "temperature":{"yes":0.0,"no":1.0},
                    },
                },
                {
                    "id":"perfect-cheap","cost":1.0,"feasible":True,
                    "likelihoods":{
                        "nutrient":{"yes":1.0,"no":0.0},
                        "temperature":{"yes":0.0,"no":1.0},
                    },
                },
            ],
            max_test_cost=5.0,
        )
        self.assertEqual(out["selected_test"]["test_id"],"perfect-cheap")

    def test_invalid_likelihood_normalization_fails_closed(self):
        with self.assertRaisesRegex(HypothesisKernelError,"TEST_PROB_NOT_NORMALIZED"):
            formulate_and_rank(
                observations=OBS,
                mechanisms=MECH[:2],
                priors={"nutrient":0.5,"temperature":0.5},
                tests=[{
                    "id":"bad","cost":1.0,"feasible":True,
                    "likelihoods":{
                        "nutrient":{"yes":0.8,"no":0.8},
                        "temperature":{"yes":0.5,"no":0.5},
                    },
                }],
                max_test_cost=1.0,
            )

    def test_missing_prior_fails_closed(self):
        with self.assertRaisesRegex(HypothesisKernelError,"PRIORS_MISSING"):
            formulate_and_rank(
                observations=OBS,
                mechanisms=MECH[:2],
                priors={"nutrient":1.0},
                tests=[],
                max_test_cost=1.0,
            )

    def test_no_matching_mechanism_returns_unresolved_not_invention(self):
        out=formulate_and_rank(
            observations=[{"variable":"mass","direction":1}],
            mechanisms=MECH,
            priors={},
            tests=[],
            max_test_cost=1.0,
        )
        self.assertEqual(out["status"],"UNRESOLVED_NO_EXPLICIT_MECHANISM_MATCH")
        self.assertFalse(out["semantic_authority"])


if __name__=="__main__":
    unittest.main(verbosity=2)
