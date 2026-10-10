from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from canonical.runtime import general_adequate_decision_controller_v1 as controller
from canonical.runtime import general_adequate_decision_fixed_point_v2 as fixed


class R2FixedPointBoundTruthReentryV1Tests(unittest.TestCase):
    @staticmethod
    def _request():
        return {
            "task_id": "R2_V86_BOUND_TRUTH_REENTRY",
            "goal": "Choose and realize the adequate action for this bounded decision.",
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
            "goal_satisfaction_binding": {"receipt": {}, "verification": {}},
        }

    @staticmethod
    def _raw_contract():
        return {
            "pass": True,
            "task_contract_sha256": "contract-sha",
            "task_sha256": "goal-sha",
            "nonwhitespace_source_coverage_complete": True,
            "acceptance_contract": {"obligations": [{"id": "o1"}]},
        }

    @staticmethod
    def _goal_binding_pass():
        return {
            "pass": True,
            "status": "PASS__GOAL_TO_DECISION_CONTEXT_AUTHENTICATED",
            "goal_sha256": "g",
            "decision_payload_sha256": "d",
        }

    @staticmethod
    def _goal_satisfaction_pass():
        return {
            "pass": True,
            "status": "PASS__ACTUAL_GOAL_SATISFACTION_AUTHENTICATED",
            "policy_id": "policy.p",
            "realization_sha256": "r",
        }

    @staticmethod
    def _decision_pass():
        return {
            "pass": True,
            "status": "PASS__P3_REAL_CONTEXT_BOUND_RELEVANCE_CEGAR_LOOP",
            "selected_policy_id": "policy.p",
            "selected_claim_ids": ["A"],
            "rendered_text": "Do the certified action.",
            "p3_contract_cell_authorized": True,
        }

    @staticmethod
    def _information_open(predicate_id: str):
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "BOUND_RELEVANCE_CEGAR_LOOP_UNSATISFIED",
            "detail": {
                "loop_result": {
                    "pass": False,
                    "status": "OPEN__SELECTED_PREDICATE_PROOF_PAYLOAD_REQUIRED",
                    "reason": "SELECTED_FORMULA_ATOM_HAS_NO_TRUTH_CERTIFICATE_PAYLOAD",
                    "detail": {"predicate_id": predicate_id},
                }
            },
        }

    def test_fixed_point_bound_truth_origin_is_consumed_before_success(self):
        predicate_id = "source-condition-sha256:critical"
        truth_payload = {
            "truth_kind": "TEST_TRUTH_KIND",
            "predicate_id": predicate_id,
            "source_text": "bound evidence",
        }
        proposal = Mock(return_value={
            "request_patch": {
                "information_origin_by_predicate_id": {
                    predicate_id: {
                        "context_value_bound": True,
                        "context_binding_id": "binding:critical",
                        "bound_truth_payload": truth_payload,
                    }
                }
            }
        })

        observed = []

        def p3(payload, *, repo_root=None):
            loop = payload["bound_relevance_cegar_loop"]
            by_predicate = loop["truth_payloads_by_predicate_id"]
            observed.append(dict(by_predicate))
            if predicate_id not in by_predicate:
                return self._information_open(predicate_id)
            self.assertEqual(by_predicate[predicate_id], truth_payload)
            return self._decision_pass()

        with patch.object(
            fixed.direct_adequacy,
            "preflight",
            return_value={"matched": False, "direct_route_semantic_open": False},
        ), patch.object(
            controller,
            "compile_contract",
            return_value=self._raw_contract(),
        ), patch.object(
            controller,
            "_authenticate_goal_binding",
            return_value=self._goal_binding_pass(),
        ), patch.object(
            controller,
            "evaluate_p3",
            side_effect=p3,
        ), patch.object(
            controller,
            "_authenticate_goal_satisfaction_binding",
            return_value=self._goal_satisfaction_pass(),
        ):
            out = fixed.run(
                self._request(),
                proposal_provider=proposal,
                max_fixed_point_steps=2,
            )

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["r2_fixed_point_status"],
            "PASS__R2_ADAPTIVE_FIXED_POINT_CLOSED",
        )
        proposal.assert_called_once()
        self.assertEqual(len(observed), 3)
        self.assertNotIn(predicate_id, observed[0])
        self.assertNotIn(predicate_id, observed[1])
        self.assertEqual(observed[2][predicate_id], truth_payload)

        controller_steps = [
            row for row in out["r2_fixed_point_trace"]
            if row.get("kind") == "V1_CONTROLLER"
        ]
        self.assertEqual(len(controller_steps), 2)
        self.assertFalse(controller_steps[0]["pass"])
        self.assertTrue(controller_steps[1]["pass"])

        packet = proposal.call_args.args[0]
        self.assertEqual(packet["next_required_edge"], "MINIMUM_USER_CONTROLLED_SPECIFICATION")
        self.assertFalse(packet["provider_is_semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
