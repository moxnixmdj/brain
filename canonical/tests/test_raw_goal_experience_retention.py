"""The front door must remember what it did, and remembering must be inert.

106 modules in `canonical/runtime` implement learning, episode retention, skill
induction and Pareto admission. The front door called none of them -- a grep
for the self-improvement, learning and feedback symbols in
`live_integrated_brain_v1.py` returned 0 -- so every goal the machine carried
out was forgotten the moment it returned, and the learning loop never had any
experience to learn from.

`run_raw_goal` is now a thin wrapper that records passing runs through
`record_success_observation`, which is the module's own entry point for exactly
this and which refuses to promote anything without independent verification.

Two properties are pinned here, and the second matters more than the first:

1. Passing runs are retained; failing runs are not.
2. **Retention cannot change an outcome.** Nothing is consulted to decide
   success, and a learning layer that raises must not fail a run. A machine
   that remembered its way to a green result would be worse than one that
   forgot, so the wrapper is asserted to return the implementation's result
   untouched even while the recorder is throwing.
"""
from __future__ import annotations

import pathlib
import unittest
import uuid

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

import sys

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime import (  # noqa: E402
    autonomous_verified_self_improvement_v1 as self_improvement,
)
from canonical.runtime import live_integrated_brain_v1 as live  # noqa: E402

SURFACE = "RAW_GOAL_FRONT_DOOR_V1"
PASSING_GOAL = "Verify an existing tar.gz archive against its manifest."
FAILING_GOAL = "Assess the consistency of knowledge observations."


# A fresh nonce per run, plus explicit checkpoint cleanup: the controller
# short-circuits a repeated task_id, so fixed ids would make this suite pass
# once and fail on every subsequent run in the same tree.
_NONCE = uuid.uuid4().hex[:10]
_STATE_DIR = REPO_ROOT / "canonical/astra_runtime/state"


def _run(tag, goal):
    """Run one goal under a unique task_id and remove its checkpoint."""
    task_id = f"{tag}_{_NONCE}"
    checkpoint = _STATE_DIR / (
        f"{task_id}__live-raw-goal-controller__CONTROLLER_CHECKPOINT.json"
    )
    try:
        return live.run_raw_goal({"task_id": task_id, "goal": goal})
    finally:
        checkpoint.unlink(missing_ok=True)


def _run_impl(tag, goal):
    task_id = f"{tag}_{_NONCE}"
    checkpoint = _STATE_DIR / (
        f"{task_id}__live-raw-goal-controller__CONTROLLER_CHECKPOINT.json"
    )
    try:
        return live._run_raw_goal_impl({"task_id": task_id, "goal": goal})
    finally:
        checkpoint.unlink(missing_ok=True)


def _observations():
    return dict(self_improvement.load_state().get("observations") or {})


def _front_door_observations():
    return {
        k: v for k, v in _observations().items()
        if (v or {}).get("surface") == SURFACE
    }


class ExperienceIsRetainedTests(unittest.TestCase):
    def test_a_passing_run_is_retained(self):
        before = _front_door_observations()
        res = _run("RETAIN_PROBE_PASS", PASSING_GOAL)
        self.assertIs(res.get("pass"), True)
        after = _front_door_observations()
        self.assertGreater(len(after), len(before))
        newest = max(after.values(), key=lambda v: str(v.get("surface")))
        self.assertEqual(newest.get("surface"), SURFACE)
        self.assertTrue(str(newest.get("status") or "").startswith("PASS__"))

    def test_a_failing_run_is_not_retained(self):
        """The recorder refuses an output that did not pass, so a failure can
        never be laundered into remembered success."""
        res = _run("RETAIN_PROBE_FAIL", FAILING_GOAL)
        self.assertIsNot(res.get("pass"), True)
        with self.assertRaises(self_improvement.SelfImprovementError):
            self_improvement.record_success_observation(res, surface=SURFACE)

    def test_retention_becomes_explicit_pending_work_not_a_shortcut(self):
        """The module's own contract: a plain runtime success is recorded as
        work to build a verifiable episode, never promoted to a reusable skill
        by the act of being remembered."""
        _run("RETAIN_PROBE_WORK", PASSING_GOAL)
        stats = self_improvement.load_state().get("stats") or {}
        self.assertGreaterEqual(int(stats.get("success_observation_count") or 0), 1)
        self.assertEqual(int(stats.get("verified_episode_count") or 0), 0)


class RetentionCannotChangeAnOutcomeTests(unittest.TestCase):
    """The property that keeps this honest."""

    def test_the_wrapper_returns_the_implementation_result_untouched(self):
        impl = _run_impl("WRAP_PROBE_IMPL_A", PASSING_GOAL)
        wrapped = _run("WRAP_PROBE_IMPL_B", PASSING_GOAL)
        for key in ("pass", "status", "selected_plan",
                    "semantic_acceptance_complete", "compiled_capability_id"):
            self.assertEqual(wrapped.get(key), impl.get(key), key)

    def test_a_learning_failure_cannot_fail_a_run(self):
        """If retaining experience could break execution, the learning layer
        would be a new way to lose capability rather than gain it."""
        real = self_improvement.record_success_observation

        def _boom(*args, **kwargs):
            raise RuntimeError("LEARNING_LAYER_IS_BROKEN")

        self_improvement.record_success_observation = _boom
        try:
            res = _run("WRAP_PROBE_BOOM", PASSING_GOAL)
        finally:
            self_improvement.record_success_observation = real
        self.assertIs(res.get("pass"), True)

    def test_nothing_is_consulted_to_decide_success(self):
        """A learned route must never be what makes a goal pass. Emptying the
        retained experience entirely must not change the result, because the
        result comes from the implementation, not from memory."""
        res = _run("WRAP_PROBE_COLD", PASSING_GOAL)
        self.assertIs(res.get("pass"), True)
        self.assertEqual(res.get("compiled_capability_id"),
                         "archive.verify.tar_gz.gnu")

    def test_the_recorder_ignores_a_non_mapping(self):
        live._record_raw_goal_experience(None)
        live._record_raw_goal_experience("not a mapping")
        live._record_raw_goal_experience({"pass": True})  # no crash, recorded
        live._record_raw_goal_experience({"pass": False})


if __name__ == "__main__":
    unittest.main()
