"""A retained success must be re-inspectable, replayable and reachable.

Three defects kept the Brain's own learning loop from ever consuming what the
front door achieved, and each was silent:

1. `archive.tar_gz.create_from_manifest` had no independent re-inspector, so
   the trace verifier refused it with `NO_INDEPENDENT_REINSPECTION_FOR`, and no
   goal whose work was that capability could ever be accepted.
2. The compound return path reported no `selected_plan`, so
   `_make_success_proof_capsule` returned None and a passing multi-clause goal
   was retained with no proof material at all.
3. The retained replay context had the wrong shape, so
   `get_success_replay_context` raised `SUCCESS_OBSERVATION_NOT_REPLAYABLE`.

Together these made `r3_raw_success_adapter_v1` unreachable: it requires an
accepted run whose `selected_plan` is exactly the create capability, but
acceptance required the verify capability alongside it. Its precondition was
unsatisfiable by any real run, so it was dead code.

The tests here pin the re-inspection itself (including tamper controls), the
self-identifying acceptance record, and end-to-end reachability of the adapter.
"""
from __future__ import annotations

import hashlib
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
from canonical.runtime import r3_raw_success_adapter_v1 as raw_adapter  # noqa: E402
from canonical.runtime import raw_goal_trace_acceptance_v1 as trace_acc  # noqa: E402
from canonical.runtime.raw_goal_archive_acceptance_v1 import (  # noqa: E402
    CAPABILITY as ARCHIVE_CAPABILITY,
)

CREATE_GOAL = "Create a tar.gz archive from a manifest."

# The one shape the archive acceptance grammar admits. Its manifest and the
# evidence file it references are both tracked, so this does not depend on
# anything a previous run happened to leave behind.
_ARCHIVE_MANIFEST = "canonical/astra_runtime/tmp/ARCHIVE_VERIFY_MANIFEST.json"


def _grammar_goal(output_rel):
    return (
        f"Create a tar.gz archive from the manifest {_ARCHIVE_MANIFEST}, "
        f"including all its verification_paths files, and save it to "
        f"{output_rel}."
    )
COMPOUND_GOAL = (
    "Create a tar.gz archive from a manifest and verify the archive "
    "against that manifest."
)
_NONCE = uuid.uuid4().hex[:10]
_STATE_DIR = REPO_ROOT / "canonical/astra_runtime/state"


def _run(tag, goal):
    """Run one goal under a unique task_id and remove its checkpoint.

    A repeated task_id is short-circuited by the controller, so fixed ids would
    make this suite pass once and fail on every later run in the same tree.
    """
    task_id = f"{tag}_{_NONCE}"
    checkpoint = _STATE_DIR / (
        f"{task_id}__live-raw-goal-controller__CONTROLLER_CHECKPOINT.json"
    )
    try:
        return live.run_raw_goal({"task_id": task_id, "goal": goal})
    finally:
        checkpoint.unlink(missing_ok=True)


def _run_keeping_checkpoint(tag, goal):
    """Run one goal and keep its checkpoint, returning a cleanup callable.

    The R3 adapter re-opens the controller checkpoint from disk to bind the
    episode to real evidence, so a test that adapts a retained success must not
    delete that file first. Cleanup is the caller's job.
    """
    task_id = f"{tag}_{_NONCE}"
    checkpoint = _STATE_DIR / (
        f"{task_id}__live-raw-goal-controller__CONTROLLER_CHECKPOINT.json"
    )
    res = live.run_raw_goal({"task_id": task_id, "goal": goal})
    return res, checkpoint


def _reset_learning_state():
    """Start from no retained experience.

    Observation ids are content hashes, so two runs of the same goal collide on
    one id and the first run's checkpoint path is what gets retained. A test
    that needs a live checkpoint must therefore own the whole state.
    """
    pathlib.Path(self_improvement.DEFAULT_STATE_PATH).unlink(missing_ok=True)


