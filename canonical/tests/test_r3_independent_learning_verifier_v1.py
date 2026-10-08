from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from canonical.runtime import r3_independent_learning_verifier_v1 as worker
from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime import universal_verified_adaptive_solver_v3 as v3
from canonical.runtime import universal_verified_adaptive_solver_v4 as v4
from canonical.runtime import universal_verified_adaptive_solver_v12 as v12
from canonical.runtime import universal_bound_capability_carrier_v1 as carrier
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.executable_skill_program_v7 import induce_candidate, program_digest
from canonical.runtime.executable_skill_verification_authenticator_v1 import (
    authenticate_and_verify as authenticate_skill,
)
from canonical.runtime.universal_solver_episode_verification_authenticator_v1 import (
    authenticate as authenticate_episode,
)
from canonical.runtime.universal_solver_state_capsule_v1 import (
    append_verified_transition as append_fact,
    initialize as init_fact,
)
from canonical.runtime.universal_solver_value_state_v1 import (
    append_verified_transition as append_value,
    initialize as init_value,
)


class R3IndependentLearningVerifierV1Tests(unittest.TestCase):
    def _write_doc(self, root: Path, rel: str, doc: dict) -> dict[str, str]:
        raw = json.dumps(
            doc,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        return {
            "path": rel,
            "git_blob_sha": worker.git_blob_id(raw, object_format="sha1"),
        }

    def material(
        self,
        root: Path,
        *,
        episode_id: str = "ep-1",
        scope_id: str = "scope-a",
    ):
        action = {
            "type": "verified_proposal",
            "verifier_id": "EXACT_JSON_V1",
            "verifier_payload": {"expected": {"answer": 7}},
            "effect_contract": {
                "effects": ["answer.proved"],
                "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
            },
        }
        cap = {
            "id": "cap.exact",
            "requires": [],
            "provides": ["answer.proved"],
            "result_fields": [],
            "action": action,
        }
        problem = {
            "task_id": "r3-independent-verifier-test",
            "initial_facts": [],
            "target_effects": ["answer.proved"],
            "capabilities": [cap],
        }

        semantic_core = {
            "capability_id": "cap.exact",
            "task_contract_sha256": v4.task_contract_sha256(problem),
            "requires": [],
            "verifier_id": "EXACT_JSON_V1",
            "verifier_payload_sha256": v4._digest(action["verifier_payload"]),
            "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
            "provided_effects": ["answer.proved"],
        }
        receipt_doc = {
            "schema": v3.BINDING_SCHEMA,
            **semantic_core,
            "pass": True,
            "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
        }
        receipt_ref = self._write_doc(
            root,
            "evidence/cap-exact.receipt.json",
            receipt_doc,
        )
        verification_doc = {
            "schema": v3.BINDING_VERIFY_SCHEMA,
            **semantic_core,
            "subject_git_blob_sha": receipt_ref["git_blob_sha"],
            "pass": True,
            "independent_verified": True,
            "implication_semantics_verified": True,
            "independent_verifier_id": "TEST_INDEPENDENT_SEMANTICS_VERIFIER",
        }
        verification_ref = self._write_doc(
            root,
            "evidence/cap-exact.verification.json",
            verification_doc,
        )
        cap["effect_semantics_binding"] = {
            "receipt": receipt_ref,
            "verification": verification_ref,
        }

        proposal = {"candidate": {"answer": 7}}
        verdict = v1.BUILTIN_VERIFIERS["EXACT_JSON_V1"](
            action["verifier_payload"],
            proposal,
        )
        self.assertTrue(verdict["pass"], verdict)

        initial_value = init_value(problem)
        trace = [{
            "cycle": 0,
            "capability_id": "cap.exact",
            "verifier_id": "EXACT_JSON_V1",
            "action_contract_sha256": v1._digest(action),
            "packet_index": 0,
            "proposal_sha256": v1._digest(proposal),
            "proposal_source": "TEST",
            "proposal_request_sha256": None,
            "proposal_packet_sha256": None,
            "proposal_source_id": None,
            "verdict_status": verdict["status"],
            "proof_digest": verdict["proof_digest"],
            "accepted_proposal": proposal,
            "action_type": action["type"],
            "verified_output": verdict["verified_output"],
            "effect_outcome": None,
            "effect_outcome_sha256": None,
            "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
            "semantic_authentication_schema": None,
            "effect_semantics_receipt": receipt_ref,
            "effect_semantics_verification": verification_ref,
            "effect_semantics_authenticated": True,
            "independent_effect_semantics_verifier_id": (
                "TEST_INDEPENDENT_SEMANTICS_VERIFIER"
            ),
            "new_verified_facts": ["answer.proved"],
            "resolved_action": action,
            "value_capsule_head_before": initial_value["head_hash"],
        }]
        fact = append_fact(
            init_fact(problem),
            capability=cap,
            trace_row=trace[0],
        )
        value = append_value(
            initial_value,
            capability=cap,
            trace_row=trace[0],
        )
        trace[0]["value_capsule_head_after"] = value["head_hash"]

        steps = [{"op": "cap.exact", "inputs": [], "outputs": ["answer.proved"]}]
        episode = {
            "episode_id": episode_id,
            "scope_id": scope_id,
            "steps": steps,
            "preconditions": [],
            "postconditions": ["answer.proved"],
            "invalidators": [],
            "program_sha256": program_digest(
                steps=steps,
                preconditions=[],
                postconditions=["answer.proved"],
                invalidators=[],
            ),
        }
        request = {
            "kind": "EPISODE_VERIFICATION",
            "problem": problem,
            "episode": episode,
            "trace": trace,
            "fact_capsule_head_hash": fact["head_hash"],
            "value_capsule_head_hash": value["head_hash"],
        }
        return problem, episode, trace, request

    def _bound_outer_problem(self):
        inner = {
            "initial_facts": [],
            "target_effects": ["inner.done"],
            "capabilities": [{
                "id": "inner",
                "requires": [],
                "provides": ["inner.done"],
                "cost": 1,
                "result_fields": [],
                "action": {
                    "type": "invoke_capability",
                    "args": {"capability_id": "verified.test.capability"},
                    "expect": {
                        "type": "field_equals",
                        "field": "verified",
                        "value": True,
                    },
                },
            }],
            "finish_summary": "INNER_DONE",
        }
        action = {
            "type": "verified_policy",
            "verifier_id": "BOUND_CAPABILITY_EXECUTION_V1",
            "verifier_payload": {"problem": inner},
            "effect_contract": {
                "effects": ["GOAL"],
                "verifier_success_condition": SUCCESS_CONDITIONS[
                    "BOUND_CAPABILITY_EXECUTION_V1"
                ],
            },
        }
        return {
            "task_id": "r3-bound-carrier-learning",
            "initial_facts": [],
            "target_effects": ["GOAL"],
            "capabilities": [{
                "id": "macro",
                "requires": [],
                "provides": ["GOAL"],
                "cost": 1,
                "result_fields": [],
                "action": action,
                "bound_capability_carrier": True,
            }],
        }

    def _bind_bound_outer_semantics(self, root: Path, problem: dict) -> None:
        cap = problem["capabilities"][0]
        action = cap["action"]
        expected = {
            "capability_id": "macro",
            "task_contract_sha256": v3.task_contract_sha256(problem),
            "requires": [],
            "verifier_id": "BOUND_CAPABILITY_EXECUTION_V1",
            "verifier_payload_sha256": v1._digest(action["verifier_payload"]),
            "verifier_success_condition": SUCCESS_CONDITIONS[
                "BOUND_CAPABILITY_EXECUTION_V1"
            ],
            "provided_effects": ["GOAL"],
        }
        receipt = self._write_doc(
            root,
            "evidence/bound-macro.receipt.json",
            {
                "schema": v3.BINDING_SCHEMA,
                **expected,
                "pass": True,
                "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
            },
        )
        verification = self._write_doc(
            root,
            "evidence/bound-macro.verification.json",
            {
                "schema": v3.BINDING_VERIFY_SCHEMA,
                "subject_git_blob_sha": receipt["git_blob_sha"],
                **expected,
                "pass": True,
                "independent_verified": True,
                "implication_semantics_verified": True,
                "independent_verifier_id": "TEST_BOUND_CARRIER_SEMANTICS_VERIFIER",
            },
        )
        cap["effect_semantics_binding"] = {
            "receipt": receipt,
            "verification": verification,
        }

    def _authenticate_material(self, root: Path, *, episode_id: str, scope_id: str):
        problem, episode, trace, request = self.material(
            root,
            episode_id=episode_id,
            scope_id=scope_id,
        )
        binding = worker.verify_episode_request(request, repo_root=root)
        self.assertIsInstance(binding, dict)
        auth = authenticate_episode(
            binding,
            problem=problem,
            episode=episode,
            trace=trace,
            fact_capsule_head_hash=request["fact_capsule_head_hash"],
            value_capsule_head_hash=request["value_capsule_head_hash"],
            repo_root=root,
        )
        self.assertTrue(auth["pass"], auth)
        return auth["authenticated_episode"]

    def test_non_effectful_episode_reauthenticates_semantics_and_authenticates(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            problem, episode, trace, request = self.material(root)
            binding = worker.verify_episode_request(request, repo_root=root)
            self.assertIsInstance(binding, dict)
            auth = authenticate_episode(
                binding,
                problem=problem,
                episode=episode,
                trace=trace,
                fact_capsule_head_hash=request["fact_capsule_head_hash"],
                value_capsule_head_hash=request["value_capsule_head_hash"],
                repo_root=root,
            )
            self.assertTrue(auth["pass"], auth)
            self.assertEqual(
                auth["independent_verifier_id"],
                worker.INDEPENDENT_VERIFIER_ID,
            )
            self.assertFalse(auth["effect_outcomes_reverified"])

    def test_semantics_receipt_substitution_is_rejected(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _, _, _, request = self.material(root)
            request["trace"][0]["effect_semantics_receipt"] = {
                "path": "evidence/not-the-bound-receipt.json",
                "git_blob_sha": "0" * 40,
            }
            self.assertIsNone(worker.verify_episode_request(request, repo_root=root))

    def test_nonempty_route_invalidators_fail_closed(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _, episode, _, request = self.material(root)
            episode["invalidators"] = ["route_falsified:cap.hidden"]
            episode["program_sha256"] = program_digest(
                steps=episode["steps"],
                preconditions=episode["preconditions"],
                postconditions=episode["postconditions"],
                invalidators=episode["invalidators"],
            )
            self.assertIsNone(worker.verify_episode_request(request, repo_root=root))

    def test_effectful_episode_is_not_self_replayed_or_self_attested(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _, _, _, request = self.material(root)
            request["trace"][0]["effect_outcome_sha256"] = "e" * 64
            request["trace"][0]["effect_outcome"] = {"pretend": "effect"}
            self.assertIsNone(worker.verify_episode_request(request, repo_root=root))

    def test_bound_carrier_effectful_episode_is_reverified_without_effect_replay(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            problem = self._bound_outer_problem()
            self._bind_bound_outer_semantics(root, problem)
            with mock.patch.object(
                carrier.astra_runtime,
                "_invoke_bound_capability",
                return_value={"verified": True},
            ) as invoke:
                out = v12.run(
                    problem,
                    repo_root=root,
                    episode_id="bound-ep",
                    scope_id="bound-scope",
                )

            self.assertTrue(out["pass"], out)
            self.assertEqual(out["status"], "SOLVED__EPISODE_VERIFICATION_REQUIRED")
            self.assertEqual(invoke.call_count, 1)
            self.assertTrue(out["trace"][0]["effect_outcome_sha256"])
            request = {
                "kind": "EPISODE_VERIFICATION",
                "problem": problem,
                "episode": out["current_episode"],
                "trace": out["trace"],
                "fact_capsule_head_hash": out["state_capsule_head_hash"],
                "value_capsule_head_hash": out["value_capsule_head_hash"],
            }
            binding = worker.verify_episode_request(request, repo_root=root)
            self.assertIsInstance(binding, dict)
            self.assertEqual(invoke.call_count, 1, "verification must not replay the effect")
            auth = authenticate_episode(
                binding,
                problem=problem,
                episode=out["current_episode"],
                trace=out["trace"],
                fact_capsule_head_hash=out["state_capsule_head_hash"],
                value_capsule_head_hash=out["value_capsule_head_hash"],
                repo_root=root,
            )
            self.assertTrue(auth["pass"], auth)
            self.assertTrue(auth["effect_outcomes_reverified"])

    def test_bound_carrier_effect_outcome_tamper_is_rejected(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            problem = self._bound_outer_problem()
            self._bind_bound_outer_semantics(root, problem)
            with mock.patch.object(
                carrier.astra_runtime,
                "_invoke_bound_capability",
                return_value={"verified": True},
            ):
                out = v12.run(
                    problem,
                    repo_root=root,
                    episode_id="bound-ep-tamper",
                    scope_id="bound-scope",
                )
            self.assertTrue(out["pass"], out)
            trace = json.loads(json.dumps(out["trace"]))
            trace[0]["effect_outcome"]["executed_nonfinish_action_count"] = 999
            request = {
                "kind": "EPISODE_VERIFICATION",
                "problem": problem,
                "episode": out["current_episode"],
                "trace": trace,
                "fact_capsule_head_hash": out["state_capsule_head_hash"],
                "value_capsule_head_hash": out["value_capsule_head_hash"],
            }
            self.assertIsNone(worker.verify_episode_request(request, repo_root=root))

    def test_exact_skill_is_verified_only_from_reauthenticated_source_episodes(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            authenticated = [
                self._authenticate_material(root, episode_id="ep-1", scope_id="scope-a"),
                self._authenticate_material(root, episode_id="ep-2", scope_id="scope-b"),
            ]
            state_path = root / "state.json"
            state_path.write_text(
                json.dumps({"episodes": {"one": authenticated[0], "two": authenticated[1]}}),
                encoding="utf-8",
            )
            candidate = induce_candidate(authenticated)
            binding = worker.verify_skill_request(
                {"kind": "SKILL_VERIFICATION", "candidate": candidate},
                repo_root=root,
                state_path=state_path,
            )
            self.assertIsInstance(binding, dict)
            auth = authenticate_skill(candidate, binding, repo_root=root)
            self.assertTrue(auth["pass"], auth)
            self.assertEqual(auth["verified_skill"]["scope_relation"], "EXACT")
            self.assertTrue(auth["verified_skill"]["reuse_authorized"])

    def test_non_effectful_structural_superset_is_independently_proved(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            authenticated = [
                self._authenticate_material(root, episode_id="ep-1", scope_id="scope-a"),
                self._authenticate_material(root, episode_id="ep-2", scope_id="scope-b"),
            ]
            state_path = root / "state.json"
            state_path.write_text(
                json.dumps({"episodes": {"one": authenticated[0], "two": authenticated[1]}}),
                encoding="utf-8",
            )
            candidate = induce_candidate(authenticated)
            binding = worker.verify_skill_request(
                {
                    "kind": "SKILL_SCOPE_GENERALIZATION_VERIFICATION",
                    "candidate": candidate,
                    "requested_scope_relation": "PROVEN_SUPERSET",
                    "requested_scope_predicate": "STRUCTURAL_MATCH_V1",
                    "supported_scope_predicates": ["STRUCTURAL_MATCH_V1"],
                },
                repo_root=root,
                state_path=state_path,
            )
            self.assertIsInstance(binding, dict)
            auth = authenticate_skill(candidate, binding, repo_root=root)
            self.assertTrue(auth["pass"], auth)
            self.assertEqual(
                auth["verified_skill"]["scope_relation"],
                "PROVEN_SUPERSET",
            )
            self.assertEqual(
                auth["verified_skill"]["scope_predicate"],
                "STRUCTURAL_MATCH_V1",
            )

    def test_scope_worker_rejects_unadmitted_generalization_predicate(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            state_path = root / "state.json"
            state_path.write_text(json.dumps({"episodes": {}}), encoding="utf-8")
            out = worker.verify_skill_request(
                {
                    "kind": "SKILL_SCOPE_GENERALIZATION_VERIFICATION",
                    "candidate": {"candidate_only": True},
                    "requested_scope_relation": "PROVEN_SUPERSET",
                    "requested_scope_predicate": "ANYTHING_MATCHES",
                    "supported_scope_predicates": ["STRUCTURAL_MATCH_V1"],
                },
                repo_root=root,
                state_path=state_path,
            )
            self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main()
