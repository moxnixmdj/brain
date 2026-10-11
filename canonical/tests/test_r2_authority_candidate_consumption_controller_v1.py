from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from canonical.runtime import general_adequate_decision_controller_v1 as c
from canonical.runtime import regcap_four_way_governing_requirement_discriminator_v1 as four


PID = "regcap-loss-cushion-sha256:original"


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
    def decision_pass():
        return {
            "pass": True,
            "status": "PASS__P3_REAL_CONTEXT_BOUND_RELEVANCE_CEGAR_LOOP",
            "selected_policy_id": "policy.p",
            "rendered_text": "Do the certified action.",
        }

    @staticmethod
    def typed_request():
        return {
            "request_kind": "ACQUIRE_ONE_AUTHENTICATED_GOVERNING_REQUIREMENT_OBSERVATION",
            "scope_id": four.SCOPE_ID,
            "observation_id": four.OBSERVATION_ID,
            "candidate_concept_ids": list(four.DOMAIN),
            "allowed_outcomes": dict(four.OUTCOMES),
            "minimum_observation_count": 1,
            "independent_verification_required": True,
        }

    def opened(self):
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "BOUND_RELEVANCE_CEGAR_LOOP_UNSATISFIED",
            "detail": {
                "loop_result": {
                    "pass": False,
                    "status": "OPEN__SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED",
                    "reason": "SELECTED_SEMANTIC_TRUTH_CERTIFICATE_RETURNED_UNKNOWN_OR_FAILED",
                    "detail": {"predicate_id": PID},
                    "next_information_request": self.typed_request(),
                    "next_required_edge": "REGCAP_LOSS_CUSHION_MINIMUM_POLICY_CHANGING_INFORMATION",
                }
            },
        }

    def request(self):
        return {
            "task_id": "R2_AUTHORITY_CANDIDATE_CONSUMPTION",
            "goal": "Resolve the bounded regulatory-capital ambiguity.",
            "decision_payload": {
                "context_id": "ctx",
                "v3_input": {"task": {}},
                "bound_relevance_cegar_loop": {
                    "cegar_problem": {},
                    "truth_payloads_by_discriminator_id": {},
                    "truth_payloads_by_predicate_id": {
                        PID: {
                            "truth_kind": "REGCAP_LOSS_CUSHION_GROUNDING",
                            "predicate_id": PID,
                            "claim_kind": "RELATIVE_RIVAL_SELECTION",
                            "source_text": "loss-absorbing cushion",
                            "source_id": "doc:original",
                            "start": 0,
                            "end": len("loss-absorbing cushion"),
                            "target_concept_id": "REGCAP::MREL",
                        }
                    },
                    "source_positive_selection_contracts": {},
                },
            },
            "goal_to_decision_binding": {"receipt": {}, "verification": {}},
            "goal_satisfaction_binding": {"receipt": {}, "verification": {}},
            "information_origin_by_predicate_id": {
                PID: {
                    "context_value_bound": False,
                    "information_owner": "EXTERNAL_WORLD",
                    "source_scope": {
                        "kind": "UNBOUND_SOURCE",
                        "query": "official governing requirement",
                        "authority_domains": ["example.org"],
                        "timeout_s": 20,
                        "max_bytes": 1500000,
                    },
                    "discovery_delegated": True,
                }
            },
        }

    def test_default_discovery_reenters_p3_with_enriched_original_truth_payload(self):
        candidate = {
            "schema": c.authority_discovery_provider.SCHEMA,
            "pass": True,
            "status": "PASS__AUTHORITY_DOMAIN_SOURCE_CANDIDATE_DISCOVERED",
            "candidate_only": True,
            "semantic_truth_authority": False,
            "chosen_url": "https://data.example.org/requirement",
            "chosen_host": "data.example.org",
            "query": "official governing requirement",
            "authority_domains": ["example.org"],
        }
        enriched = {
            **self.request()["decision_payload"]["bound_relevance_cegar_loop"][
                "truth_payloads_by_predicate_id"
            ][PID],
            "governing_requirement_candidate": {
                "chosen_url": candidate["chosen_url"],
                "chosen_host": candidate["chosen_host"],
            },
        }
        discovery = Mock(return_value=candidate)
        adapter = Mock(return_value={
            "pass": True,
            "status": "PASS__AUTHORITY_CANDIDATE_BOUND_TO_EXISTING_REGCAP_TRUTH_CHECKER",
            "truth_payload_candidates": [enriched],
            "candidate_count": 1,
            "downstream_checker_refetch_required": True,
            "original_predicate_identity_preserved": True,
        })
        seen = []

        def p3(payload, *, repo_root=None):
            seen.append(payload)
            return self.opened() if len(seen) == 1 else self.decision_pass()

        with patch.object(c, "compile_contract", return_value=self.raw_contract()), \
             patch.object(c, "_authenticate_goal_binding", return_value=self.goal_binding()), \
             patch.object(c, "evaluate_p3", side_effect=p3), \
             patch.object(c.authority_discovery_provider, "provide", discovery), \
             patch.object(c.authority_candidate_adapter, "adapt", adapter), \
             patch.object(c, "_authenticate_goal_satisfaction_binding", return_value=self.goal_acceptance()):
            out = c.run(self.request())

        self.assertTrue(out["pass"], out)
        self.assertEqual(len(seen), 2)
        rows = seen[1]["bound_relevance_cegar_loop"][
            "truth_payloads_by_predicate_id"
        ][PID]
        self.assertIsInstance(rows, list)
        self.assertEqual(len(rows), 2)
        self.assertNotIn("governing_requirement_candidate", rows[0])
        self.assertEqual(
            rows[1]["governing_requirement_candidate"]["chosen_url"],
            candidate["chosen_url"],
        )
        self.assertEqual(rows[1]["predicate_id"], PID)
        self.assertEqual(
            out["information_trace"][-1]["ingestion_status"],
            "AUTHORITY_DISCOVERY_CANDIDATE_BOUND_TO_EXISTING_TRUTH_CHECKER",
        )
        self.assertTrue(
            out["information_trace"][-1]["original_predicate_identity_preserved"]
        )
        discovery.assert_called_once()
        adapter.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
