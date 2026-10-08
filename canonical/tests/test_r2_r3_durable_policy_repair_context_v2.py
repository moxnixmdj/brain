from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import live_brain_runtime_v1 as brain


POLICY_PREFIX = "BOUND_CAPABILITY_POLICY::"


def failure(capability_id: str) -> dict:
    policy_id = POLICY_PREFIX + capability_id
    return {
        "pass": False,
        "status": "OPEN__POSITIVE_POLICY_ADEQUACY_COVERAGE_REQUIRED",
        "next_required_edge": "AUTHENTICATED_POSITIVE_POLICY_ADEQUACY_COVERAGE",
        "next_policy_request": {
            "loop_status": "OPEN__POSITIVE_POLICY_ADEQUACY_COVERAGE_REQUIRED",
            "required_artifact": "POSITIVE_POLICY_ADEQUACY_COVERAGE",
            "selected_policy_id": policy_id,
            "search_context": {
                "authenticated_policy_ids": [],
                "rejected_policy_candidates": [
                    {
                        "policy_id": policy_id,
                        "reason": "ADEQUACY_BINDING_MISSING",
                        "raw_secret": "must_not_persist",
                    }
                ],
                "certified_common_policies": [],
                "uncovered_models": [
                    {
                        "model_id": "m0",
                        "valuation": {"PRIVATE_FACT": True},
                    }
                ],
                "surviving_model_count": 1,
            },
        },
    }


def retry_context() -> dict:
    return {
        "mode": "decision",
        "request": {"task_id": "t", "goal": "audit tests"},
        "known_absent_invalidators": [],
        "learn": True,
    }


