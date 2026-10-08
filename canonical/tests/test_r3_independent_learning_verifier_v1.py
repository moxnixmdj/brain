from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import r3_independent_learning_verifier_v1 as worker
from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
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
    def material(self, *, episode_id: str = "ep-1", scope_id: str = "scope-a"):
        action = {
            "type": "verified_proposal",
            "verifier_id": "EXACT_JSON_V1",
            "verifier_payload": {"expected": {"answer": 7}},
        }
        problem = {
            "task_id": "r3-independent-verifier-test",
            "initial_facts": [],
            "target_effects": ["answer.proved"],
            "capabilities": [{
                "id": "cap.exact",
                "requires": [],
                "provides": ["answer.proved"],
                "result_fields": [],
                "action": action,
            }],
        }
        proposal = {"candidate": {"answer": 7}}
        verdict = v1.BUILTIN_VERIFIERS["EXACT_JSON_V1"](
            action["verifier_payload"],
            proposal,
        )
        self.assertTrue(verdict["pass"], verdict)
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
            "new_verified_facts": ["answer.proved"],
        }]
        fact = append_fact(init_fact(problem), capability=problem["capabilities"][0], trace_row=trace[0])
        value = append_value(init_value(problem), capability=problem["capabilities"][0], trace_row=trace[0])
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

    def test_non_effectful_episode_is_independently_recomputed_and_authenticates(self):
        problem, episode, trace, request = self.material()
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "canonical" / "runtime").mkdir(parents=True)
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

    def test_effectful_episode_is_not_self_replayed_or_self_attested(self):
        _, _, _, request = self.material()
        request["trace"][0]["effect_outcome_sha256"] = "e" * 64
        request["trace"][0]["effect_outcome"] = {"pretend": "effect"}
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "canonical" / "runtime").mkdir(parents=True)
            binding = worker.verify_episode_request(request, repo_root=root)
            self.assertIsNone(binding)

    def test_exact_skill_is_verified_only_from_reauthenticated_source_episodes(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            (root / "canonical" / "runtime").mkdir(parents=True)

            authenticated = []
            for eid, scope in (("ep-1", "scope-a"), ("ep-2", "scope-b")):
                problem, episode, trace, request = self.material(
                    episode_id=eid,
                    scope_id=scope,
                )
                binding = worker.verify_episode_request(request, repo_root=root)
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
                authenticated.append(auth["authenticated_episode"])

            state_path = root / "state.json"
            state_path.write_text(
                json.dumps({
                    "episodes": {
                        "one": authenticated[0],
                        "two": authenticated[1],
                    }
                }),
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
            (root / "canonical" / "runtime").mkdir(parents=True)
            authenticated = []
            for eid, scope in (("ep-1", "scope-a"), ("ep-2", "scope-b")):
                problem, episode, trace, request = self.material(
                    episode_id=eid,
                    scope_id=scope,
                )
                binding = worker.verify_episode_request(request, repo_root=root)
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
                authenticated.append(auth["authenticated_episode"])

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
            self.assertEqual(auth["verified_skill"]["scope_relation"], "PROVEN_SUPERSET")
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


# Keep the effectful readback cases inside the already-wired R3 verifier suite.
from canonical.tests.test_r3_effectful_learning_readback_v1 import (
    R3EffectfulLearningReadbackV1Tests,
)


if __name__ == "__main__":
    unittest.main()
