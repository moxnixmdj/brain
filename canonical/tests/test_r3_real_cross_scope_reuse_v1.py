from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import live_brain_runtime_v1 as live
from canonical.runtime import r3_independent_learning_verifier_v1 as independent
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime import universal_verified_adaptive_solver_v3 as v3
from canonical.runtime import universal_verified_adaptive_solver_v4 as v4


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical" / "astra_runtime" / "tmp"
CAPABILITY_ID = "cap.exact"
TARGET = "answer.proved"
PREDICATE = learning.VERIFIED_SUPERSET_SCOPE_PREDICATE


def _canon(doc) -> bytes:
    return json.dumps(
        doc,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _write_doc(path: Path, doc) -> dict[str, str]:
    raw = _canon(doc)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "git_blob_sha": git_blob_id(raw, object_format="sha1"),
    }


def _problem(work: Path, *, task_id: str) -> dict:
    action = {
        "type": "verified_proposal",
        "verifier_id": "EXACT_JSON_V1",
        "verifier_payload": {"expected": {"answer": 7}},
        "effect_contract": {
            "effects": [TARGET],
            "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
        },
    }
    cap = {
        "id": CAPABILITY_ID,
        "requires": [],
        "provides": [TARGET],
        "cost": 1,
        "result_fields": [],
        "action": action,
    }
    problem = {
        "task_id": task_id,
        "initial_facts": [],
        "target_effects": [TARGET],
        "capabilities": [cap],
    }
    core = {
        "capability_id": CAPABILITY_ID,
        "task_contract_sha256": v4.task_contract_sha256(problem),
        "requires": [],
        "verifier_id": "EXACT_JSON_V1",
        "verifier_payload_sha256": v1._digest(action["verifier_payload"]),
        "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
        "provided_effects": [TARGET],
    }
    receipt = _write_doc(
        work / "semantics.receipt.json",
        {
            "schema": v3.BINDING_SCHEMA,
            **core,
            "pass": True,
            "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
        },
    )
    verification = _write_doc(
        work / "semantics.verification.json",
        {
            "schema": v3.BINDING_VERIFY_SCHEMA,
            "subject_git_blob_sha": receipt["git_blob_sha"],
            **core,
            "pass": True,
            "independent_verified": True,
            "implication_semantics_verified": True,
            "independent_verifier_id": "R3_REAL_CROSS_SCOPE_SEMANTICS_V1",
        },
    )
    cap["effect_semantics_binding"] = {
        "receipt": receipt,
        "verification": verification,
    }
    return problem


def _providers(state_path: Path, receipt_dir: str):
    return {
        "episode_verification_provider": (
            lambda req: independent.verify_episode_request(
                req,
                repo_root=ROOT,
                receipt_dir=receipt_dir,
            )
        ),
        "skill_verification_provider": (
            lambda req: independent.verify_skill_request(
                req,
                repo_root=ROOT,
                state_path=state_path,
                receipt_dir=receipt_dir,
            )
        ),
    }