class R2R3DurablePolicyRepairContextV2Tests(unittest.TestCase):
    def test_failure_observation_persists_compact_frontier_in_retry_capsule(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            observed = brain._observe_runtime_outcome(
                failure("python.tests.audit.unittest"),
                state_path=state_path,
                learn=True,
                retry_context=retry_context(),
            )
            self.assertIsNotNone(observed)
            retry = learning.get_failure_retry_context(
                observed["diagnosis"]["failure_fingerprint"],
                state_path=state_path,
                retry_capsule_sha256=observed["retry_capsule_sha256"],
            )
            repair_context = retry["context"]["policy_repair_context"]
            self.assertEqual(
                repair_context["grounded_bound_policy_candidates"],
                [
                    {
                        "policy_id": (
                            "BOUND_CAPABILITY_POLICY::python.tests.audit.unittest"
                        ),
                        "capability_id": "python.tests.audit.unittest",
                    }
                ],
            )
            rendered = repr(repair_context)
            self.assertNotIn("PRIVATE_FACT", rendered)
            self.assertNotIn("raw_secret", rendered)
            self.assertNotIn("valuation", rendered)

    def test_distinct_policy_frontiers_get_distinct_retry_work(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            a = brain._observe_runtime_outcome(
                failure("python.tests.audit.unittest"),
                state_path=state_path,
                learn=True,
                retry_context=retry_context(),
            )
            b = brain._observe_runtime_outcome(
                failure("auto.pypi.msgpack"),
                state_path=state_path,
                learn=True,
                retry_context=retry_context(),
            )
            self.assertEqual(
                a["diagnosis"]["failure_fingerprint"],
                b["diagnosis"]["failure_fingerprint"],
            )
            self.assertNotEqual(
                a["retry_capsule_sha256"],
                b["retry_capsule_sha256"],
            )
            state = learning.load_state(state_path)
            queued = [
                row
                for row in state["improvement_queue"].values()
                if row.get("kind") == "REPAIR_FAILURE_CLASS"
            ]
            self.assertEqual(len(queued), 2)

    def test_deferred_repair_recovers_grounded_frontier_from_retry_capsule(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            observed = brain._observe_runtime_outcome(
                failure("python.tests.audit.unittest"),
                state_path=state_path,
                learn=True,
                retry_context=retry_context(),
            )
            synthesized = {
                "pass": False,
                "status": "REPAIR_ARCHITECTURE_UNRESOLVED",
                "failure_fingerprint": observed["diagnosis"]["failure_fingerprint"],
                "required_repair_effect": "repair.policy_adequacy_cover.available",
                "causal_synthesis": {"classification": "NEW_PRIMITIVE_REQUIRED"},
            }
            with patch.object(
                brain,
                "synthesize_failure_repair",
                return_value=synthesized,
            ), patch.object(
                brain,
                "_v12_run",
                return_value={"pass": False, "status": "TEST_STOP"},
            ) as solver, patch.object(
                brain,
                "_observe_runtime_outcome",
                return_value=None,
            ):
                out = brain.execute_failure_repair_cycle(
                    {
                        "failure_fingerprint": (
                            observed["diagnosis"]["failure_fingerprint"]
                        ),
                        "retry_capsule_sha256": observed["retry_capsule_sha256"],
                        "components": [],
                        "initial_facts": [],
                        "learn": False,
                    },
                    state_path=state_path,
                    capability_expander=lambda *_args, **_kwargs: None,
                )
            self.assertFalse(out["pass"])
            problem = solver.call_args.args[0]
            self.assertEqual(
                problem["repair_context"]["grounded_bound_policy_candidates"][0][
                    "capability_id"
                ],
                "python.tests.audit.unittest",
            )
            self.assertEqual(len(problem["target_effects"]), 1)
            self.assertTrue(
                problem["target_effects"][0].startswith(
                    "repair.policy_adequacy.prove::"
                )
            )

    def test_conflicting_direct_and_persisted_repair_context_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            observed = brain._observe_runtime_outcome(
                failure("python.tests.audit.unittest"),
                state_path=state_path,
                learn=True,
                retry_context=retry_context(),
            )
            synthesized = {
                "pass": False,
                "status": "REPAIR_ARCHITECTURE_UNRESOLVED",
                "required_repair_effect": "repair.policy_adequacy_cover.available",
                "causal_synthesis": {"classification": "NEW_PRIMITIVE_REQUIRED"},
            }
            with patch.object(
                brain,
                "synthesize_failure_repair",
                return_value=synthesized,
            ):
                out = brain.execute_failure_repair_cycle(
                    {
                        "failure_fingerprint": (
                            observed["diagnosis"]["failure_fingerprint"]
                        ),
                        "retry_capsule_sha256": observed["retry_capsule_sha256"],
                        "components": [],
                        "repair_context": {
                            "schema": "PROJECT_BRAIN_R2_POLICY_REPAIR_CONTEXT_V1",
                            "grounded_bound_policy_candidates": [
                                {
                                    "policy_id": (
                                        "BOUND_CAPABILITY_POLICY::auto.pypi.msgpack"
                                    ),
                                    "capability_id": "auto.pypi.msgpack",
                                }
                            ],
                        },
                    },
                    state_path=state_path,
                    capability_expander=lambda *_args, **_kwargs: None,
                )
            self.assertFalse(out["pass"])
            self.assertEqual(
                out["reason"],
                "REPAIR_CONTEXT_CONFLICT_WITH_RETRY_CAPSULE",
            )

    def test_original_replay_strips_repair_only_context(self):
        ctx = {
            **retry_context(),
            "policy_repair_context": {
                "schema": "PROJECT_BRAIN_R2_POLICY_REPAIR_CONTEXT_V1",
                "grounded_bound_policy_candidates": [],
            },
        }
        with patch.object(
            brain,
            "run",
            return_value={"pass": False, "status": "TEST_REPLAY"},
        ) as replay:
            brain._replay_retry_context(
                ctx,
                repo_root=brain.ROOT,
                information_provider=None,
                proposal_provider=None,
                capability_expander=None,
            )
        replayed = replay.call_args.args[0]
        self.assertNotIn("policy_repair_context", replayed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
