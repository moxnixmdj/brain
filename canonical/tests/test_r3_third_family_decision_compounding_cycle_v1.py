from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import live_brain_runtime_v1 as live
from canonical.runtime import live_integrated_brain_v1 as bound_brain
from canonical.runtime import r3_improvement_queue_driver_v1 as driver
from canonical.runtime import r3_independent_learning_verifier_v1 as independent
from canonical.runtime import r3_structural_bound_success_adapter_v1 as structural
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    BINDING_SCHEMA,
    BINDING_VERIFY_SCHEMA,
    task_contract_sha256,
)
from canonical.runtime import universal_verified_adaptive_solver_v1 as solver_v1


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical" / "astra_runtime" / "tmp"
RULES = ROOT / structural.RULES_PATH
CAPABILITY_ID = "decision.synthesis.typed.stdlib"
TARGET = "decision.synthesis.typed"
PRECONDITION = "structured.decision_evidence.available"


def _write_json(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _decision_problem(decision_id: str, winner: str) -> dict:
    loser = "B" if winner == "A" else "A"
    return {
        "schema": "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
        "decision_id": decision_id,
        "question": "Select the better supported alternative.",
        "alternatives": [
            {"id": "A", "label": "Alternative A"},
            {"id": "B", "label": "Alternative B"},
        ],
        "constraints": [],
        "evidence": [
            {
                "id": f"{decision_id}-support-{winner}",
                "alternative": winner,
                "relation": "SUPPORTS",
                "confidence": 0.95,
                "strength": 1.0,
                "independence_group": "primary",
                "claim": f"{winner} has strong independent support.",
                "provenance": [{"source": "regression-fixture", "ref": f"{decision_id}:1"}],
            },
            {
                "id": f"{decision_id}-support-{loser}",
                "alternative": loser,
                "relation": "SUPPORTS",
                "confidence": 0.20,
                "strength": 1.0,
                "independence_group": "secondary",
                "claim": f"{loser} has weak support.",
                "provenance": [{"source": "regression-fixture", "ref": f"{decision_id}:2"}],
            },
        ],
        "policy": {
            "minimum_support_ratio": 0.60,
            "maximum_conflict_ratio": 0.50,
            "minimum_independent_support_groups": 1,
            "minimum_net_margin": 0.10,
        },
    }


class R3ThirdFamilyDecisionCompoundingCycleV1Tests(unittest.TestCase):
    def setUp(self):
        self._rules = RULES.read_bytes()
        _write_json(
            RULES,
            {
                "schema": "PROJECT_BRAIN_R3_STRUCTURAL_BOUND_ADAPTER_RULES_V1",
                "version": 1,
                "rules": [],
            },
        )
        TMP.mkdir(parents=True, exist_ok=True)
        self._checkpoint_paths: list[Path] = []
        self._receipt_root = ROOT / independent.DEFAULT_RECEIPT_DIR
        self._receipt_root.mkdir(parents=True, exist_ok=True)
        self._receipt_files_before = set(self._receipt_root.glob("*.json"))

    def tearDown(self):
        RULES.write_bytes(self._rules)
        for path in self._checkpoint_paths:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        for path in set(self._receipt_root.glob("*.json")) - self._receipt_files_before:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def _bound_task(self, work: Path, *, task_id: str, winner: str):
        work.mkdir(parents=True, exist_ok=True)
        input_path = work / "decision_input.json"
        output_path = work / "decision_output.json"
        _write_json(input_path, _decision_problem(task_id, winner))
        out = bound_brain.run(
            {
                "task_id": task_id,
                "initial_facts": [PRECONDITION],
                "target_effects": [TARGET],
                "allowed_capability_ids": [CAPABILITY_ID],
                "capability_inputs": {
                    CAPABILITY_ID: {
                        "input_path": input_path.relative_to(ROOT).as_posix(),
                        "output_path": output_path.relative_to(ROOT).as_posix(),
                    }
                },
            }
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_plan"], [CAPABILITY_ID])
        self.assertTrue(output_path.is_file())
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["selected_alternative"], winner, payload)
        checkpoint = out.get("controller_checkpoint") or {}
        cp = checkpoint.get("path")
        if cp:
            self._checkpoint_paths.append(ROOT / cp)
        return out, input_path, output_path

    @staticmethod
    def _record_wrapped_success(out, *, state_path: Path):
        return learning.record_success_observation(
            out,
            surface="REAL_BOUND_DECISION_WRAPPED_SUCCESS_REGRESSION",
            state_path=state_path,
            replay_context={
                "mode": "generic",
                "problem": {
                    "task_id": out["task_id"],
                    "initial_facts": [PRECONDITION],
                },
            },
        )

    @staticmethod
    def _providers(root: Path, state_path: Path, receipt_dir: str):
        return {
            "episode_verification_provider": lambda req: independent.verify_episode_request(
                req, repo_root=root, receipt_dir=receipt_dir
            ),
            "skill_verification_provider": lambda req: independent.verify_skill_request(
                req, repo_root=root, state_path=state_path, receipt_dir=receipt_dir
            ),
        }

    @staticmethod
    def _save_semantics_pair(root: Path, base_rel: str, problem):
        cap = problem["capabilities"][0]
        action = cap["action"]
        expected = {
            "capability_id": cap["id"],
            "task_contract_sha256": task_contract_sha256(problem),
            "requires": list(cap["requires"]),
            "verifier_id": "BOUND_CAPABILITY_EXECUTION_V1",
            "verifier_payload_sha256": solver_v1._digest(action["verifier_payload"]),
            "verifier_success_condition": SUCCESS_CONDITIONS[
                "BOUND_CAPABILITY_EXECUTION_V1"
            ],
            "provided_effects": list(cap["provides"]),
        }
        receipt_doc = {
            "schema": BINDING_SCHEMA,
            **expected,
            "pass": True,
            "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
        }
        receipt_rel = base_rel + "/receipt.json"
        receipt_raw = json.dumps(
            receipt_doc,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
        (root / receipt_rel).parent.mkdir(parents=True, exist_ok=True)
        (root / receipt_rel).write_bytes(receipt_raw)
        receipt_ref = {
            "path": receipt_rel,
            "git_blob_sha": git_blob_id(receipt_raw, object_format="sha1"),
        }
        verification_doc = {
            "schema": BINDING_VERIFY_SCHEMA,
            "subject_git_blob_sha": receipt_ref["git_blob_sha"],
            **expected,
            "pass": True,
            "independent_verified": True,
            "implication_semantics_verified": True,
            "independent_verifier_id": "r3-decision-third-family-regression-semantics",
        }
        verify_rel = base_rel + "/verification.json"
        verify_raw = json.dumps(
            verification_doc,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
        (root / verify_rel).write_bytes(verify_raw)
        verify_ref = {
            "path": verify_rel,
            "git_blob_sha": git_blob_id(verify_raw, object_format="sha1"),
        }
        problem["capabilities"][0]["effect_semantics_binding"] = {
            "receipt": receipt_ref,
            "verification": verify_ref,
        }

    def test_real_decision_acquire_reopen_promote_reuse_and_pareto_replace(self):
        with TemporaryDirectory(dir=TMP) as td:
            work = Path(td)
            token = work.name.replace("_", "-")
            state_path = work / "SELF_IMPROVEMENT_STATE.json"
            receipt_dir = work.relative_to(ROOT).as_posix() + "/receipts"
            providers = self._providers(ROOT, state_path, receipt_dir)

            first, _, _ = self._bound_task(
                work / "first",
                task_id=f"r3-decision-{token}-1",
                winner="A",
            )
            first_obs = self._record_wrapped_success(first, state_path=state_path)
            self.assertTrue(first_obs["proof_available"], first_obs)
            first_proof = learning.get_success_proof_context(
                first_obs["observation_id"], state_path=state_path
            )
            self.assertEqual(
                first_proof["material"]["verified_initial_facts"],
                [PRECONDITION],
            )

            parked = driver.advance_once(state_path=state_path, repo_root=ROOT)
            self.assertEqual(
                parked["status"],
                "IMPROVEMENT_PARKED__CURRENT_OWNED_VERIFICATION_FRONTIER_INCOMPLETE",
                parked,
            )
            acquired = driver.advance_once(state_path=state_path, repo_root=ROOT)
            self.assertTrue(acquired["pass"], acquired)
            self.assertEqual(
                acquired["status"],
                "IMPROVEMENT_ADVANCED__SUCCESS_ADAPTER_FRONTIER_EXPANDED_AND_SUCCESS_REOPENED",
                acquired,
            )
            self.assertTrue(acquired["verification_authority_unchanged"], acquired)

            verified_first = driver.advance_once(state_path=state_path, repo_root=ROOT)
            self.assertEqual(
                verified_first["status"],
                "IMPROVEMENT_ADVANCED__SUCCESS_BECAME_VERIFIED_EPISODE",
                verified_first,
            )

            second, _, _ = self._bound_task(
                work / "second",
                task_id=f"r3-decision-{token}-2",
                winner="B",
            )
            self._record_wrapped_success(second, state_path=state_path)
            verified_second = driver.advance_once(state_path=state_path, repo_root=ROOT)
            self.assertEqual(
                verified_second["status"],
                "IMPROVEMENT_ADVANCED__SUCCESS_BECAME_VERIFIED_EPISODE",
                verified_second,
            )
            promoted = driver.advance_once(state_path=state_path, repo_root=ROOT)
            self.assertEqual(
                promoted["status"],
                "IMPROVEMENT_ADVANCED__SKILL_VERIFIED_AND_PARETO_ADJUDICATED",
                promoted,
            )

            state = learning.load_state(state_path)
            active = [
                (sid, rec)
                for sid, rec in state["skills"].items()
                if rec.get("active") is True
            ]
            self.assertEqual(len(active), 1, active)
            two_skill_id, two_record = active[0]
            self.assertEqual(two_record["pareto_metrics"]["reliability"], 2)
            source_scope = two_record["skill"]["source_scopes"][0]

            third_dir = work / "third"
            third_dir.mkdir(parents=True, exist_ok=True)
            input_path = third_dir / "decision_input.json"
            output_path = third_dir / "decision_output.json"
            _write_json(
                input_path,
                _decision_problem(f"r3-decision-{token}-3-inner", "A"),
            )
            inner = {
                "initial_facts": [],
                "target_effects": ["inner.done"],
                "capabilities": [
                    {
                        "id": "inner.decision",
                        "requires": [],
                        "provides": ["inner.done"],
                        "cost": 1,
                        "result_fields": [],
                        "action": {
                            "type": "invoke_capability",
                            "args": {
                                "capability_id": CAPABILITY_ID,
                                "input_path": input_path.relative_to(ROOT).as_posix(),
                                "output_path": output_path.relative_to(ROOT).as_posix(),
                            },
                            "expect": {
                                "type": "field_equals",
                                "field": "output_verified",
                                "value": True,
                            },
                        },
                    }
                ],
                "finish_summary": "INNER_DECISION_DONE",
            }
            action = {
                "type": "verified_policy",
                "verifier_id": "BOUND_CAPABILITY_EXECUTION_V1",
                "verifier_payload": {"problem": inner},
                "effect_contract": {
                    "effects": [TARGET],
                    "verifier_success_condition": SUCCESS_CONDITIONS[
                        "BOUND_CAPABILITY_EXECUTION_V1"
                    ],
                },
            }
            problem = {
                "task_id": f"r3-decision-{token}-3",
                "initial_facts": [PRECONDITION],
                "target_effects": [TARGET],
                "capabilities": [
                    {
                        "id": CAPABILITY_ID,
                        "requires": [PRECONDITION],
                        "provides": [TARGET],
                        "cost": 1,
                        "result_fields": [],
                        "action": action,
                        "bound_capability_carrier": True,
                    }
                ],
            }
            self._save_semantics_pair(
                ROOT,
                work.relative_to(ROOT).as_posix() + "/semantics",
                problem,
            )
            reused = live.run_generic(
                problem,
                repo_root=ROOT,
                state_path=state_path,
                episode_id=f"r3-decision-{token}-3",
                scope_id=source_scope,
                learn=True,
                **providers,
            )
            self.assertTrue(reused["pass"], reused)
            self.assertTrue(reused["reuse_first"], reused)
            self.assertEqual(reused["reused_skill_id"], two_skill_id, reused)
            self.assertFalse(reused["fallback_used"], reused)
            self.assertTrue(output_path.is_file())
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["selected_alternative"], "A", payload)
            self.assertTrue(reused["solver_output"]["current_episode_verified"], reused)

            post = driver.advance_once(state_path=state_path, repo_root=ROOT)
            self.assertEqual(
                post["status"],
                "IMPROVEMENT_ADVANCED__SKILL_VERIFIED_AND_PARETO_ADJUDICATED",
                post,
            )
            final = learning.load_state(state_path)
            active = [
                (sid, rec)
                for sid, rec in final["skills"].items()
                if rec.get("active") is True
            ]
            self.assertEqual(len(active), 1, active)
            three_skill_id, three_record = active[0]
            self.assertNotEqual(three_skill_id, two_skill_id)
            self.assertEqual(three_record["pareto_metrics"]["reliability"], 3)
            self.assertEqual(len(three_record["skill"]["source_episode_ids"]), 3)
            self.assertFalse(final["skills"][two_skill_id]["active"])
            self.assertEqual(final["skills"][two_skill_id]["dominated_by"], three_skill_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
