from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import r3_independent_learning_verifier_v1 as worker
from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime.executable_skill_program_v7 import program_digest
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


def effect_problem() -> dict:
    return {
        "initial_facts": [],
        "target_effects": ["RECEIPT_WRITTEN_AND_VERIFIED"],
        "capabilities": [{
            "id": "write-receipt",
            "requires": [],
            "provides": ["RECEIPT_WRITTEN_AND_VERIFIED"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_effect_tool",
                "pre_verifier_id": "TYPED_ACCEPTANCE_PROGRAM_V1",
                "pre_verifier_payload": {
                    "program": {
                        "schema": "PROJECT_BRAIN_TYPED_ACCEPTANCE_PROGRAM_SPEC_V1",
                        "fields": [
                            {
                                "id": "name",
                                "type": "enum",
                                "dimension": "dimensionless",
                                "source": "candidate",
                            },
                            {
                                "id": "score",
                                "type": "number",
                                "dimension": "score",
                                "source": "candidate",
                            },
                            {
                                "id": "passed",
                                "type": "boolean",
                                "dimension": "dimensionless",
                                "source": "candidate",
                            },
                        ],
                        "accept_when": {
                            "op": "and",
                            "args": [
                                {
                                    "op": "eq",
                                    "left": {"op": "ref", "id": "name"},
                                    "right": {
                                        "op": "const",
                                        "type": "enum",
                                        "dimension": "dimensionless",
                                        "value": "Alice",
                                    },
                                },
                                {
                                    "op": "ge",
                                    "left": {"op": "ref", "id": "score"},
                                    "right": {
                                        "op": "const",
                                        "type": "number",
                                        "dimension": "score",
                                        "value": 0.5,
                                    },
                                },
                                {"op": "ref", "id": "passed"},
                            ],
                        },
                    },
                    "trusted_values": {},
                },
                "executor_id": "H100_VERIFIED_EFFECT_TOOL_REGISTRY_V1",
                "executor_payload": {
                    "tool_id": "JSON_RECEIPT_WRITER_V1",
                    "sandbox_rel": "r3-effect-episode",
                },
            },
        }],
    }


class R3EffectfulLearningReadbackV1Tests(unittest.TestCase):
    def material(self, effect_root: Path):
        problem = effect_problem()
        proposal = {
            "candidate_values": {
                "name": "Alice",
                "score": 0.75,
                "passed": True,
            }
        }
        out = v1.run(
            problem,
            proposal_packets={"write-receipt": [proposal]},
            effect_root=str(effect_root),
        )
        self.assertTrue(out["pass"], out)
        trace = list(out["trace"])
        self.assertEqual(len(trace), 1)
        row = trace[0]
        self.assertTrue(row["effect_outcome_sha256"])
        self.assertEqual(
            row["effect_outcome"]["proposal_sha256"],
            row["proposal_sha256"],
        )

        fact = append_fact(
            init_fact(problem),
            capability=problem["capabilities"][0],
            trace_row=row,
        )
        value = append_value(
            init_value(problem),
            capability=problem["capabilities"][0],
            trace_row=row,
        )
        steps = [{
            "op": "write-receipt",
            "inputs": [],
            "outputs": ["RECEIPT_WRITTEN_AND_VERIFIED"],
        }]
        episode = {
            "episode_id": "effect-episode-1",
            "scope_id": "effect-scope",
            "steps": steps,
            "preconditions": [],
            "postconditions": ["RECEIPT_WRITTEN_AND_VERIFIED"],
            "invalidators": [],
            "program_sha256": program_digest(
                steps=steps,
                preconditions=[],
                postconditions=["RECEIPT_WRITTEN_AND_VERIFIED"],
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
            "effect_root": str(effect_root),
        }
        return problem, episode, trace, request

    def test_effectful_episode_is_promoted_only_after_fresh_readback(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            repo_root = root / "repo"
            effect_root = root / "effects"
            (repo_root / "canonical" / "runtime").mkdir(parents=True)

            problem, episode, trace, request = self.material(effect_root)
            binding = worker.verify_episode_request(
                request,
                repo_root=repo_root,
            )
            self.assertIsInstance(binding, dict)
            auth = authenticate_episode(
                binding,
                problem=problem,
                episode=episode,
                trace=trace,
                fact_capsule_head_hash=request["fact_capsule_head_hash"],
                value_capsule_head_hash=request["value_capsule_head_hash"],
                repo_root=repo_root,
            )
            self.assertTrue(auth["pass"], auth)
            self.assertTrue(auth["effect_outcomes_reverified"])

    def test_effectful_episode_reverification_fails_after_effect_bytes_drift(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            repo_root = root / "repo"
            effect_root = root / "effects"
            (repo_root / "canonical" / "runtime").mkdir(parents=True)

            _, _, _, request = self.material(effect_root)
            target = (
                effect_root
                / "r3-effect-episode"
                / "receipts"
                / "result.json"
            )
            target.write_text('{"tampered":true}', encoding="utf-8")
            binding = worker.verify_episode_request(
                request,
                repo_root=repo_root,
            )
            self.assertIsNone(binding)


if __name__ == "__main__":
    unittest.main(verbosity=2)
