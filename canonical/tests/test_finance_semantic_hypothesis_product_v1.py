from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import finance_semantic_hypothesis_product_v1 as producer
from canonical.runtime import finance_semantic_hypothesis_product_verify_v1 as verifier
from canonical.runtime import (
    r2_finance_semantic_hypothesis_product_direct_adequacy_v1 as route,
)
from canonical.runtime import r2_direct_end_to_end_adequacy_v16 as router


def case(*, coref_matters=False, sense_matters=True):
    return {
        "schema": producer.INPUT_SCHEMA,
        "domain": "FINANCE",
        "ambiguity_owner": "USER_INTENT",
        "cartesian_product_complete": True,
        "terminal_signature_factorization_complete": True,
        "dimensions": [
            {
                "dimension_id": "coreference",
                "candidate_set_complete": True,
                "candidates": [
                    {
                        "candidate_id": "bank",
                        "terminal_signature_fragment": (
                            {"entity": "bank"} if coref_matters else {}
                        ),
                    },
                    {
                        "candidate_id": "waiver",
                        "terminal_signature_fragment": (
                            {"entity": "waiver"} if coref_matters else {}
                        ),
                    },
                ],
            },
            {
                "dimension_id": "sense",
                "candidate_set_complete": True,
                "candidates": [
                    {
                        "candidate_id": "profit-margin",
                        "terminal_signature_fragment": (
                            {"policy": "A"} if sense_matters else {"policy": "A"}
                        ),
                    },
                    {
                        "candidate_id": "collateral-margin",
                        "terminal_signature_fragment": (
                            {"policy": "B"} if sense_matters else {"policy": "A"}
                        ),
                    },
                ],
            },
        ],
        "observations": [
            {
                "observation_id": "resolve-coreference",
                "dimension_id": "coreference",
                "outcome_map_complete": True,
                "outcomes": {"bank": "bank", "waiver": "waiver"},
                "cost_units": 0.5,
            },
            {
                "observation_id": "resolve-sense",
                "dimension_id": "sense",
                "outcome_map_complete": True,
                "outcomes": {
                    "profit-margin": "profit",
                    "collateral-margin": "collateral",
                },
                "cost_units": 1,
            },
        ],
    }


class FinanceSemanticHypothesisProductV1Tests(unittest.TestCase):
    def test_irrelevant_dimension_is_not_disambiguated(self):
        out = producer.compute(case(coref_matters=False, sense_matters=True))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["joint_world_count"], 4)
        self.assertEqual(
            out["decision"]["action"],
            "ACQUIRE_MINIMUM_TERMINALLY_RELEVANT_DISCRIMINATOR",
        )
        self.assertEqual(out["decision"]["next_observation_id"], "resolve-sense")
        self.assertEqual(out["decision"]["minimum_worst_case_cost_units"], 1.0)

    def test_all_joint_worlds_terminally_equivalent_need_no_resolution(self):
        out = producer.compute(case(coref_matters=False, sense_matters=False))
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["decision"]["action"], "CONTINUE_WITHOUT_DISAMBIGUATION"
        )

    def test_both_dimensions_can_be_required(self):
        out = producer.compute(case(coref_matters=True, sense_matters=True))
        self.assertEqual(
            out["decision"]["minimum_worst_case_cost_units"], 1.5
        )

    def test_incomplete_dimension_fails_closed(self):
        bad = case()
        bad["dimensions"][0]["candidate_set_complete"] = False
        with self.assertRaisesRegex(
            ValueError, "CANDIDATE_SET_COMPLETENESS_REQUIRED"
        ):
            producer.compute(bad)

    def test_conflicting_factorized_terminal_fields_fail_closed(self):
        bad = case()
        bad["dimensions"][0]["candidates"][0][
            "terminal_signature_fragment"
        ] = {"policy": "X"}
        with self.assertRaisesRegex(
            ValueError, "TERMINAL_SIGNATURE_FRAGMENT_CONFLICT"
        ):
            producer.compute(bad)

    def test_independent_verifier_rejects_tamper(self):
        c = case()
        out = producer.compute(c)
        out["joint_world_count"] = 99
        checked = verifier.verify(c, out)
        self.assertFalse(checked["verified"], checked)

    def test_direct_route_transaction_succeeds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "canonical" / "cases" / "product.json"
            target = root / "canonical" / "out" / "result.json"
            source.parent.mkdir(parents=True)
            source.write_text(json.dumps(case(), sort_keys=True), encoding="utf-8")
            goal = (
                "Using the bounded finance semantic hypothesis product case at "
                "canonical/cases/product.json, compute and independently verify "
                "the decision-relevant joint semantic ambiguity control and save "
                "it to canonical/out/result.json."
            )
            request = {"task_id": "semantic-product", "goal": goal}
            result = route.run(request, repo_root=root)
            self.assertTrue(result["pass"], result)
            self.assertTrue(target.is_file())
            self.assertEqual(result["joint_world_count"], 4)

    def test_direct_route_rolls_back_on_verifier_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "canonical" / "cases" / "product.json"
            target = root / "canonical" / "out" / "result.json"
            source.parent.mkdir(parents=True)
            target.parent.mkdir(parents=True)
            source.write_text(json.dumps(case(), sort_keys=True), encoding="utf-8")
            target.write_text('{"old":true}\n', encoding="utf-8")
            before = target.read_bytes()
            goal = (
                "Using the bounded finance semantic hypothesis product case at "
                "canonical/cases/product.json, compute and independently verify "
                "the decision-relevant joint semantic ambiguity control and save "
                "it to canonical/out/result.json."
            )
            request = {"task_id": "semantic-product-rollback", "goal": goal}
            first = route.verifier.verify(case(), route.producer.compute(case()))
            with patch.object(
                route.verifier,
                "verify",
                side_effect=[
                    first,
                    {
                        "verified": False,
                        "producer_independent": True,
                        "reason": "forced",
                    },
                ],
            ):
                result = route.run(request, repo_root=root)
            self.assertFalse(result["pass"], result)
            self.assertTrue(result["rollback_complete"], result)
            self.assertEqual(target.read_bytes(), before)

    def test_v16_delegates_unmatched_requests_to_v15(self):
        sentinel = {"matched": False, "status": "DELEGATED"}
        with patch.object(router.v15, "preflight", return_value=sentinel) as delegated:
            out = router.preflight({"task_id": "x", "goal": "not this grammar"})
        self.assertEqual(out, sentinel)
        delegated.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
