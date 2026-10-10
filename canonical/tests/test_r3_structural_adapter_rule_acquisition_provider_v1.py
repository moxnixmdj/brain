from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from canonical.runtime import r3_structural_adapter_rule_acquisition_provider_v1 as provider


class StructuralAdapterRuleAcquisitionProviderTests(unittest.TestCase):
    def _fixture(self):
        td = TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        rules = root / provider.RULES_PATH
        rules.parent.mkdir(parents=True, exist_ok=True)
        rules.write_text(json.dumps({
            "schema": "PROJECT_BRAIN_R3_STRUCTURAL_BOUND_ADAPTER_RULES_V1",
            "version": 1,
            "rules": [],
        }), encoding="utf-8")
        state_path = root / "state.json"
        state_path.write_text("{}", encoding="utf-8")
        wid = "handoff-1"
        blocked = "blocked-1"
        observation_id = "observation-1"
        state = {
            "improvement_queue": {
                wid: {
                    "work_id": wid,
                    "kind": provider.FRONTIER_KIND,
                    "status": "PENDING",
                    "payload": {
                        "blocked_success_work_id": blocked,
                        "observation_id": observation_id,
                    },
                },
                blocked: {
                    "work_id": blocked,
                    "kind": "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE",
                    "status": "PARKED",
                    "frontier_expansion_work_id": wid,
                    "parked_reason": "NO_CURRENT_OWNED_VERIFICATION_PATH",
                },
            },
            "observations": {
                observation_id: {
                    "schema": "PROJECT_BRAIN_R3_SUCCESS_OBSERVATION_V1",
                    "observation_id": observation_id,
                    "surface": "TEST_PROOF_BEARING_SURFACE",
                    "frontier_expansion_work_id": wid,
                    "learning_disposition_reason": (
                        "OWNED_SUCCESS_ADAPTER_RETURNED_NO_CANDIDATE"
                    ),
                },
            },
        }
        request = {
            "kind": provider.FRONTIER_KIND,
            "improvement_work_id": wid,
            "blocked_success_work_id": blocked,
            "observation_id": observation_id,
            "allowed_frontier_change_class": (
                "SUCCESS_ADAPTER_ONLY__VERIFICATION_AUTHORITY_IMMUTABLE"
            ),
            "verification_authority_change_allowed": False,
        }
        return root, state_path, state, request

    def _common_patches(self, state):
        proof = {
            "proof_capsule_sha256": "a" * 64,
            "material": {"shape": "proof"},
        }
        replay = {
            "replay_capsule_sha256": "b" * 64,
            "context": {
                "mode": "generic",
                "problem": {"task_id": "x"},
            },
        }
        context = {
            "pass": True,
            "context_sha256": "sha256:" + "c" * 64,
        }
        reduction = {
            "pass": True,
            "retained_proof_class": "CHECKPOINTED_VERIFIED_EXECUTION",
            "admissible_repair_classes": [
                provider.repair_reducer.ADAPTER,
                provider.repair_reducer.NEW_EVIDENCE,
            ],
            "must_acquire_new_distinguishing_evidence": False,
        }
        return (
            mock.patch.object(provider.learning, "load_state", return_value=state),
            mock.patch.object(
                provider.learning,
                "get_success_proof_context",
                return_value=proof,
            ),
            mock.patch.object(
                provider.learning,
                "get_success_replay_context",
                return_value=replay,
            ),
            mock.patch.object(
                provider.author_context,
                "compile_context",
                return_value=context,
            ),
            mock.patch.object(
                provider.repair_reducer,
                "reduce_author_context",
                return_value=reduction,
            ),
        )

    def test_installs_only_proved_existing_structural_profile(self):
        root, state_path, state, request = self._fixture()
        callable_provider = provider.make_provider(
            repo_root=root,
            state_path=state_path,
        )
        patches = self._common_patches(state)
        with (
            patches[0], patches[1], patches[2], patches[3], patches[4],
            mock.patch.object(provider.structural, "adapt", return_value=None),
            mock.patch.object(
                provider.structural,
                "preflight",
                side_effect=[
                    None,
                    {
                        "candidate_only": True,
                        "promotion_authority": False,
                        "terminal_authority": False,
                        "status": "CANDIDATE_READY",
                    },
                ],
            ),
        ):
            out = callable_provider(request)

        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress_claimed"], out)
        self.assertFalse(out["verification_authority_changed"])
        doc = json.loads((root / provider.RULES_PATH).read_text(encoding="utf-8"))
        self.assertEqual(len(doc["rules"]), 1)
        rule = doc["rules"][0]
        self.assertEqual(rule["surface"], "TEST_PROOF_BEARING_SURFACE")
        self.assertEqual(
            rule["source_schema"],
            "PROJECT_BRAIN_R3_SUCCESS_OBSERVATION_V1",
        )
        self.assertEqual(
            rule["normalization_profile"],
            provider.structural.NORMALIZATION_PROFILES[1],
        )
        self.assertFalse(rule["verification_authority"])
        self.assertFalse(rule["promotion_authority"])
        self.assertFalse(rule["terminal_authority"])

    def test_no_proved_profile_does_not_mutate_frontier(self):
        root, state_path, state, request = self._fixture()
        callable_provider = provider.make_provider(
            repo_root=root,
            state_path=state_path,
        )
        before = (root / provider.RULES_PATH).read_bytes()
        patches = self._common_patches(state)
        with (
            patches[0], patches[1], patches[2], patches[3], patches[4],
            mock.patch.object(provider.structural, "adapt", return_value=None),
            mock.patch.object(provider.structural, "preflight", return_value=None),
        ):
            out = callable_provider(request)

        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["reason"],
            "NO_EXISTING_VERIFIER_PRESERVING_STRUCTURAL_PROFILE_PROVED",
        )
        self.assertEqual(before, (root / provider.RULES_PATH).read_bytes())

    def test_rejects_verification_authority_rewrite_request(self):
        root, state_path, _state, request = self._fixture()
        callable_provider = provider.make_provider(
            repo_root=root,
            state_path=state_path,
        )
        request["verification_authority_change_allowed"] = True
        out = callable_provider(request)
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["reason"],
            "VERIFICATION_AUTHORITY_CHANGE_MUST_BE_FORBIDDEN",
        )

    def test_conflicting_active_rule_fails_closed(self):
        root, state_path, state, request = self._fixture()
        rules_path = root / provider.RULES_PATH
        doc = json.loads(rules_path.read_text(encoding="utf-8"))
        doc["rules"] = [{
            "rule_id": "existing",
            "status": "ACTIVE",
            "surface": "TEST_PROOF_BEARING_SURFACE",
            "source_schema": "PROJECT_BRAIN_R3_SUCCESS_OBSERVATION_V1",
            "verification_kind": provider.bound.VERIFICATION_KIND,
            "normalization_profile": provider.structural.NORMALIZATION_PROFILES[0],
        }]
        rules_path.write_text(json.dumps(doc), encoding="utf-8")
        callable_provider = provider.make_provider(
            repo_root=root,
            state_path=state_path,
        )
        patches = self._common_patches(state)
        with (
            patches[0], patches[1], patches[2], patches[3], patches[4],
            mock.patch.object(provider.structural, "adapt", return_value=None),
            mock.patch.object(
                provider.structural,
                "preflight",
                side_effect=[
                    None,
                    {
                        "candidate_only": True,
                        "promotion_authority": False,
                        "terminal_authority": False,
                        "status": "CANDIDATE_READY",
                    },
                ],
            ),
        ):
            out = callable_provider(request)

        self.assertFalse(out["pass"], out)
        self.assertEqual(out["reason"], "CONFLICTING_STRUCTURAL_RULE_ALREADY_ACTIVE")


if __name__ == "__main__":
    unittest.main()
