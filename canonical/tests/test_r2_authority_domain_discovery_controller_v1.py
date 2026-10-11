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
            "task_id": "R2_AUTHORITY_DISCOVERY_DEFAULT",
            "goal": "Choose the adequate action using the delegated external fact.",
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
            "information_origin_by_predicate_id": {
                predicate_id: {
                    "context_value_bound": False,
                    "information_owner": "EXTERNAL_WORLD",
                    "source_scope": {
                        "kind": "UNBOUND_SOURCE",
                        "query": "World Bank SP.POP.TOTL official indicator",
                        "authority_domains": ["worldbank.org"],
                        "timeout_s": 20,
                        "max_bytes": 1500000,
                    },
                    "discovery_delegated": True,
                }
            },
        }

    def test_default_delegated_discovery_materializes_before_checker_handoff(self):
        predicate_id = "source-condition-sha256:critical"
        req = self.request(predicate_id)
        candidate = {
            "schema": c.authority_discovery_provider.SCHEMA,
            "pass": True,
            "status": "PASS__AUTHORITY_DOMAIN_SOURCE_CANDIDATE_DISCOVERED",
            "candidate_only": True,
            "chosen_url": "https://data.worldbank.org/indicator/SP.POP.TOTL",
            "chosen_host": "data.worldbank.org",
            "semantic_truth_authority": False,
        }
        materialized = {
            "schema": c.authority_candidate_materializer.SCHEMA,
            "kind": c.authority_candidate_materializer.KIND,
            "pass": True,
            "status": "PASS__AUTHORITY_CANDIDATE_CONTENT_ADDRESSED_MATERIALIZED",
            "retrieval_materialization_verified": True,
            "source_text": "materialized bytes",
            "source_id": "https://data.worldbank.org/indicator/SP.POP.TOTL",
            "source_sha256": "a" * 64,
            "provider_authority": False,
            "semantic_truth_authority": False,
        }
        default = Mock(return_value=candidate)
        opened = self.opened(predicate_id)

        with patch.object(c, "compile_contract", return_value=self.raw_contract()), \
             patch.object(c, "_authenticate_goal_binding", return_value=self.goal_binding()), \
             patch.object(c, "evaluate_p3", return_value=opened) as p3, \
             patch.object(c.authority_discovery_provider, "provide", default), \
             patch.object(
                 c.authority_candidate_materializer,
                 "materialize",
                 return_value=materialized,
             ) as materialize:
            out = c.run(req)

        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__MATERIALIZED_AUTHORITY_SOURCE_CHECKER_ADAPTER_REQUIRED",
        )
        self.assertEqual(
            out["next_required_edge"],
            "CHECKER_SPECIFIC_AUTHENTICATED_SOURCE_INTERPRETATION",
        )
        self.assertEqual(out["retrieval_candidate"], candidate)
        self.assertEqual(out["materialized_authority_source"], materialized)
        self.assertEqual(
            out["information_trace"][-1]["kind"],
            "AUTHORITY_CANDIDATE_MATERIALIZATION",
        )
        self.assertTrue(
            out["information_trace"][-1]["materialization_verified"]
        )
        default.assert_called_once()
        materialize.assert_called_once()
        packet = default.call_args.args[0]
        self.assertTrue(packet["external_research_authorized"])
        self.assertEqual(
            packet["source_scope"],
            req["information_origin_by_predicate_id"][predicate_id]["source_scope"],
        )
        p3.assert_called_once()

    def test_materialization_failure_preserves_candidate_edge(self):
        predicate_id = "source-condition-sha256:critical"
        req = self.request(predicate_id)
        candidate = {
            "schema": c.authority_discovery_provider.SCHEMA,
            "pass": True,
            "status": "PASS__AUTHORITY_DOMAIN_SOURCE_CANDIDATE_DISCOVERED",
            "candidate_only": True,
            "chosen_url": "https://data.worldbank.org/indicator/SP.POP.TOTL",
            "chosen_host": "data.worldbank.org",
            "semantic_truth_authority": False,
        }
        materialization_failure = {
            "schema": c.authority_candidate_materializer.SCHEMA,
            "kind": c.authority_candidate_materializer.KIND,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "AUTHORITY_REDIRECT_OUTSIDE_AUTHORITY_DOMAINS",
            "semantic_truth_authority": False,
        }
        default = Mock(return_value=candidate)

        with patch.object(c, "compile_contract", return_value=self.raw_contract()), \
             patch.object(c, "_authenticate_goal_binding", return_value=self.goal_binding()), \
             patch.object(c, "evaluate_p3", return_value=self.opened(predicate_id)), \
             patch.object(c.authority_discovery_provider, "provide", default), \
             patch.object(
                 c.authority_candidate_materializer,
                 "materialize",
                 return_value=materialization_failure,
             ):
            out = c.run(req)

        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__RETRIEVAL_CANDIDATE_MATERIALIZATION_REQUIRED",
        )
        self.assertEqual(
            out["next_required_edge"],
            "CHECKER_CONSUMABLE_MATERIALIZATION_FROM_AUTHORITY_CANDIDATE",
        )
        self.assertEqual(
            out["information_provider_failure"],
            materialization_failure,
        )

    def test_default_discovery_failure_stays_research_open(self):
        predicate_id = "source-condition-sha256:critical"
        req = self.request(predicate_id)
        failure = {
            "schema": c.authority_discovery_provider.SCHEMA,
            "pass": False,
            "status": "OPEN__NO_AUTHORITY_DOMAIN_CANDIDATE_DISCOVERED",
            "reason": "AUTHORITATIVE_SOURCE_NOT_DISCOVERED",
            "semantic_truth_authority": False,
        }
        default = Mock(return_value=failure)

        with patch.object(c, "compile_contract", return_value=self.raw_contract()), \
             patch.object(c, "_authenticate_goal_binding", return_value=self.goal_binding()), \
             patch.object(c, "evaluate_p3", return_value=self.opened(predicate_id)) as p3, \
             patch.object(c.authority_discovery_provider, "provide", default):
            out = c.run(req)

        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__DELEGATED_MINIMUM_RESEARCH_REQUIRED")
        self.assertEqual(
            out["information_trace"][-1]["ingestion_status"],
            "AUTHORITY_DISCOVERY_NOT_VERIFIED",
        )
        p3.assert_called_once()

    def test_custom_provider_overrides_default_discovery_provider(self):
        predicate_id = "source-condition-sha256:critical"
        req = self.request(predicate_id)
        custom = Mock(return_value=None)
        default = Mock(return_value=None)

        with patch.object(c, "compile_contract", return_value=self.raw_contract()), \
             patch.object(c, "_authenticate_goal_binding", return_value=self.goal_binding()), \
             patch.object(c, "evaluate_p3", return_value=self.opened(predicate_id)), \
             patch.object(c.authority_discovery_provider, "provide", default):
            out = c.run(req, information_provider=custom)

        self.assertFalse(out["pass"])
        custom.assert_called_once()
        default.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