class R3RealCrossScopeReuseV1Tests(unittest.TestCase):
    def test_real_non_effectful_skill_generalizes_and_reuses_in_fresh_scope(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=TMP) as td:
            work = Path(td)
            token = work.name.replace("_", "-")
            state_path = work / "SELF_IMPROVEMENT_STATE.json"
            receipt_dir = work.relative_to(ROOT).as_posix() + "/receipts"
            providers = _providers(state_path, receipt_dir)
            def proposer(request, index, prior):
                return {"candidate": {"answer": 7}}

            first = live.run_generic(
                _problem(work / "a", task_id=f"cross-scope-{token}-a"),
                repo_root=ROOT,
                state_path=state_path,
                proposal_provider=proposer,
                episode_id=f"cross-scope-{token}-ep-a",
                scope_id="scope-a",
                learn=True,
                **providers,
            )
            self.assertTrue(first["pass"], first)
            self.assertTrue(
                first["solver_output"]["current_episode_verified"],
                first,
            )
            self.assertFalse(first["reuse_first"], first)

            second = live.run_generic(
                _problem(work / "b", task_id=f"cross-scope-{token}-b"),
                repo_root=ROOT,
                state_path=state_path,
                proposal_provider=proposer,
                episode_id=f"cross-scope-{token}-ep-b",
                scope_id="scope-b",
                learn=True,
                **providers,
            )
            self.assertTrue(second["pass"], second)
            self.assertTrue(
                second["solver_output"]["current_episode_verified"],
                second,
            )
            self.assertFalse(second["reuse_first"], second)

            queued = learning.load_state(state_path)
            pending = [
                row
                for row in queued["improvement_queue"].values()
                if row.get("status") == "PENDING"
            ]
            self.assertTrue(
                any(row.get("kind") == "VERIFY_SKILL_CANDIDATE" for row in pending),
                pending,
            )

            exact = learning.advance_verification_queue(
                state_path=state_path,
                repo_root=ROOT,
                skill_verification_provider=providers["skill_verification_provider"],
                max_actions=1,
            )
            self.assertEqual(exact["completed"], 1, exact)
            exact_state = learning.load_state(state_path)
            active = [
                (sid, row)
                for sid, row in exact_state["skills"].items()
                if row.get("active") is True
            ]
            self.assertEqual(len(active), 1, active)
            skill_id, exact_record = active[0]
            exact_skill = exact_record["skill"]
            self.assertEqual(exact_skill["scope_relation"], "EXACT")
            self.assertEqual(
                set(exact_skill["source_scopes"]),
                {"scope-a", "scope-b"},
            )
            self.assertTrue(
                any(
                    row.get("kind") == "SEEK_VERIFIED_SCOPE_GENERALIZATION"
                    and row.get("status") == "PENDING"
                    for row in exact_state["improvement_queue"].values()
                ),
                exact_state["improvement_queue"],
            )

            generalized = learning.advance_verification_queue(
                state_path=state_path,
                repo_root=ROOT,
                skill_verification_provider=providers["skill_verification_provider"],
                max_actions=1,
            )
            self.assertEqual(generalized["completed"], 1, generalized)
            self.assertEqual(
                generalized["results"][0]["scope_relation"],
                "PROVEN_SUPERSET",
                generalized,
            )
            self.assertEqual(
                generalized["results"][0]["scope_predicate"],
                PREDICATE,
                generalized,
            )

            generalized_state = learning.load_state(state_path)
            record = generalized_state["skills"][skill_id]
            self.assertTrue(record["active"], record)
            skill = record["skill"]
            self.assertEqual(skill["scope_relation"], "PROVEN_SUPERSET")
            self.assertEqual(skill["scope_predicate"], PREDICATE)
            self.assertEqual(set(skill["source_scopes"]), {"scope-a", "scope-b"})

            third = live.run_generic(
                _problem(work / "c", task_id=f"cross-scope-{token}-c"),
                repo_root=ROOT,
                state_path=state_path,
                proposal_provider=proposer,
                episode_id=f"cross-scope-{token}-ep-c",
                scope_id="scope-c",
                learn=True,
                **providers,
            )
            self.assertTrue(third["pass"], third)
            self.assertTrue(third["reuse_first"], third)
            self.assertEqual(third["reused_skill_id"], skill_id, third)
            self.assertFalse(third["fallback_used"], third)
            self.assertTrue(
                third["solver_output"]["current_episode_verified"],
                third,
            )
            self.assertTrue(third["reuse_attempt"]["pass"], third)
            self.assertFalse(
                third["reuse_attempt"]["effect_may_have_occurred"],
                third,
            )

            final = learning.load_state(state_path)
            reuse = final["reuse"][skill_id]
            self.assertEqual(reuse["attempts"], 1, reuse)
            self.assertEqual(reuse["successes"], 1, reuse)
            self.assertEqual(reuse["pre_effect_failures"], 0, reuse)
            self.assertEqual(reuse["effectful_failures"], 0, reuse)


if __name__ == "__main__":
    unittest.main(verbosity=2)