def _create_row(res):
    """The executed trace row for the create capability."""
    trace = (res.get("controller_execution") or {}).get("trace") or []
    for row in trace:
        result = row.get("result") if isinstance(row, dict) else None
        if isinstance(result, dict) and result.get("capability_id") == ARCHIVE_CAPABILITY:
            return (row.get("plan") or {}).get("args") or {}, result
    return None, None


class CreateCapabilityIsIndependentlyReinspectableTests(unittest.TestCase):
    def setUp(self):
        self.res = _run("REINSPECT", CREATE_GOAL)
        self.args, self.result = _create_row(self.res)
        self.assertIsNotNone(self.result, "the create step did not execute")

    def test_the_capability_now_has_an_inspector(self):
        self.assertIn(ARCHIVE_CAPABILITY, trace_acc.INSPECTORS)

    def test_a_real_produced_archive_passes_reinspection(self):
        ok, reason, evidence = trace_acc.INSPECTORS[ARCHIVE_CAPABILITY](
            self.args, self.result, REPO_ROOT
        )
        self.assertTrue(ok, reason)
        self.assertGreaterEqual(evidence.get("members_byte_compared_to_source", 0), 1)

    def test_tampering_with_the_archive_is_refused(self):
        """The point of re-inspection: rewritten bytes must not pass."""
        path = REPO_ROOT / self.result["output_path"]
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"tampered")
            ok, reason, _ = trace_acc.INSPECTORS[ARCHIVE_CAPABILITY](
                self.args, self.result, REPO_ROOT
            )
        finally:
            path.write_bytes(original)
        self.assertFalse(ok)
        self.assertEqual(reason, "ARCHIVE_SHA256_MISMATCH")

    def test_a_missing_archive_is_refused(self):
        path = REPO_ROOT / self.result["output_path"]
        original = path.read_bytes()
        try:
            path.unlink()
            ok, reason, _ = trace_acc.INSPECTORS[ARCHIVE_CAPABILITY](
                self.args, self.result, REPO_ROOT
            )
        finally:
            path.write_bytes(original)
        self.assertFalse(ok)
        self.assertEqual(reason, "ARCHIVE_ABSENT_FROM_DISK")

    def test_a_claimed_member_absent_from_disk_is_refused(self):
        """The archive must match reality, not just the producer's own digests."""
        forged = dict(self.result)
        forged["members"] = list(self.result["members"]) + ["canonical/NOT_THERE.json"]
        forged["member_count"] = len(forged["members"])
        ok, reason, _ = trace_acc.INSPECTORS[ARCHIVE_CAPABILITY](
            self.args, forged, REPO_ROOT
        )
        self.assertFalse(ok)
        self.assertIn(reason, {
            "ARCHIVE_MEMBER_SET_MISMATCH", "ARCHIVE_SOURCE_ABSENT_FROM_DISK"})

    def test_a_non_tar_gz_output_is_refused(self):
        path = REPO_ROOT / self.result["output_path"]
        original = path.read_bytes()
        payload = b"not an archive at all"
        forged = dict(self.result)
        forged["output_sha256"] = hashlib.sha256(payload).hexdigest()
        forged["output_bytes"] = len(payload)
        try:
            path.write_bytes(payload)
            ok, reason, _ = trace_acc.INSPECTORS[ARCHIVE_CAPABILITY](
                self.args, forged, REPO_ROOT
            )
        finally:
            path.write_bytes(original)
        self.assertFalse(ok)
        self.assertEqual(reason, "ARCHIVE_NOT_A_READABLE_GZIP_TAR")


class AcceptedRunIsSelfIdentifyingTests(unittest.TestCase):
    def test_the_acceptance_names_the_goal_and_contract_it_judged(self):
        res = _run("SELFID", CREATE_GOAL)
        self.assertIs(res.get("semantic_acceptance_complete"), True)
        acc = res.get("raw_goal_acceptance") or {}
        goal = res.get("raw_goal") or CREATE_GOAL
        self.assertEqual(
            acc.get("goal_sha256"), hashlib.sha256(goal.encode("utf-8")).hexdigest())
        self.assertEqual(
            acc.get("task_contract_sha256"), res.get("raw_task_contract_sha256"))
        self.assertEqual(acc.get("goal_sha256"), res.get("raw_goal_sha256"))


