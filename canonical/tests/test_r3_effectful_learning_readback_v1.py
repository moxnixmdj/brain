from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_independent_learning_verifier_v1 as worker
from canonical.runtime import universal_verified_adaptive_solver_v4 as v4
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.executable_skill_program_v7 import program_digest
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    BINDING_SCHEMA,
    BINDING_VERIFY_SCHEMA,
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


def _canon(value) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _write_doc(root: Path, rel: str, doc: dict) -> dict[str, str]:
    raw = _canon(doc).encode("utf-8")
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return {
        "path": rel,
        "git_blob_sha": git_blob_id(raw, object_format="sha1"),
    }


def effect_problem(repo_root: Path) -> dict:
    provides = ["RECEIPT_WRITTEN_AND_VERIFIED"]
    action = {
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
        "effect_contract": {
            "effects": provides,
            "verifier_success_condition": SUCCESS_CONDITIONS["TYPED_ACCEPTANCE_PROGRAM_V1"],
        },
    }
    cap = {
        "id": "write-receipt",
        "requires": [],
        "provides": provides,
        "cost": 1,
        "result_fields": [],
        "action": action,
    }
    problem = {
        "task_id": "r3-effectful-learning-readback",
        "initial_facts": [],
        "target_effects": provides,
        "capabilities": [cap],
    }

    verifier_id = action["pre_verifier_id"]
    payload = action["pre_verifier_payload"]
    core = {
        "capability_id": cap["id"],
        "task_contract_sha256": v4.task_contract_sha256(problem),
        "requires": [],
        "verifier_id": verifier_id,
        "verifier_payload_sha256": sha256(_canon(payload).encode("utf-8")).hexdigest(),
        "verifier_success_condition": SUCCESS_CONDITIONS[verifier_id],
        "provided_effects": provides,
    }
    receipt = {
        "schema": BINDING_SCHEMA,
        **core,
        "pass": True,
        "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
    }
    receipt_ref = _write_doc(
        repo_root,
        "evidence/write-receipt.effect-semantics.receipt.json",
        receipt,
    )
    verification = {
        "schema": BINDING_VERIFY_SCHEMA,
        **core,
        "subject_git_blob_sha": receipt_ref["git_blob_sha"],
        "pass": True,
        "independent_verified": True,
        "implication_semantics_verified": True,
        "independent_verifier_id": "R3_EFFECT_TEST_INDEPENDENT_SEMANTICS_VERIFIER",
    }
    verification_ref = _write_doc(
        repo_root,
        "evidence/write-receipt.effect-semantics.verification.json",
        verification,
    )
    cap["effect_semantics_binding"] = {
        "receipt": receipt_ref,
        "verification": verification_ref,
    }
    return problem


class R3EffectfulLearningReadbackV1Tests(unittest.TestCase):
    def material(self, repo_root: Path, effect_root: Path):
        problem = effect_problem(repo_root)
        proposal = {
            "candidate_values": {
                "name": "Alice",
                "score": 0.75,
                "passed": True,
            }
        }
        out = v4.run(
            problem,
            proposal_packets={"write-receipt": [proposal]},
            repo_root=repo_root,
            effect_root=str(effect_root),
        )
        self.assertTrue(out["pass"], out)
        trace = list(out["trace"])
        self.assertEqual(len(trace), 1)
        row = trace[0]
        self.assertTrue(row["effect_outcome_sha256"])
        self.assertTrue(row["effect_semantics_authenticated"])
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
            repo_root.mkdir(parents=True)

            problem, episode, trace, request = self.material(repo_root, effect_root)
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

    def test_learning_episode_autonomously_promotes_effectful_success_via_readback(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            repo_root = root / "repo"
            effect_root = root / "effects"
            state_path = root / "state.json"
            repo_root.mkdir(parents=True)
            problem = effect_problem(repo_root)
            proposal = {
                "candidate_values": {
                    "name": "Alice",
                    "score": 0.75,
                    "passed": True,
                }
            }
            out = learning.run_learning_episode(
                problem,
                repo_root=repo_root,
                state_path=state_path,
                proposal_packets={"write-receipt": [proposal]},
                effect_root=str(effect_root),
                episode_id="effect-auto-episode",
                scope_id="effect-auto-scope",
            )
            self.assertTrue(out["pass"], out)
            self.assertTrue(out["solver_output"]["current_episode_verified"], out)
            auth = out["solver_output"]["episode_verification_authentication"]
            self.assertTrue(auth["pass"], auth)
            self.assertTrue(auth["effect_outcomes_reverified"], auth)
            state = learning.load_state(state_path)
            self.assertEqual(len(state["episodes"]), 1, state)
            self.assertFalse(any(
                row.get("kind") == "VERIFY_EPISODE" and row.get("status") == "PENDING"
                for row in state["improvement_queue"].values()
            ), state)

    def test_effectful_episode_reverification_fails_after_effect_bytes_drift(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            repo_root = root / "repo"
            effect_root = root / "effects"
            repo_root.mkdir(parents=True)

            _, _, _, request = self.material(repo_root, effect_root)
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
