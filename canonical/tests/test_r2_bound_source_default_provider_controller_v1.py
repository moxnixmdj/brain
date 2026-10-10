from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from canonical.runtime import general_adequate_decision_controller_v1 as c


class Tests(unittest.TestCase):
    @staticmethod
    def raw_contract():
        return {
            "pass": True,
            "task_contract_sha256": "contract-sha",
            "nonwhitespace_source_coverage_complete": True,
            "acceptance_contract": {"obligations": [{"obligation_id": "RAWREQ:o1"}]},
        }

    @staticmethod
    def goal_binding():
        return {"pass": True, "status": "PASS__GOAL_TO_DECISION_CONTEXT_AUTHENTICATED"}

    @staticmethod
    def goal_acceptance():
        return {"pass": True, "status": "PASS__ACTUAL_GOAL_SATISFACTION_AUTHENTICATED"}

    @staticmethod
    def decision():
        return {
            "pass": True,
            "status": "PASS__P3_REAL_CONTEXT_BOUND_RELEVANCE_CEGAR_LOOP",
            "selected_policy_id": "policy.p",
            "rendered_text": "Do the certified action.",
        }

    @staticmethod
    def opened(predicate_id):
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

    def request(self, predicate_id):
        return {
            "task_id": "R2_BOUND_SOURCE_DEFAULT",
            "goal": "Choose the adequate bounded action.",
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
            "information_origin_by_predicate_id": {
                predicate_id: {
                    "context_value_bound": False,
                    "information_owner": "EXTERNAL_WORLD",
                    "source_scope": {
                        "kind": "BOUND_SOURCE",
                        "source_id": "bound.finance",
                        "policy_url": "https://evidence.example/policy.txt",
                        "policy_source_id": "policy:bound",
                        "policy_sha256": "1" * 64,
                        "fact_url": "https://evidence.example/facts.json",
                        "fact_source_id": "facts:bound",
                        "fact_sha256": "2" * 64,
                    },
                    "discovery_delegated": False,
                }
            },
        }

    def test_no_custom_provider_uses_default_only_for_bound_source_and_preserves_scope(self):
        predicate_id = "source-condition-sha256:critical"
        req = self.request(predicate_id)
        observed = []
        raw_material = {
            "kind": c.source_proof_material.KIND,
            "source_text": "Total exposure means exposure_amount.",
            "source_id": "policy:bound",
            "fact_source": b'{"schema_id":"FINANCE_TYPED_CONTEXT_V1","fields":{}}',
            "fact_source_id": "facts:bound",
        }
        default = Mock(return_value=raw_material)

        def p3(payload, *, repo_root=None):
            observed.append(payload)
            return self.opened(predicate_id) if len(observed) == 1 else self.decision()

        with patch.object(c, "compile_contract", return_value=self.raw_contract()), \
             patch.object(c, "_authenticate_goal_binding", return_value=self.goal_binding()), \
             patch.object(c, "evaluate_p3", side_effect=p3), \
             patch.object(c.bound_source_provider, "provide", default), \
             patch.object(c, "_authenticate_goal_satisfaction_binding", return_value=self.goal_acceptance()):
            out = c.run(req)

        self.assertTrue(out["pass"], out)
        default.assert_called_once()
        packet = default.call_args.args[0]
        self.assertEqual(packet["acquisition_plan"]["action"], "OBSERVE_BOUND_SOURCE_ONLY")
        self.assertEqual(packet["source_scope"], req["information_origin_by_predicate_id"][predicate_id]["source_scope"])
        inserted = observed[1]["bound_relevance_cegar_loop"]["truth_payloads_by_predicate_id"][predicate_id]
        self.assertEqual(len(inserted), 2)
        self.assertFalse(out["terminal_authority"])

    def test_custom_provider_overrides_default_bound_source_provider(self):
        predicate_id = "source-condition-sha256:critical"
        req = self.request(predicate_id)
        custom = Mock(return_value={"source_text": "legacy proposal"})
        default = Mock(return_value=None)
        seen = []

        def p3(payload, *, repo_root=None):
            seen.append(payload)
            return self.opened(predicate_id) if len(seen) == 1 else self.decision()

        with patch.object(c, "compile_contract", return_value=self.raw_contract()), \
             patch.object(c, "_authenticate_goal_binding", return_value=self.goal_binding()), \
             patch.object(c, "evaluate_p3", side_effect=p3), \
             patch.object(c.bound_source_provider, "provide", default), \
             patch.object(c, "_authenticate_goal_satisfaction_binding", return_value=self.goal_acceptance()):
            out = c.run(req, information_provider=custom)

        self.assertTrue(out["pass"], out)
        custom.assert_called_once()
        default.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
