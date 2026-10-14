from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import one_shot_reality_closure_v2 as v2


def closure(
    *,
    status,
    passed=False,
    internal=(),
    evidence=(),
    external=False,
    initial="i",
    final="f",
):
    return {
        "schema": "PROJECT_BRAIN_ONE_SHOT_VERIFIED_CLOSURE_V1",
        "status": status,
        "pass": passed,
        "fixed_point": True,
        "closure_class": "x",
        "initial_frontier_digest": initial,
        "final_frontier_digest": final,
        "final_state_sha256": "a" * 64,
        "irreducible_external_information_proved": external,
        "residual": {
            "internal_blockers": list(internal),
            "evidence_blockers": list(evidence),
            "irreducible_external_information_proved": external,
        },
    }


class RealityClosureV2Tests(unittest.TestCase):
    def test_context_capacity_arithmetic_for_rank13_class(self):
        out = v2.certify_context_capacity_repair(
            observed_request_tokens=9202,
            configured_context_tokens=8192,
            candidate_context_tokens=16384,
            headroom_tokens=256,
        )
        self.assertTrue(out["arithmetic_capacity_pass"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["strict_required_context_tokens"], 9459)
        self.assertIn("LIVE_ZERO_EXPOSURE_RECEIPT_REQUIRED", out["status"])

    def test_context_capacity_live_gate_requires_exact_identity_and_zero_exposure(self):
        receipt = {
            "benchmark_exposure_count": 0,
            "observed_probe_tokens": 10000,
            "candidate_context_tokens": 16384,
            "live_probe_pass": True,
            "model_sha256": "model",
            "runtime_commit": "runtime",
            "receipt_sha256": "b" * 64,
        }
        out = v2.certify_context_capacity_repair(
            observed_request_tokens=9202,
            configured_context_tokens=8192,
            candidate_context_tokens=16384,
            headroom_tokens=256,
            live_probe_receipt=receipt,
            expected_model_sha256="model",
            expected_runtime_commit="runtime",
        )
        self.assertTrue(out["pass"])

    def test_internal_residual_compiles_to_constructive_gap(self):
        out = v2.compile_gap_contract(
            closure(status="OPEN", internal=("ROOT1_GAP",))
        )
        self.assertEqual(out["gap_class"], "CONSTRUCTIVE_CAPABILITY_GAP")
        self.assertFalse(out["verification_authority_mutation_allowed"])

    def test_unproved_externality_routes_to_pending_acquisition_not_external(self):
        c = closure(
            status="OPEN",
            evidence=("MISSING_FACT",),
            external=False,
        )
        with patch.object(v2.v1, "run", return_value=c):
            out = v2.run(
                repo_root=".",
                reality_acquisition_provider=lambda contract: {
                    "pass": True,
                    "frontier_changed": True,
                    "verification_authority_mutated": False,
                    "receipt_sha256": "c" * 64,
                },
            )
        self.assertFalse(out["pass"])
        self.assertIn("PENDING_ACQUISITION_OR_EXPERIMENT", out["status"])
        self.assertEqual(
            out["gap_contract"]["gap_class"],
            "PENDING_ACQUISITION_OR_EXPERIMENT",
        )

    def test_externality_guard_does_not_misroute_evidence_to_synthesis(self):
        row = closure(
            status="OPEN__INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
            internal=("EXTERNALITY_NOT_PROVED__CONTINUE_INTERNAL_SEARCH_SYNTHESIS_OR_BYPASS",),
            evidence=("NEW_EXPERIENCE_REQUIRED__HISTORICAL_FAILURE_REPLAY_CAPSULE_MISSING",),
            external=False,
        )
        row["residual"]["pending_acquisition_or_experiment_required"] = True
        row["residual"]["internal_unsolved"] = True
        out = v2.compile_gap_contract(row)
        self.assertEqual(
            out["gap_class"],
            "PENDING_ACQUISITION_OR_EXPERIMENT",
        )
        self.assertEqual(out["basis"]["constructive_internal_blockers"], [])

    def test_pending_acquisition_provider_then_verified_closure(self):
        first = closure(
            status="OPEN",
            evidence=("MISSING_FACT",),
            external=False,
            initial="i0",
            final="f0",
        )
        second = closure(
            status="PASS",
            passed=True,
            initial="i1",
            final="f1",
        )
        provider = lambda contract: {
            "pass": True,
            "frontier_changed": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "c" * 64,
            "acquisition_or_experiment_attempted": True,
            "evidence_trace_sha256": "9" * 64,
        }
        with patch.object(v2.v1, "run", side_effect=[first, second]):
            out = v2.run(repo_root=".", evidence_acquisition_provider=provider)
        self.assertTrue(out["pass"], out)

    def test_constructive_gap_provider_then_verified_closure(self):
        first = closure(
            status="OPEN",
            internal=("ROOT1_GAP",),
            initial="i0",
            final="f0",
        )
        second = closure(
            status="PASS",
            passed=True,
            initial="i1",
            final="f1",
        )
        provider = lambda contract: {
            "pass": True,
            "frontier_changed": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "d" * 64,
            "reuse_or_search_trace_complete": True,
            "new_code_written": False,
            "verifier_generated_or_reused": True,
            "verifier_passed": True,
        }
        with patch.object(v2.v1, "run", side_effect=[first, second]):
            out = v2.run(repo_root=".", capability_synthesis_provider=provider)
        self.assertTrue(out["pass"])
        self.assertEqual(out["status"], "PASS__PROOF_CARRYING_REALITY_CLOSURE_FIXED_POINT")

    def test_provider_false_progress_is_rejected_when_next_frontier_unchanged(self):
        first = closure(
            status="OPEN",
            internal=("ROOT1_GAP",),
            initial="i0",
            final="same",
        )
        second = closure(
            status="OPEN",
            internal=("ROOT1_GAP",),
            initial="same",
            final="same",
        )
        provider = lambda contract: {
            "pass": True,
            "frontier_changed": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "e" * 64,
            "reuse_or_search_trace_complete": True,
            "new_code_written": False,
            "verifier_generated_or_reused": True,
            "verifier_passed": True,
        }
        with patch.object(v2.v1, "run", side_effect=[first, second]):
            out = v2.run(repo_root=".", capability_synthesis_provider=provider)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__PROVIDER_RECEIPT_WITHOUT_OBSERVED_FRONTIER_CHANGE",
        )

    def test_provider_cannot_mutate_verification_authority(self):
        first = closure(status="OPEN", internal=("ROOT1_GAP",))
        provider = lambda contract: {
            "pass": True,
            "frontier_changed": True,
            "verification_authority_mutated": True,
            "receipt_sha256": "f" * 64,
        }
        with patch.object(v2.v1, "run", return_value=first):
            out = v2.run(repo_root=".", capability_synthesis_provider=provider)
        self.assertFalse(out["pass"])
        self.assertTrue(out["internal_unsolved"])
        self.assertEqual(
            out["status"],
            "OPEN__INTERNAL_UNSOLVED__INFRASTRUCTURE_OR_PROVIDER_FAILURE",
        )
        self.assertEqual(
            out["failure"]["stage"],
            "CAPABILITY_SYNTHESIS_PROVIDER",
        )

    def test_new_code_requires_pre_code_search_minimality_and_verifier(self):
        first = closure(status="OPEN", internal=("ROOT1_GAP",))
        provider = lambda contract: {
            "pass": True,
            "frontier_changed": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "8" * 64,
            "reuse_or_search_trace_complete": True,
            "new_code_written": True,
            "pre_code_search_exhausted": False,
            "minimal_missing_transform_only": True,
            "verifier_generated_or_reused": True,
            "verifier_passed": True,
        }
        with patch.object(v2.v1, "run", return_value=first):
            out = v2.run(repo_root=".", capability_synthesis_provider=provider)
        self.assertFalse(out["pass"])
        self.assertTrue(out["internal_unsolved"])
        self.assertIn(
            "PRE_CODE_SEARCH_NOT_EXHAUSTED",
            out["failure"]["reason"],
        )

    def test_v1_exception_is_internal_infrastructure_failure(self):
        with patch.object(
            v2.v1,
            "run",
            side_effect=RuntimeError("runner unavailable"),
        ):
            out = v2.run(repo_root=".")
        self.assertFalse(out["pass"])
        self.assertTrue(out["internal_unsolved"])
        self.assertFalse(out["failure"]["externality_proved"])
        self.assertEqual(out["failure"]["stage"], "V1_CLOSURE_ENGINE")

    def test_provider_exception_is_internal_not_external(self):
        first = closure(status="OPEN", internal=("ROOT1_GAP",))
        def provider(contract):
            raise RuntimeError("transport died")
        with patch.object(v2.v1, "run", return_value=first):
            out = v2.run(repo_root=".", capability_synthesis_provider=provider)
        self.assertFalse(out["pass"])
        self.assertTrue(out["internal_unsolved"])
        self.assertFalse(out["failure"]["externality_proved"])
        self.assertEqual(
            out["failure"]["stage"],
            "CAPABILITY_SYNTHESIS_PROVIDER",
        )

    def test_infrastructure_repair_provider_repairs_then_retries(self):
        solved = closure(
            status="PASS",
            passed=True,
            initial="i1",
            final="f1",
        )
        repair_calls = []
        def repair(request):
            repair_calls.append(request)
            return {
                "pass": True,
                "infrastructure_repaired": True,
                "verification_authority_mutated": False,
                "receipt_sha256": "7" * 64,
            }
        with patch.object(
            v2.v1,
            "run",
            side_effect=[RuntimeError("runner unavailable"), solved],
        ):
            out = v2.run(
                repo_root=".",
                infrastructure_repair_provider=repair,
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(len(repair_calls), 1)
        self.assertEqual(
            out["transcript"][0]["status"],
            "INFRASTRUCTURE_REPAIR_RECEIPT_ACCEPTED__RETRY_CLOSURE_LOOP",
        )

    def test_shared_cause_candidates_collapse_multiple_obligations(self):
        pending = []
        for wid in ("w1", "w2", "w3"):
            pending.append({
                "schema": v2.SEMANTIC_WORK_SCHEMA,
                "work_id": wid,
                "work_digest": wid.ljust(64, "0"),
                "kind": "REPAIR_FAILURE_CLASS",
                "status": "PENDING",
                "payload": {
                    "repair_class": "SAME_ROOT_CAUSE",
                    "boundary_root": "shared.root",
                },
            })
        out = v2.compile_gap_contract(
            closure(status="OPEN", internal=("ROOT1_GAP",)),
            pending_work=pending,
        )
        self.assertGreaterEqual(out["shared_cause_candidate_count"], 1)
        self.assertEqual(
            out["shared_cause_candidates"][0]["terminal_obligations_reached"],
            3,
        )
        self.assertEqual(
            out["required_attempt_order"][0],
            "REUSE_EXISTING_CAPABILITY",
        )
        self.assertTrue(out["search_before_new_code_required"])

    def test_conservative_leverage_uses_probability_lower_bound(self):
        rows = v2.rank_candidates([
            {
                "id": "a",
                "success_probability_interval": [0.5, 0.9],
                "truth_reach_lower_bound": 10,
                "future_reuse_multiplier_lower_bound": 2,
                "critical_path_seconds": 10,
            },
            {
                "id": "b",
                "success_probability_interval": [0.9, 0.95],
                "truth_reach_lower_bound": 5,
                "future_reuse_multiplier_lower_bound": 1,
                "critical_path_seconds": 10,
            },
        ])
        self.assertEqual(rows[0]["id"], "a")
        self.assertAlmostEqual(rows[0]["conservative_leverage_score"], 1.0)


    def test_constructive_contract_preserves_semantic_failure_evidence(self):
        pending = [{
            "schema": v2.SEMANTIC_WORK_SCHEMA,
            "work_id": "w1",
            "work_digest": "1" * 64,
            "kind": "REPAIR_FAILURE_CLASS",
            "status": "PARKED",
            "verification_frontier_sha256": "2" * 64,
            "adapter_frontier_sha256": "3" * 64,
            "verification_authority_sha256": "4" * 64,
            "payload": {
                "required_result": "VERIFIED_REPAIR",
                "repair_class": "ACQUIRE_COMPOSE_OR_INVENT_VERIFIABLE_CAPABILITY",
                "failure_fingerprint": "failure:abc",
                "failure_status": "FAIL",
                "falsified_capability_ids": ["cap.old"],
                "counterexamples": [{"input": "x", "expected": "y"}],
                "retry_capsule_sha256": "5" * 64,
            },
        }]
        out = v2.compile_gap_contract(
            closure(status="OPEN", internal=("ROOT1_GAP",)),
            pending_work=pending,
        )
        self.assertEqual(out["constructive_capability_contract_count"], 1)
        contract = out["constructive_capability_contracts"][0]
        basis = contract["basis"]
        self.assertEqual(basis["failure_fingerprint"], "failure:abc")
        self.assertEqual(basis["counterexamples"][0]["expected"], "y")
        self.assertEqual(basis["retry_capsule_sha256"], "5" * 64)
        self.assertEqual(
            basis["verification_authority_sha256"], "4" * 64
        )
        self.assertFalse(contract["verification_authority_mutation_allowed"])
        self.assertFalse(contract["self_verification_allowed"])

    def test_pending_semantic_work_loads_complete_durable_payload(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            path.write_text(json.dumps({
                "improvement_queue": {
                    "w2": {
                        "kind": "EXPAND_SUCCESS_VERIFICATION_FRONTIER",
                        "status": "PENDING",
                        "observations": 3,
                        "verification_authority_sha256": "a" * 64,
                        "payload": {
                            "observation_id": "obs-1",
                            "required_capability_class": "R3_SUCCESS_ADAPTER_PATCH_AUTHOR",
                            "counterexamples": [{"shape": "novel-wrapper"}],
                            "proof_capsule_sha256": "b" * 64,
                        },
                    }
                }
            }), encoding="utf-8")
            rows = v2._pending_semantic_work(state_path=path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["work_id"], "w2")
        self.assertEqual(
            rows[0]["payload"]["required_capability_class"],
            "R3_SUCCESS_ADAPTER_PATCH_AUTHOR",
        )
        self.assertEqual(
            rows[0]["payload"]["counterexamples"],
            [{"shape": "novel-wrapper"}],
        )
        self.assertEqual(len(rows[0]["work_digest"]), 64)


    def test_decision_sufficient_baseline_is_lossless_and_content_addressed(self):
        gap = v2.compile_gap_contract(
            closure(
                status="OPEN",
                internal=("ROOT1_GAP",),
                evidence=("MISSING_FACT",),
            )
        )
        out = v2.compile_decision_sufficient_contract(gap)
        self.assertTrue(out["pass"])
        self.assertEqual(
            out["reduction_mode"],
            "LOSSLESS_IDENTITY__NO_UNVERIFIED_OMISSION",
        )
        self.assertEqual(out["omitted_evidence"], [])
        self.assertEqual(len(out["source_contract_sha256"]), 64)
        self.assertEqual(len(out["representation_sha256"]), 64)
        kinds = {row["kind"] for row in out["representation"]["policy_changing_requirements"]}
        self.assertIn("INTERNAL_BLOCKER", kinds)
        self.assertIn("EVIDENCE_BLOCKER", kinds)

    def test_minimum_information_contract_deduplicates_and_forbids_broad_default(self):
        gap = v2.compile_gap_contract(
            closure(
                status="OPEN",
                evidence=("MISSING_FACT", "MISSING_FACT", "OTHER_FACT"),
            )
        )
        decision = v2.compile_decision_sufficient_contract(gap)
        out = v2.compile_minimum_information_contract(gap, decision)
        self.assertEqual(out["request_count"], 2)
        self.assertEqual(
            out["proof_precedence"][-1],
            "FULL_EMPIRICAL_EVALUATION_LAST",
        )
        self.assertTrue(all(
            row["broad_acquisition_forbidden_without_minimality_proof"]
            for row in out["requests"]
        ))

    def test_structured_r2_acquisition_survives_minimum_information_compilation(self):
        row = closure(
            status="OPEN__INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
            evidence=("R2_PENDING_ACQUISITION:FINANCE_SEMANTIC_ADEQUACY_TAIL",),
        )
        row["residual"]["pending_acquisition_or_experiment_required"] = True
        row["residual"]["internal_unsolved"] = True
        row["residual"]["r2_acquisition_requests"] = [{
            "schema": "PROJECT_BRAIN_R2_PENDING_ACQUISITION_REQUEST_V1",
            "cell_id": "FINANCE_SEMANTIC_ADEQUACY_TAIL",
            "state": "INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
            "required_action": "ACQUIRE_ONLY_MINIMUM_AUTHENTICATED_DISCRIMINATOR",
            "remaining_boundary": "UNBOUND_SEMANTIC_MANIFEST_OR_EVIDENCE",
            "wake_conditions": [
                "NEW_AUTHENTICATED_OEWN_DECISION_MANIFEST_BINDING_COMPLETE_TERMINAL_SIGNATURES_TO_ALL_RELEASE_RELATIVE_SENSES",
                "NEW_AUTHENTICATED_SENSE_DISCRIMINATOR_OBSERVATION_RECEIPT",
            ],
            "request_kind": "R2_POLICY_CHANGING_EVIDENCE_OR_SCOPE_CERTIFICATE",
            "proof_or_existing_receipt_precedes_new_reality": True,
            "broad_acquisition_forbidden_without_minimality_proof": True,
            "full_benchmark_default": False,
            "source_r2_authority_sha256": "9" * 64,
            "request_sha256": "8" * 64,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }]
        gap = v2.compile_gap_contract(row)
        self.assertEqual(gap["gap_class"], "PENDING_ACQUISITION_OR_EXPERIMENT")
        self.assertEqual(gap["basis"]["r2_acquisition_request_count"], 1)
        decision = v2.compile_decision_sufficient_contract(gap)
        kinds = {
            x["kind"]
            for x in decision["representation"]["policy_changing_requirements"]
        }
        self.assertIn("R2_STRUCTURED_ACQUISITION_REQUEST", kinds)
        out = v2.compile_minimum_information_contract(gap, decision)
        self.assertEqual(out["request_count"], 1)
        self.assertEqual(out["structured_r2_request_count"], 1)
        request = out["requests"][0]
        self.assertEqual(
            request["kind"],
            "R2_STRUCTURED_POLICY_CHANGING_ACQUISITION",
        )
        self.assertEqual(
            request["r2_cell_id"],
            "FINANCE_SEMANTIC_ADEQUACY_TAIL",
        )
        self.assertEqual(
            request["remaining_boundary"],
            "UNBOUND_SEMANTIC_MANIFEST_OR_EVIDENCE",
        )
        self.assertEqual(len(request["wake_conditions"]), 2)
        self.assertFalse(request["full_benchmark_default"])

    def test_evidence_provider_receives_exact_structured_r2_acquisition(self):
        first = closure(
            status="OPEN__INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
            evidence=("R2_PENDING_ACQUISITION:FINANCE_SEMANTIC_ADEQUACY_TAIL",),
            initial="i0",
            final="f0",
        )
        first["residual"]["pending_acquisition_or_experiment_required"] = True
        first["residual"]["internal_unsolved"] = True
        first["residual"]["r2_acquisition_requests"] = [{
            "schema": "PROJECT_BRAIN_R2_PENDING_ACQUISITION_REQUEST_V1",
            "cell_id": "FINANCE_SEMANTIC_ADEQUACY_TAIL",
            "state": "INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
            "required_action": "ACQUIRE_ONLY_MINIMUM_AUTHENTICATED_DISCRIMINATOR",
            "remaining_boundary": "UNBOUND_SEMANTIC_MANIFEST_OR_EVIDENCE",
            "wake_conditions": ["NEW_AUTHENTICATED_SENSE_DISCRIMINATOR_OBSERVATION_RECEIPT"],
            "request_kind": "R2_POLICY_CHANGING_EVIDENCE_OR_SCOPE_CERTIFICATE",
            "proof_or_existing_receipt_precedes_new_reality": True,
            "broad_acquisition_forbidden_without_minimality_proof": True,
            "full_benchmark_default": False,
            "source_r2_authority_sha256": "7" * 64,
            "request_sha256": "6" * 64,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }]
        second = closure(
            status="PASS",
            passed=True,
            initial="i1",
            final="f1",
        )
        seen = {}
        def provider(contract):
            seen.update(contract)
            return {
                "pass": True,
                "frontier_changed": True,
                "verification_authority_mutated": False,
                "receipt_sha256": "5" * 64,
                "acquisition_or_experiment_attempted": True,
                "evidence_trace_sha256": "4" * 64,
            }
        with patch.object(v2.v1, "run", side_effect=[first, second]):
            out = v2.run(repo_root=".", evidence_acquisition_provider=provider)
        self.assertTrue(out["pass"], out)
        minimum = seen["minimum_information_contract"]
        self.assertEqual(minimum["request_count"], 1)
        self.assertEqual(minimum["structured_r2_request_count"], 1)
        request = minimum["requests"][0]
        self.assertEqual(request["r2_cell_id"], "FINANCE_SEMANTIC_ADEQUACY_TAIL")
        self.assertEqual(
            request["wake_conditions"],
            ["NEW_AUTHENTICATED_SENSE_DISCRIMINATOR_OBSERVATION_RECEIPT"],
        )

    def test_synthesis_provider_receives_decision_sufficient_contract(self):
        first = closure(
            status="OPEN",
            internal=("ROOT1_GAP",),
            initial="i0",
            final="f0",
        )
        second = closure(
            status="PASS",
            passed=True,
            initial="i1",
            final="f1",
        )
        seen = {}
        def provider(contract):
            seen.update(contract)
            return {
                "pass": True,
                "frontier_changed": True,
                "verification_authority_mutated": False,
                "receipt_sha256": "7" * 64,
                "reuse_or_search_trace_complete": True,
                "new_code_written": False,
                "verifier_generated_or_reused": True,
                "verifier_passed": True,
            }
        with patch.object(v2.v1, "run", side_effect=[first, second]):
            out = v2.run(repo_root=".", capability_synthesis_provider=provider)
        self.assertTrue(out["pass"])
        self.assertEqual(
            seen["decision_sufficient_contract"]["schema"],
            v2.DECISION_SUFFICIENT_SCHEMA,
        )

    def test_evidence_provider_receives_minimum_information_contract(self):
        first = closure(
            status="OPEN",
            evidence=("MISSING_FACT",),
            initial="i0",
            final="f0",
        )
        first["residual"]["pending_acquisition_or_experiment_required"] = True
        second = closure(
            status="PASS",
            passed=True,
            initial="i1",
            final="f1",
        )
        seen = {}
        def provider(contract):
            seen.update(contract)
            return {
                "pass": True,
                "frontier_changed": True,
                "verification_authority_mutated": False,
                "receipt_sha256": "6" * 64,
                "acquisition_or_experiment_attempted": True,
                "evidence_trace_sha256": "5" * 64,
            }
        with patch.object(v2.v1, "run", side_effect=[first, second]):
            out = v2.run(repo_root=".", evidence_acquisition_provider=provider)
        self.assertTrue(out["pass"])
        self.assertEqual(
            seen["minimum_information_contract"]["schema"],
            v2.MINIMUM_INFORMATION_SCHEMA,
        )
        self.assertEqual(seen["minimum_information_contract"]["request_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
