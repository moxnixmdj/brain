from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from canonical.runtime import professional_quality_r10_execution_property_challenge_v1 as r10


class R10ExecutionPropertyChallengeTests(unittest.TestCase):
    def test_exact_current_bounded_challenges_pass_without_closing_leaf(self):
        out=r10.evaluate()
        self.assertTrue(out["pass"],out)
        self.assertTrue(all(out["checks"].values()))
        self.assertFalse(out["r10_execution_leaf_closed"])
        self.assertFalse(out["r10_root_closed"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertTrue(all(out["still_open_property_truth"].values()))

    def test_arbitrary_default_across_nondominated_replacements_fails(self):
        unsafe={
            "pass":True,
            "status":"OPTION_PRESERVING_DEFAULT_SELECTED",
            "global_preferred_default_capability_id":"quality-leaning",
            "global_active_capability_ids":["quality-leaning","generalization-leaning"],
        }
        with patch.object(r10.options,"select_effective_for_scope",return_value=unsafe):
            out=r10.evaluate()
        self.assertFalse(out["pass"])
        self.assertFalse(out["checks"]["NONDOMINATED_ALTERNATIVES_DO_NOT_GET_ARBITRARY_DEFAULT"])

    def test_broad_policy_acquisition_without_minimality_fails(self):
        original=r10.decision.compile_minimum_information_contract
        def unsafe(gap,decision):
            out=deepcopy(original(gap,decision))
            out["requests"][0]["broad_acquisition_forbidden_without_minimality_proof"]=False
            return out
        with patch.object(r10.decision,"compile_minimum_information_contract",side_effect=unsafe):
            out=r10.evaluate()
        self.assertFalse(out["pass"])
        self.assertFalse(out["checks"]["MISSING_POLICY_PARAMETERS_COMPILE_TO_MINIMUM_INFORMATION"])

    def test_missing_multiplicity_escalation_fails(self):
        original=r10._load
        def load(rel,sha):
            out=deepcopy(original(rel,sha))
            if rel==r10.PROFILE_REL:
                out["escalation_triggers"]=[
                    x for x in out["escalation_triggers"]
                    if x!="MODEL_OR_ANALYSIS_MULTIPLICITY_DECISION_SENSITIVE"
                ]
            return out
        with patch.object(r10,"_load",side_effect=load):
            out=r10.evaluate()
        self.assertFalse(out["pass"])
        self.assertFalse(out["checks"]["MULTIPLICITY_AND_VETO_CONDITIONS_TRIGGER_ESCALATION_OR_ABSTENTION"])

    def test_distinct_semantic_contract_collapse_fails(self):
        with patch.object(
            r10.options,
            "select_active_frontier",
            return_value={"active_capability_ids":["policy-b"]},
        ):
            out=r10.evaluate()
        self.assertFalse(out["pass"])
        self.assertFalse(out["checks"]["DIFFERENT_SEMANTIC_CONTRACTS_DO_NOT_DOMINATE_EACH_OTHER"])


if __name__=="__main__":
    unittest.main(verbosity=2)