class CompoundRunsRetainProofMaterialTests(unittest.TestCase):
    def test_a_multi_clause_success_reports_the_capabilities_that_ran(self):
        res = _run("COMPOUND", COMPOUND_GOAL)
        self.assertIs(res.get("pass"), True)
        selected = res.get("selected_plan")
        self.assertIsInstance(selected, list)
        self.assertIn(ARCHIVE_CAPABILITY, selected)
        self.assertGreater(len(selected), 1)

    def test_the_retained_observation_carries_proof_material(self):
        """Without `selected_plan` the proof capsule was None, so a passing
        multi-clause goal could never be re-inspected or learned from."""
        _run("PROOFMAT", COMPOUND_GOAL)
        state = self_improvement.load_state()
        observations = state.get("observations") or {}
        self.assertTrue(observations)
        capsules = [
            (o.get("proof_capsule") or {}).get("material")
            for o in observations.values()
        ]
        self.assertTrue(any(isinstance(m, dict) and m.get("selected_plan")
                            for m in capsules))


class LearningLoopCanReachItsAdapterTests(unittest.TestCase):
    """The headline: the R3 raw success adapter is reachable from a real run."""

    def test_the_replay_context_has_the_shape_the_adapter_requires(self):
        ctx = live._raw_goal_replay_context({"task_id": "T", "goal": "G"})
        self.assertEqual(ctx.get("mode"), "raw_bound")
        self.assertEqual(ctx.get("request"), {"goal": "G", "task_id": "T"})

    def test_an_incomplete_request_produces_no_replay_context(self):
        self.assertIsNone(live._raw_goal_replay_context(None))
        self.assertIsNone(live._raw_goal_replay_context({"goal": "G"}))
        self.assertIsNone(live._raw_goal_replay_context({"goal": "", "task_id": "T"}))

    def test_an_accepted_create_run_is_adaptable(self):
        _reset_learning_state()
        res, checkpoint = _run_keeping_checkpoint("ADAPT", CREATE_GOAL)
        self.assertIs(res.get("semantic_acceptance_complete"), True)
        try:
            self._assert_adaptable()
        finally:
            checkpoint.unlink(missing_ok=True)

    def _assert_adaptable(self):
        state = self_improvement.load_state()
        observations = state.get("observations") or {}
        self.assertTrue(observations)
        oid = next(
            k for k, o in observations.items()
            if ((o.get("proof_capsule") or {}).get("material") or {}).get(
                "selected_plan") == [ARCHIVE_CAPABILITY]
        )
        replay = self_improvement.get_success_replay_context(oid)
        adapted = raw_adapter.adapt(
            {
                "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
                "observation": dict(observations[oid]),
                "replay_context": replay["context"],
                "improvement_work_id": "test",
                "authority_requested": "CANDIDATE_ONLY",
            },
            repo_root=REPO_ROOT,
        )
        self.assertIsInstance(adapted, dict)
        self.assertEqual(
            adapted.get("status"), "RAW_ACCEPTED_SUCCESS_EPISODE_CANDIDATE_READY")
        # It grants nothing: a candidate is not a promotion.
        self.assertIs(adapted.get("promotion_authority"), False)
        self.assertIs(adapted.get("execution_authority"), False)
        self.assertIs(
            adapted["solver_output"]["current_episode_verified"], False)

    def test_the_old_replay_shape_is_rejected_by_the_adapter(self):
        """Negative control: the shape this replaced adapted nothing."""
        _reset_learning_state()
        res, checkpoint = _run_keeping_checkpoint("ADAPT_NEG", CREATE_GOAL)
        try:
            state = self_improvement.load_state()
            observations = state.get("observations") or {}
            oid = next(
                k for k, o in observations.items()
                if ((o.get("proof_capsule") or {}).get("material") or {}).get(
                    "selected_plan") == [ARCHIVE_CAPABILITY]
            )
            self._assert_not_adaptable(observations, oid)
        finally:
            checkpoint.unlink(missing_ok=True)

    def _assert_not_adaptable(self, observations, oid):
        adapted = raw_adapter.adapt(
            {
                "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
                "observation": dict(observations[oid]),
                "replay_context": {"surface": "RAW_GOAL_FRONT_DOOR_V1",
                                   "goal": CREATE_GOAL},
                "improvement_work_id": "test",
                "authority_requested": "CANDIDATE_ONLY",
            },
            repo_root=REPO_ROOT,
        )
        self.assertIsNone(adapted)


