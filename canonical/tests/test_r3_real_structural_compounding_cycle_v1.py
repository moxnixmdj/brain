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
CAPABILITY_ID = "archive.tar_gz.create_from_manifest"
TARGET = CAPABILITY_ID


def _write_json(path: Path, doc) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class R3RealStructuralCompoundingCycleV1Tests(unittest.TestCase):
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

    def _bound_task(self, work: Path, *, task_id: str, payload: str):
        work.mkdir(parents=True, exist_ok=True)
        source = work / "source.txt"
        source.write_text(payload + "\n", encoding="utf-8")
        manifest = work / "manifest.json"
        _write_json(
            manifest,
            {
                "schema": "R3_REAL_COMPOUND_REGRESSION_FIXTURE_V1",
                "records": [
                    {
                        "verification_paths": [
                            source.relative_to(ROOT).as_posix()
                        ]
                    }
                ],
            },
        )
        output = work / "bundle.tar.gz"
        out = bound_brain.run(
            {
                "task_id": task_id,
                "initial_facts": ["manifest.json.available"],
                "target_effects": [TARGET],
                "allowed_capability_ids": [CAPABILITY_ID],
                "capability_inputs": {
                    CAPABILITY_ID: {
                        "manifest_path": manifest.relative_to(ROOT).as_posix(),
                        "output_path": output.relative_to(ROOT).as_posix(),
                    }
                },
            }
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__REAL_TASK_PLANNED_EXECUTED_AND_REVERIFIED",
            out,
        )
        self.assertEqual(out["selected_plan"], [CAPABILITY_ID])
        self.assertTrue(output.is_file())
        checkpoint = out.get("controller_checkpoint") or {}
        cp = checkpoint.get("path")
        if cp:
            self._checkpoint_paths.append(ROOT / cp)
        return out, manifest, output

    @staticmethod
    def _record_wrapped_success(out, *, state_path: Path):
        return learning.record_success_observation(
            out,
            surface="REAL_BOUND_WRAPPED_SUCCESS_REGRESSION",
            state_path=state_path,
            replay_context={
                "mode": "generic",
                "problem": {
                    "task_id": out["task_id"],
                    "initial_facts": ["manifest.json.available"],
                    # target_effects deliberately omitted: the acquired adapter
                    # may recover only the exact proved target from the
                    # authenticated success proof capsule.
                },
            },
        )

    @staticmethod
    def _providers(root: Path, state_path: Path, receipt_dir: str):
        return {
            "episode_verification_provider": lambda req: independent.verify_episode_request(
                req,
                repo_root=root,
                receipt_dir=receipt_dir,
            ),
            "skill_verification_provider": lambda req: independent.verify_skill_request(
                req,
                repo_root=root,
                state_path=state_path,
                receipt_dir=receipt_dir,
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
            "verifier_payload_sha256": solver_v1._digest(
                action["verifier_payload"]
            ),
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
            "independent_verifier_id": (
                "r3-real-structural-compounding-regression-semantics"
            ),
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

    def test_real_acquire_reopen_promote_reuse_and_pareto_replace(self):
        with TemporaryDirectory(dir=TMP) as td:
            work = Path(td)
            token = work.name.replace("_", "-")
            state_path = work / "SELF_IMPROVEMENT_STATE.json"
            receipt_dir = work.relative_to(ROOT).as_posix() + "/receipts"
            providers = self._providers(ROOT, state_path, receipt_dir)

            first, _, _ = self._bound_task(
                work / "first",
                task_id=f"r3-regression-{token}-1",
                payload="first independently retained episode",
            )
            first_obs = self._record_wrapped_success(
                first,
                state_path=state_path,
            )
            self.assertTrue(first_obs["proof_available"], first_obs)

            parked = driver.advance_once(
                state_path=state_path,
                repo_root=ROOT,
            )
            self.assertEqual(
                parked["status"],
                "IMPROVEMENT_PARKED__CURRENT_OWNED_VERIFICATION_FRONTIER_INCOMPLETE",
                parked,
            )

            authority_before = driver._owned_success_verification_authority_sha256(
                repo_root=ROOT
            )
            acquired = driver.advance_once(
                state_path=state_path,
                repo_root=ROOT,
            )
            self.assertTrue(acquired["pass"], acquired)
            self.assertTrue(acquired["verification_authority_unchanged"], acquired)
            self.assertEqual(
                acquired["status"],
                "IMPROVEMENT_ADVANCED__SUCCESS_ADAPTER_FRONTIER_EXPANDED_AND_SUCCESS_REOPENED",
                acquired,
            )
            self.assertEqual(
                authority_before,
                driver._owned_success_verification_authority_sha256(
                    repo_root=ROOT
                ),
            )
            rules = json.loads(RULES.read_text(encoding="utf-8"))
            active_rules = [
                row for row in rules["rules"] if row.get("status") == "ACTIVE"
            ]
            self.assertEqual(len(active_rules), 1, active_rules)
            self.assertEqual(
                active_rules[0]["normalization_profile"],
                structural.PROFILE_PROOF_TARGETS,
            )

            verified_first = driver.advance_once(
                state_path=state_path,
                repo_root=ROOT,
            )
            self.assertEqual(
                verified_first["status"],
                "IMPROVEMENT_ADVANCED__SUCCESS_BECAME_VERIFIED_EPISODE",
                verified_first,
            )

            second, _, _ = self._bound_task(
                work / "second",
                task_id=f"r3-regression-{token}-2",
                payload="second independently retained episode",
            )
            self._record_wrapped_success(second, state_path=state_path)

            verified_second = driver.advance_once(
                state_path=state_path,
                repo_root=ROOT,
            )
            self.assertEqual(
                verified_second["status"],
                "IMPROVEMENT_ADVANCED__SUCCESS_BECAME_VERIFIED_EPISODE",
                verified_second,
            )
            promoted = driver.advance_once(
                state_path=state_path,
                repo_root=ROOT,
            )
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
            two_episode_skill_id, two_episode_record = active[0]
            self.assertEqual(
                two_episode_record["pareto_metrics"]["reliability"],
                2,
            )
            source_scope = two_episode_record["skill"]["source_scopes"][0]

            third_dir = work / "third"
            third_dir.mkdir(parents=True, exist_ok=True)
            source = third_dir / "source.txt"
            source.write_text(
                "third fresh task must reuse promoted skill\n",
                encoding="utf-8",
            )
            manifest = third_dir / "manifest.json"
            _write_json(
                manifest,
                {
                    "schema": "R3_REAL_COMPOUND_REGRESSION_FIXTURE_V1",
                    "records": [
                        {
                            "verification_paths": [
                                source.relative_to(ROOT).as_posix()
                            ]
                        }
                    ],
                },
            )
            output = third_dir / "bundle.tar.gz"
            inner = {
                "initial_facts": [],
                "target_effects": ["inner.done"],
                "capabilities": [
                    {
                        "id": "inner.archive",
                        "requires": [],
                        "provides": ["inner.done"],
                        "cost": 1,
                        "result_fields": [],
                        "action": {
                            "type": "invoke_capability",
                            "args": {
                                "capability_id": CAPABILITY_ID,
                                "manifest_path": manifest.relative_to(
                                    ROOT
                                ).as_posix(),
                                "output_path": output.relative_to(
                                    ROOT
                                ).as_posix(),
                            },
                            "expect": {
                                "type": "field_equals",
                                "field": "output_verified",
                                "value": True,
                            },
                        },
                    }
                ],
                "finish_summary": "INNER_ARCHIVE_DONE",
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
                "task_id": f"r3-regression-{token}-3",
                "initial_facts": ["manifest.json.available"],
                "target_effects": [TARGET],
                "capabilities": [
                    {
                        "id": CAPABILITY_ID,
                        "requires": ["manifest.json.available"],
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
                episode_id=f"r3-regression-{token}-3",
                scope_id=source_scope,
                learn=True,
                **providers,
            )
            self.assertTrue(reused["pass"], reused)
            self.assertTrue(reused["reuse_first"], reused)
            self.assertEqual(
                reused["reused_skill_id"],
                two_episode_skill_id,
                reused,
            )
            self.assertFalse(reused["fallback_used"], reused)
            self.assertTrue(output.is_file())
            self.assertTrue(
                reused["solver_output"]["current_episode_verified"],
                reused,
            )
            self.assertTrue(reused["reuse_attempt"]["pass"], reused)
            self.assertTrue(
                reused["reuse_attempt"]["effect_may_have_occurred"],
                reused,
            )

            post_reuse = driver.advance_once(
                state_path=state_path,
                repo_root=ROOT,
            )
            self.assertEqual(
                post_reuse["status"],
                "IMPROVEMENT_ADVANCED__SKILL_VERIFIED_AND_PARETO_ADJUDICATED",
                post_reuse,
            )
            final = learning.load_state(state_path)
            active = [
                (sid, rec)
                for sid, rec in final["skills"].items()
                if rec.get("active") is True
            ]
            self.assertEqual(len(active), 1, active)
            three_episode_skill_id, three_episode_record = active[0]
            self.assertNotEqual(
                three_episode_skill_id,
                two_episode_skill_id,
            )
            self.assertEqual(
                three_episode_record["pareto_metrics"]["reliability"],
                3,
            )
            self.assertEqual(
                len(
                    three_episode_record["skill"]["source_episode_ids"]
                ),
                3,
            )
            self.assertTrue(
                three_episode_record["skill"]["reuse_authorized"]
            )
            old = final["skills"][two_episode_skill_id]
            self.assertFalse(old["active"])
            self.assertEqual(
                old["dominated_by"],
                three_episode_skill_id,
            )
            self.assertEqual(
                final["reuse"][two_episode_skill_id],
                {
                    "attempts": 1,
                    "successes": 1,
                    "pre_effect_failures": 0,
                    "effectful_failures": 0,
                },
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
