from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from canonical.runtime import general_adequate_decision_controller_v1 as controller


PRED = "source-condition-sha256:critical"


def base_request():
    return {
        "task_id": "MIN_INFO_ORIGIN_INTEGRATION",
        "goal": "Choose the adequate action.",
        "decision_payload": {
            "context_id": "ctx",
            "v3_input": {"task": {}},
            "bound_relevance_cegar_loop": {
                "cegar_problem": {},
                "truth_payloads_by_discriminator_id": {},
                "truth_payloads_by_predicate_id": {},
                "source_positive_selection_contracts": {},
            },
        },
        "goal_to_decision_binding": {"receipt": {}, "verification": {}},
    }


def raw_contract():
    return {
        "pass": True,
        "task_contract_sha256": "contract-sha",
        "task_sha256": "goal-sha",
        "nonwhitespace_source_coverage_complete": True,
        "acceptance_contract": {"obligations": [{"obligation_id": "RAWREQ:o1"}]},
    }


def goal_binding():
    return {"pass": True, "status": "PASS__GOAL_TO_DECISION_CONTEXT_AUTHENTICATED"}


def information_open():
    return {
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": "BOUND_RELEVANCE_CEGAR_LOOP_UNSATISFIED",
        "detail": {
            "loop_result": {
                "pass": False,
                "status": "OPEN__SELECTED_PREDICATE_PROOF_PAYLOAD_REQUIRED",
                "reason": "SELECTED_FORMULA_ATOM_HAS_NO_TRUTH_CERTIFICATE_PAYLOAD",
                "detail": {"predicate_id": PRED},
            }
        },
    }


class Tests(unittest.TestCase):
    def _run_open(self, origin=None):
        req = base_request()
        if origin is not None:
            req["information_origin_by_predicate_id"] = {PRED: origin}
        with patch.object(controller, "compile_contract", return_value=raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=goal_binding()), \
             patch.object(controller, "evaluate_p3", return_value=information_open()):
            return controller.run(req)

    def test_unclassified_missing_information_defaults_to_ask_not_research(self):
        out = self._run_open()
        self.assertEqual(out["status"], "OPEN__USER_MINIMUM_CLARIFICATION_REQUIRED")
        plan = out["next_information_request"]["acquisition_plan"]
        self.assertEqual(plan["action"], "ASK_USER_MINIMUM_CLARIFICATION")
        self.assertFalse(plan["external_research_authorized"])

    def test_user_specification_routes_to_minimum_clarification(self):
        out = self._run_open({
            "information_owner": "USER_SPECIFICATION",
            "context_value_bound": False,
            "clarification_key": "product_and_vendor",
        })
        self.assertEqual(out["status"], "OPEN__USER_MINIMUM_CLARIFICATION_REQUIRED")
        self.assertEqual(out["next_required_edge"], "MINIMUM_USER_CONTROLLED_SPECIFICATION")
        self.assertFalse(out["next_information_request"]["external_research_authorized"])

    def test_bound_external_source_does_not_expand_search_scope(self):
        out = self._run_open({
            "information_owner": "EXTERNAL_WORLD",
            "context_value_bound": False,
            "source_scope": {
                "kind": "BOUND_SOURCE",
                "source_id": "amazon:listing:vendor-x",
            },
            "discovery_delegated": False,
        })
        self.assertEqual(out["status"], "OPEN__BOUND_SOURCE_OBSERVATION_REQUIRED")
        plan = out["next_information_request"]["acquisition_plan"]
        self.assertEqual(plan["action"], "OBSERVE_BOUND_SOURCE_ONLY")
        self.assertEqual(plan["source_id"], "amazon:listing:vendor-x")
        self.assertFalse(out["next_information_request"]["external_research_authorized"])

    def test_explicit_discovery_delegation_is_separate_research_problem(self):
        out = self._run_open({
            "information_owner": "EXTERNAL_WORLD",
            "context_value_bound": False,
            "source_scope": {"kind": "UNBOUND_SOURCE"},
            "discovery_delegated": True,
        })
        self.assertEqual(out["status"], "OPEN__DELEGATED_MINIMUM_RESEARCH_REQUIRED")
        self.assertTrue(out["next_information_request"]["external_research_authorized"])

    def test_bound_context_payload_is_reused_before_provider(self):
        req = base_request()
        req["information_origin_by_predicate_id"] = {
            PRED: {
                "information_owner": "USER_SPECIFICATION",
                "context_value_bound": True,
                "context_binding_id": "conversation:product-vendor",
                "bound_truth_payload": {"source_text": "already-bound-context"},
            }
        }
        provider = Mock()
        observed = []

        def p3(payload, *, repo_root=None):
            observed.append(payload)
            if len(observed) == 1:
                return information_open()
            return {
                "pass": True,
                "status": "PASS__P3_REAL_CONTEXT_BOUND_RELEVANCE_CEGAR_LOOP",
                "selected_policy_id": "policy.p",
                "rendered_text": "Do it.",
            }

        with patch.object(controller, "compile_contract", return_value=raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=goal_binding()), \
             patch.object(controller, "evaluate_p3", side_effect=p3), \
             patch.object(
                 controller,
                 "_authenticate_goal_satisfaction_binding",
                 return_value={"pass": True, "status": "PASS"},
             ):
            out = controller.run(req, information_provider=provider)

        self.assertTrue(out["pass"], out)
        provider.assert_not_called()
        inserted = observed[1]["bound_relevance_cegar_loop"][
            "truth_payloads_by_predicate_id"
        ]
        self.assertEqual(inserted[PRED], {"source_text": "already-bound-context"})
        self.assertEqual(out["information_trace"][0]["kind"], "BOUND_CONTEXT_REUSE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