class LearningHappensInsideTheRunTests(unittest.TestCase):
    """The loop must close during the run, not when someone asks it to.

    Recording alone left it open: the front door retained each success and the
    improvement queue driver could turn one into a verified episode, but nothing
    on the live path called it, so `verified_episode_count` stayed 0 until
    `advance_once` was invoked by hand.
    """

    def setUp(self):
        _reset_learning_state()
        self.output = REPO_ROOT / (
            f"canonical/astra_runtime/tmp/learning_probe_{_NONCE}.tar.gz"
        )
        self.checkpoint = None

    def tearDown(self):
        self.output.unlink(missing_ok=True)
        if self.checkpoint is not None:
            self.checkpoint.unlink(missing_ok=True)

    def _run(self, tag):
        res, self.checkpoint = _run_keeping_checkpoint(
            tag, _grammar_goal(str(self.output.relative_to(REPO_ROOT))))
        return res

    def test_it_starts_from_no_verified_experience(self):
        stats = self_improvement.load_state().get("stats") or {}
        self.assertEqual(int(stats.get("verified_episode_count") or 0), 0)

    def test_one_run_yields_an_independently_verified_episode(self):
        """No manual driver call anywhere in this test."""
        res = self._run("LEARN")
        self.assertIs(res.get("semantic_acceptance_complete"), True)
        state = self_improvement.load_state()
        self.assertEqual(len(state.get("episodes") or {}), 1)
        self.assertEqual(
            int((state.get("stats") or {}).get("verified_episode_count") or 0), 1)

    def test_a_verified_episode_is_not_a_promoted_skill(self):
        """One example must not generalise. The queue asks for more matching
        episodes instead of minting a skill from a single success."""
        self._run("LEARN_SKILL")
        state = self_improvement.load_state()
        self.assertEqual(len(state.get("skills") or {}), 0)
        self.assertEqual(
            (self_improvement.next_improvement_action() or {}).get("kind"),
            "COLLECT_MATCHING_VERIFIED_EPISODE")

    def test_a_broken_learning_layer_cannot_fail_a_run(self):
        from canonical.runtime import r3_improvement_queue_driver_v1 as driver

        real = driver.drain

        def _boom(*args, **kwargs):
            raise RuntimeError("LEARNING_QUEUE_IS_BROKEN")

        driver.drain = _boom
        try:
            res = self._run("LEARN_BOOM")
        finally:
            driver.drain = real
        self.assertIs(res.get("pass"), True)

    def test_nothing_learned_decides_the_outcome(self):
        """Wiping retained experience must not change the result: the outcome
        comes from execution and re-inspection, never from memory."""
        res = self._run("LEARN_COLD")
        _reset_learning_state()
        self.assertEqual(
            int((self_improvement.load_state().get("stats") or {})
                .get("verified_episode_count") or 0), 0)
        self.assertIs(res.get("semantic_acceptance_complete"), True)
        self.assertEqual(res.get("selected_plan"), [ARCHIVE_CAPABILITY])


if __name__ == "__main__":
    unittest.main()
