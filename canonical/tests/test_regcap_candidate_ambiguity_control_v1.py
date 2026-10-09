from __future__ import annotations

import unittest

from canonical.runtime import minimum_information_origin_policy_v1 as origin
from canonical.runtime import regcap_candidate_ambiguity_control_v1 as control
from canonical.runtime import regcap_property_candidate_discovery_v1 as discovery


IDS = ["REGCAP::CCOB", "REGCAP::CCYB", "REGCAP::TLAC"]


def candidates():
    return {
        "schema": discovery.SCHEMA,
        "pass": True,
        "status": "OPEN__NON_UNIQUE_PROPERTY_CANDIDATES",
        "candidate_generation_authority": True,
        "candidate_set_complete_relative_to_bound_rivals": True,
        "open_world_candidate_set_complete": False,
        "candidate_concept_ids": list(IDS),
        "candidates": [
            {
                "concept_id": "REGCAP::CCOB",
                "positive_evidence_targets": ["POSITION::ABOVE_REGULATORY_MINIMUM"],
            },
            {
                "concept_id": "REGCAP::CCYB",
                "positive_evidence_targets": [
                    "TRIGGER::EXCESS_CREDIT_GROWTH_SYSTEM_WIDE_RISK"
                ],
            },
            {
                "concept_id": "REGCAP::TLAC",
                "positive_evidence_targets": ["REGIME::RESOLUTION"],
            },
        ],
    }


def bounded_scope():
    return {
        "kind": control.BOUND_SCOPE,
        "scope_complete": True,
        "candidate_ids": list(IDS),
    }


class Tests(unittest.TestCase):
    def test_open_world_candidate_set_never_becomes_identity(self):
        out = control.plan(
            candidates(),
            mapping_scope={"kind": "OPEN_WORLD", "scope_complete": False},
            observation_set_complete=False,
            information_owner=origin.USER_SPECIFICATION,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__OPEN_WORLD_MAPPING_REQUIRES_MINIMUM_ADDITIONAL_INFORMATION",
        )
        self.assertEqual(out["action"], "ASK_USER_MINIMUM_CLARIFICATION")
        self.assertIsNone(out["mapped_concept_id"])
        self.assertFalse(out["semantic_identity_authority"])

    def test_bounded_rivals_with_no_current_observation_route_to_minimum_user_context(self):
        out = control.plan(
            candidates(),
            mapping_scope=bounded_scope(),
            observations=[],
            observation_set_complete=True,
            information_owner="USER_INTENT",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__MINIMUM_USER_CONTEXT_REQUIRED")
        self.assertEqual(out["action"], "ASK_USER_MINIMUM_CLARIFICATION")
        self.assertGreater(len(out["ambiguity_control"]["unresolved_pairs"]), 0)

    def test_declared_resolution_observation_is_selected_when_it_is_cheapest_separator(self):
        out = control.plan(
            candidates(),
            mapping_scope=bounded_scope(),
            observations=[
                {
                    "observation_id": "OBS::RESOLUTION_REGIME",
                    "outcome_map_complete": True,
                    "cost_units": 1,
                    "outcomes": {
                        "REGCAP::CCOB": False,
                        "REGCAP::CCYB": False,
                        "REGCAP::TLAC": True,
                    },
                },
                {
                    "observation_id": "OBS::EXPENSIVE_PAIR_SEPARATOR",
                    "outcome_map_complete": True,
                    "cost_units": 5,
                    "outcomes": {
                        "REGCAP::CCOB": "A",
                        "REGCAP::CCYB": "B",
                        "REGCAP::TLAC": "C",
                    },
                },
            ],
            observation_set_complete=True,
            information_owner="SYSTEM_MODEL",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__MINIMUM_POLICY_CHANGING_DISCRIMINATOR_READY",
        )
        self.assertEqual(out["next_observation_id"], "OBS::EXPENSIVE_PAIR_SEPARATOR")
        self.assertEqual(out["minimum_worst_case_cost_units"], 5.0)
        # The cheap binary observation cannot finish the worst case because it leaves
        # CCoB and CCyB unresolved; exact minimax correctly chooses the cost-5 complete split.

    def test_bound_source_routes_to_source_only_when_current_model_cannot_separate(self):
        out = control.plan(
            candidates(),
            mapping_scope=bounded_scope(),
            observations=[],
            observation_set_complete=True,
            information_owner=origin.EXTERNAL_WORLD,
            source_scope={"kind": origin.BOUND_SOURCE, "source_id": "doc:A"},
            discovery_delegated=True,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__STRONGER_AUTHENTIC_INFORMATION_REQUIRED")
        self.assertEqual(out["action"], "OBSERVE_BOUND_SOURCE_ONLY")
        self.assertTrue(out["minimum_information_route"]["bound_source_only"])
        self.assertFalse(
            out["minimum_information_route"]["external_research_authorized"]
        )

    def test_unbound_external_world_with_delegated_discovery_authorizes_minimum_research(self):
        out = control.plan(
            candidates(),
            mapping_scope={"kind": "OPEN_WORLD", "scope_complete": False},
            observation_set_complete=False,
            information_owner=origin.EXTERNAL_WORLD,
            discovery_delegated=True,
        )
        self.assertEqual(out["action"], "RESEARCH_MINIMUM_AUTHENTICATED_FACT")
        self.assertTrue(
            out["minimum_information_route"]["external_research_authorized"]
        )
        self.assertFalse(out["semantic_truth_authority"])

    def test_scope_mismatch_fails_closed(self):
        scope = bounded_scope()
        scope["candidate_ids"] = IDS[:-1]
        out = control.plan(
            candidates(),
            mapping_scope=scope,
            observations=[],
            observation_set_complete=True,
            information_owner="USER_INTENT",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "BOUND_RIVAL_SCOPE_DOES_NOT_MATCH_AUTHENTICATED_CANDIDATE_SET",
        )

    def test_no_authority_or_terminal_credit_is_created(self):
        out = control.plan(
            candidates(),
            mapping_scope={"kind": "OPEN_WORLD", "scope_complete": False},
            observation_set_complete=False,
            information_owner=origin.USER_SPECIFICATION,
        )
        for key in (
            "semantic_identity_authority",
            "semantic_truth_authority",
            "policy_adequacy_authority",
            "execution_authority",
            "acceptance_authority",
            "promotion_authority",
            "terminal_authority",
        ):
            self.assertFalse(out[key])
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
