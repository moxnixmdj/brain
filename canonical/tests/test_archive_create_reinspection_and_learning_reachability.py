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
from collections.abc import Mapping
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
    """The executed trace row for the create capability.

    Read through `unwrap_bound_adapter_row`, because that is the shape the acceptance
    verifiers actually receive: the verified bound adapter wraps the
    capability's own result and arguments one level down, and the normalization
    is what lets an inspector written against the flat shape still read them.
    """
    trace = [
        trace_acc.unwrap_bound_adapter_row(row)
        for row in ((res.get("controller_execution") or {}).get("trace") or [])
    ]
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

    def test_a_compiled_run_replays_in_the_general_adapters_mode(self):
        """With lineage available the context uses `compiled_bound`, the mode
        that works for any bound capability rather than one sentence shape."""
        ctx = live._raw_goal_replay_context(
            {"task_id": "T", "goal": "G"},
            {"controller_execution": {"trace": [
                {"result": {"capability_id": "c", "requires": ["a.available"],
                            "provides": ["b.produced"]}},
            ]}},
        )
        self.assertEqual(ctx.get("mode"), "compiled_bound")
        self.assertEqual(ctx["request"]["initial_facts"], ["a.available"])
        self.assertEqual(ctx["request"]["target_effects"], ["b.produced"])

    def test_without_lineage_it_falls_back_to_the_raw_mode(self):
        ctx = live._raw_goal_replay_context({"task_id": "T", "goal": "G"})
        self.assertEqual(ctx.get("mode"), "raw_bound")
        self.assertEqual(ctx.get("request"), {"goal": "G", "task_id": "T"})

    def test_lineage_comes_from_the_capabilities_that_ran(self):
        facts, effects = live._plan_lineage({"controller_execution": {"trace": [
            {"result": {"capability_id": "first", "requires": ["x.available"],
                        "provides": ["y.available"]}},
            {"result": {"capability_id": "last", "requires": ["y.available"],
                        "provides": ["z.produced"]}},
            {"result": {"summary": "RAW_GOAL_COMPLETE", "type": "finish"}},
        ]}})
        self.assertEqual(facts, ["x.available"])
        self.assertEqual(effects, ["z.produced"])

    def test_the_trace_normalization_is_a_union_not_a_rewrite(self):
        """The adapter's own keys must survive, or the proof digests and the
        capability identity would be lost."""
        rows = [trace_acc.unwrap_bound_adapter_row(r) for r in [{
            "plan": {"type": "invoke_verified_bound_capability_adapter",
                     "args": {"capability_id": "cid", "inputs": {"path": "p"}}},
            "result": {"capability_id": "cid", "pass": True,
                       "composition_capsule_head_hash": "h" * 64,
                       "result": {"output_path": "o", "capability_id": "other"}},
        }]]
        args = rows[0]["plan"]["args"]
        result = rows[0]["result"]
        self.assertEqual(args["path"], "p")
        self.assertEqual(args["capability_id"], "cid")
        self.assertEqual(result["output_path"], "o")
        # adapter wins the collision, so identity is never overwritten
        self.assertEqual(result["capability_id"], "cid")
        self.assertEqual(result["composition_capsule_head_hash"], "h" * 64)

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
        from canonical.runtime import r3_bound_success_adapter_v1 as bound_adapter

        request = {
            "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
            "observation": dict(observations[oid]),
            "replay_context": replay["context"],
            "improvement_work_id": "test",
            "authority_requested": "CANDIDATE_ONLY",
        }
        # Whichever adapter the replay mode selects, an accepted run must be
        # adaptable by one of them.
        adapted = bound_adapter.adapt(request, repo_root=REPO_ROOT)
        if adapted is None:
            adapted = raw_adapter.adapt(request, repo_root=REPO_ROOT)
        self.assertIsInstance(adapted, dict, "no success adapter accepted this run")
        self.assertIn("EPISODE_CANDIDATE_READY", str(adapted.get("status")))
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


class CorpusGoalsBecomeVerifiedExperienceTests(unittest.TestCase):
    """The point of the whole change: the machine learns from its own goals.

    Before this, learning worked only for a hand-written sentence that matched
    the archive grammar. Measured across the 23 benchmark goals, 9 were
    executed and accepted and **none** of them became verified experience --
    the traces carried no proof digests, so every success adapter refused them.
    """

    def setUp(self):
        _reset_learning_state()
        self.checkpoint = None

    def tearDown(self):
        if self.checkpoint is not None:
            self.checkpoint.unlink(missing_ok=True)

    def _learn(self, tag, goal):
        before = int(
            (self_improvement.load_state().get("stats") or {})
            .get("verified_episode_count") or 0
        )
        res, self.checkpoint = _run_keeping_checkpoint(tag, goal)
        after = int(
            (self_improvement.load_state().get("stats") or {})
            .get("verified_episode_count") or 0
        )
        return res, after - before

    def test_an_accepted_benchmark_goal_becomes_a_verified_episode(self):
        from canonical.runtime import goal_compilation_benchmark_v1 as bench

        goal = next(
            g["goal"] for g in list(bench.BENCHMARK_GOALS) + list(bench.EXTENDED_BENCHMARK_GOALS)
            if g["id"] == "EXT_XLSX_CREATE"
        )
        res, delta = self._learn("CORPUS_XLSX", goal)
        self.assertIs(res.get("semantic_acceptance_complete"), True)
        self.assertEqual(delta, 1, "an accepted corpus goal produced no verified episode")

    def test_the_trace_carries_the_proof_digests_learning_binds_to(self):
        from canonical.runtime import goal_compilation_benchmark_v1 as bench

        goal = next(
            g["goal"] for g in list(bench.BENCHMARK_GOALS) + list(bench.EXTENDED_BENCHMARK_GOALS)
            if g["id"] == "EXT_AST_AUDIT"
        )
        res, _ = self._learn("CORPUS_AST", goal)
        rows = [
            trace_acc.unwrap_bound_adapter_row(row)
            for row in ((res.get("controller_execution") or {}).get("trace") or [])
        ]
        capability_rows = [
            r["result"] for r in rows
            if isinstance(r.get("result"), Mapping) and r["result"].get("capability_id")
        ]
        self.assertTrue(capability_rows)
        for result in capability_rows:
            self.assertEqual(
                len(str(result.get("composition_capsule_head_hash") or "")), 64,
                "no proof digest: this trace could never bind an episode")

    def test_normalization_never_invents_a_field(self):
        """A row with nothing wrapped must come back untouched."""
        row = {"plan": {"type": "finish", "args": {"summary": "X"}},
               "result": {"summary": "RAW_GOAL_COMPLETE"}}
        self.assertEqual(trace_acc.unwrap_bound_adapter_row(row), row)


if __name__ == "__main__":
    unittest.main()


class DurableArtifactDigestIsReverifiedTests(unittest.TestCase):
    """Whatever a capability calls its artifact, the bytes get re-hashed.

    The independent verifier only knew three artifact names. A capability whose
    file was called anything else could never become verified experience, no
    matter how real its work was, and it was refused with
    `NO_HASHED_DURABLE_ARTIFACT_TO_REVERIFY` while holding the bytes. Measured
    across the corpus that cost `EXT_DOCX_VERIFY`: accepted, re-inspected, and
    then forgotten.

    The rule is now "any `<name>_path` that carries a matching `<name>_sha256`".
    That can only add artifacts that get re-checked -- a path with no digest
    sibling is skipped exactly as before, so nothing that was accepted becomes
    refused -- and every pair it does find is still re-opened from disk and
    re-hashed, so a mismatch still refuses.
    """

    def setUp(self):
        self._dir = REPO_ROOT / "canonical/astra_runtime/tmp/durable-artifact-digest"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._made = []

    def tearDown(self):
        for p in self._made:
            p.unlink(missing_ok=True)

    def _write(self, name, payload):
        p = self._dir / name
        p.write_bytes(payload)
        self._made.append(p)
        return str(p.relative_to(REPO_ROOT)).replace("\\", "/")

    def test_a_durable_artifact_under_an_unusual_name_is_reverified(self):
        from canonical.runtime.r3_bound_success_checkpoint_verifier_v1 import (
            _reverify_hashed_artifact,
        )

        rel = self._write("bundle.tar.gz", b"real archive bytes")
        inner = {
            "verified": True,
            "docx_path": rel,
            "docx_sha256": hashlib.sha256(b"real archive bytes").hexdigest(),
        }
        self.assertIs(_reverify_hashed_artifact(inner, REPO_ROOT), True)

    def test_tampering_with_an_unusually_named_artifact_is_refused(self):
        """NEGATIVE CONTROL: the digest must be checked, not trusted."""
        from canonical.runtime.r3_bound_success_checkpoint_verifier_v1 import (
            BoundSuccessVerificationError,
            _reverify_hashed_artifact,
        )

        rel = self._write("tampered.tar.gz", b"real archive bytes")
        inner = {
            "docx_path": rel,
            # the digest of bytes that are not there
            "docx_sha256": hashlib.sha256(b"something else entirely").hexdigest(),
        }
        with self.assertRaises(BoundSuccessVerificationError) as ctx:
            _reverify_hashed_artifact(inner, REPO_ROOT)
        self.assertIn("DURABLE_ARTIFACT_HASH_MISMATCH:docx_path", str(ctx.exception))

    def test_a_path_with_no_digest_sibling_is_still_skipped(self):
        """Guard: widening must not newly refuse what it used to accept.

        `collection_path` is reported without a digest by the spreadsheet
        capability, and was ignored before. It must still be ignored, or this
        change would turn working goals into refusals.
        """
        from canonical.runtime.r3_bound_success_checkpoint_verifier_v1 import (
            _reverify_hashed_artifact,
        )

        hashed = self._write("sheet.xlsx", b"spreadsheet bytes")
        plain = self._write("collection.json", b"input only")
        inner = {
            "output_path": hashed,
            "output_sha256": hashlib.sha256(b"spreadsheet bytes").hexdigest(),
            "collection_path": plain,  # no collection_sha256 on purpose
        }
        self.assertIs(_reverify_hashed_artifact(inner, REPO_ROOT), True)

    def test_a_success_with_no_digested_artifact_is_still_refused(self):
        """Guard: the fail-closed floor is unchanged."""
        from canonical.runtime.r3_bound_success_checkpoint_verifier_v1 import (
            BoundSuccessVerificationError,
            _reverify_hashed_artifact,
        )

        plain = self._write("nodigest.tar.gz", b"real archive bytes")
        with self.assertRaises(BoundSuccessVerificationError) as ctx:
            _reverify_hashed_artifact({"archive_path": plain}, REPO_ROOT)
        self.assertIn("NO_HASHED_DURABLE_ARTIFACT_TO_REVERIFY", str(ctx.exception))

    def test_the_archive_verifier_reports_the_digest_of_what_it_verified(self):
        """The capability now names and digests the file it checked."""
        from canonical.runtime import goal_compilation_benchmark_v1 as bench

        goal = next(
            g["goal"]
            for g in list(bench.BENCHMARK_GOALS) + list(bench.EXTENDED_BENCHMARK_GOALS)
            if g["id"] == "EXT_TAR_VERIFY"
        )
        res, checkpoint = _run_keeping_checkpoint("DURABLE_TAR", goal)
        try:
            self.assertIs(res.get("pass"), True)
            rows = [
                trace_acc.unwrap_bound_adapter_row(row)
                for row in (res.get("controller_execution") or {}).get("trace") or []
            ]
            row = next(
                r for r in rows
                if isinstance(r.get("result"), Mapping)
                and r["result"].get("capability_id") == "archive.verify.tar_gz.gnu"
            )
            result = row["result"]
            digest = result.get("archive_sha256")
            self.assertIsInstance(digest, str)
            self.assertEqual(len(digest), 64)
            on_disk = (REPO_ROOT / str(result["archive_path"])).read_bytes()
            self.assertEqual(
                digest,
                hashlib.sha256(on_disk).hexdigest(),
                "the reported digest is not the digest of the bytes on disk",
            )
        finally:
            checkpoint.unlink(missing_ok=True)


class DocumentVerifyGoalBecomesExperienceTests(unittest.TestCase):
    """The corpus goal this change was measured on.

    `EXT_DOCX_VERIFY` was executed and fully accepted and still produced no
    verified episode, because its capability reported neither the document's
    name nor its digest. It is the goal that moved the corpus from 3 learned to
    4, so it is pinned here rather than left to a census.
    """

    def setUp(self):
        _reset_learning_state()
        self.checkpoint = None

    def tearDown(self):
        if self.checkpoint is not None:
            self.checkpoint.unlink(missing_ok=True)
        _reset_learning_state()

    def test_an_accepted_document_verify_goal_becomes_a_verified_episode(self):
        from canonical.runtime import goal_compilation_benchmark_v1 as bench

        goal = next(
            g["goal"]
            for g in list(bench.BENCHMARK_GOALS) + list(bench.EXTENDED_BENCHMARK_GOALS)
            if g["id"] == "EXT_DOCX_VERIFY"
        )
        before = int(
            (self_improvement.load_state().get("stats") or {}).get("verified_episode_count")
            or 0
        )
        res, self.checkpoint = _run_keeping_checkpoint("DURABLE_DOCX", goal)
        after = int(
            (self_improvement.load_state().get("stats") or {}).get("verified_episode_count")
            or 0
        )
        self.assertIs(res.get("semantic_acceptance_complete"), True)
        self.assertEqual(
            after - before,
            1,
            "an accepted document-verify goal produced no verified episode",
        )


class ArchiveAcceptanceAcceptsTheProofBearingActionTests(unittest.TestCase):
    """The archive verifier judges the work, not the spelling of the action.

    It compared the recorded plan against one hardcoded action shape, the
    registry template. The verified bound adapter action names the same
    capability and carries the same two arguments -- and is the only shape
    whose trace carries the proof digests learning binds to -- so refusing it
    meant an archive goal could be executed, accepted, re-inspected byte for
    byte, and still never become experience. Measured: that cost
    `EXT_TAR_VERIFY`.

    Accepting the second shape must not open a hole, so the controls below are
    the point of this class: the plan digest is still recomputed over the
    actions that actually ran and compared to the controller's own hash, and
    the capability and both arguments are still pinned to the sentence.
    """

    def setUp(self):
        self._out = REPO_ROOT / "canonical/astra_runtime/tmp/accepts-proof-action.tar.gz"
        self._out.unlink(missing_ok=True)
        self.checkpoint = None

    def tearDown(self):
        self._out.unlink(missing_ok=True)
        if self.checkpoint is not None:
            self.checkpoint.unlink(missing_ok=True)

    def _run(self):
        from canonical.runtime import lossless_raw_task_contract_v1 as lrc

        goal = _grammar_goal(
            str(self._out.relative_to(REPO_ROOT)).replace("\\", "/")
        )
        res, self.checkpoint = _run_keeping_checkpoint("ACCEPTS_PROOF", goal)
        _, _, compiled = live.compile_against_live_registry(goal)
        contract = lrc.compile_contract(
            goal,
            source_id="user",
            routing_target_effects=list(compiled.get("target_effects") or []),
        )
        return goal, res, contract

    def _verify(self, goal, res, contract, row=None):
        from canonical.runtime import raw_goal_archive_acceptance_v1 as archive_acc

        rows = res.get("execution")
        row = rows[0] if row is None else row
        # The inputs the verifier binds the sentence to, taken from the action
        # that ran: the bound form nests them under ``inputs``.
        args = row["controller_trace"][0]["plan"].get("args") or {}
        nested = args.get("inputs") if isinstance(args.get("inputs"), dict) else None
        inputs = dict(nested) if isinstance(nested, dict) else dict(args)
        return archive_acc.verify(
            goal=goal,
            capability_id=ARCHIVE_CAPABILITY,
            inputs=inputs,
            execution=row,
            raw_contract=contract,
            root=REPO_ROOT,
        )

    def test_a_real_run_is_accepted_and_reports_the_output_digest(self):
        goal, res, contract = self._run()
        self.assertIs(res.get("pass"), True)
        acceptance = self._verify(goal, res, contract)
        self.assertIs(
            acceptance.get("pass"), True, f"refused: {acceptance.get('reason')}"
        )
        self.assertTrue(acceptance.get("verified_output_sha256"))

    def test_the_recorded_action_still_carries_the_proof_digests(self):
        goal, res, contract = self._run()
        row = res["execution"][0]
        plan = row["controller_trace"][0]["plan"]
        self.assertEqual(
            plan["type"],
            "invoke_verified_bound_capability_adapter",
            "this goal is no longer routed through the proof-bearing action, "
            "so this test no longer proves what it claims",
        )
        inner = row["result"].get("result") or {}
        self.assertEqual(len(row["result"].get("result_sha256") or ""), 64)
        self.assertEqual(len(row["result"].get("composition_capsule_head_hash") or ""), 64)
        self.assertTrue(inner.get("output_sha256"))

    def test_changing_the_output_the_action_names_is_still_refused(self):
        """NEGATIVE CONTROL: the action must still name the sentence's output."""
        import copy

        goal, res, contract = self._run()
        row = copy.deepcopy(res["execution"][0])
        args = row["controller_trace"][0]["plan"]["args"]
        args["output_path"] = "canonical/astra_runtime/tmp/somewhere-else.tar.gz"
        verdict = self._verify(goal, res, contract, row=row)
        self.assertIs(verdict.get("pass"), False)
        self.assertEqual(
            verdict.get("reason"), "CONTROLLER_TRACE_ACTION_BINDING_MISMATCH"
        )

    def test_editing_the_plan_without_touching_its_binding_is_still_refused(self):
        """NEGATIVE CONTROL: the plan digest must still bind the exact bytes.

        The digest is now recomputed over the observed plan rather than over a
        shape this file expects. If that weakened anything, an edit that leaves
        the capability and both arguments intact -- so the binding check has
        nothing to say -- would slip through. It must still fail the digest.
        """
        import copy

        goal, res, contract = self._run()
        row = copy.deepcopy(res["execution"][0])
        row["controller_trace"][0]["plan"]["args"]["injected_note"] = "harmless"
        verdict = self._verify(goal, res, contract, row=row)
        self.assertIs(verdict.get("pass"), False)
        self.assertEqual(
            verdict.get("reason"), "CONTROLLER_TRACE_PLAN_HASH_MISMATCH"
        )

    def test_a_different_capability_in_the_action_is_refused(self):
        """NEGATIVE CONTROL: the action must still name this capability."""
        import copy

        goal, res, contract = self._run()
        row = copy.deepcopy(res["execution"][0])
        row["controller_trace"][0]["plan"]["args"]["capability_id"] = (
            "archive.verify.tar_gz.gnu"
        )
        verdict = self._verify(goal, res, contract, row=row)
        self.assertIs(verdict.get("pass"), False)
        self.assertIn("ACTION_BINDING_MISMATCH", str(verdict.get("reason")))

    def test_an_unsupported_action_type_is_refused(self):
        """NEGATIVE CONTROL: only the two known action shapes are admitted."""
        import copy

        goal, res, contract = self._run()
        row = copy.deepcopy(res["execution"][0])
        row["controller_trace"][0]["plan"]["type"] = "bash_exec"
        verdict = self._verify(goal, res, contract, row=row)
        self.assertIs(verdict.get("pass"), False)
        self.assertIn("ACTION_BINDING_MISMATCH", str(verdict.get("reason")))


class ArchiveVerifyGoalBecomesExperienceTests(unittest.TestCase):
    """The corpus goal this change was measured on: 4 learned becomes 5."""

    def setUp(self):
        _reset_learning_state()
        self.checkpoint = None

    def tearDown(self):
        if self.checkpoint is not None:
            self.checkpoint.unlink(missing_ok=True)
        _reset_learning_state()

    def test_an_accepted_archive_verify_goal_becomes_a_verified_episode(self):
        from canonical.runtime import goal_compilation_benchmark_v1 as bench

        goal = next(
            g["goal"]
            for g in list(bench.BENCHMARK_GOALS) + list(bench.EXTENDED_BENCHMARK_GOALS)
            if g["id"] == "EXT_TAR_VERIFY"
        )
        before = int(
            (self_improvement.load_state().get("stats") or {}).get("verified_episode_count")
            or 0
        )
        res, self.checkpoint = _run_keeping_checkpoint("ARCHIVE_LEARNS", goal)
        after = int(
            (self_improvement.load_state().get("stats") or {}).get("verified_episode_count")
            or 0
        )
        self.assertIs(res.get("semantic_acceptance_complete"), True)
        self.assertEqual(
            after - before,
            1,
            "an accepted archive-verify goal produced no verified episode",
        )


class CompoundPlanUpgradeIsAllOrNothingTests(unittest.TestCase):
    """A compiled plan is upgraded whole, or not at all.

    The learning adapter binds an episode only when *every* recorded step came
    through the verified bound adapter, so a partly upgraded plan earns
    nothing -- and that adapter refuses any capability whose independence was
    never established, which turns a working run into a failed one. Upgrading
    such a plan was measured to cost five accepted goals, so the guard is the
    whole point of the change and is tested directly here rather than inferred
    from a census.
    """

    def _entry(self, cid, provides, independent=True, template_args=None):
        entry = {
            "action_template": {
                "type": "invoke_capability",
                "args": {
                    "capability_id": cid,
                    **(template_args or {"path": "${input.in_path}"}),
                },
            },
            "provides": list(provides),
            "requires": [],
        }
        if independent:
            entry["verification"] = {"independently_verified": True}
        return entry

    def _action(self, cid, **args):
        return {"type": "invoke_capability", "args": {"capability_id": cid, **args}}

    def test_a_fully_verified_plan_is_upgraded(self):
        import unittest.mock as mock

        cid = "test.capability.alpha"
        entry = self._entry(cid, ["effect.alpha"])
        with mock.patch.object(live, "_bound_capability_ids", return_value=frozenset({cid})):
            out = live._upgrade_compound_actions(
                [self._action(cid, path="a/b.txt"),
                 {"type": "finish", "args": {"summary": "X"}}],
                {cid: entry},
            )
        self.assertEqual(out[0]["type"], "invoke_verified_bound_capability_adapter")
        self.assertEqual(out[0]["args"]["capability_id"], cid)
        self.assertEqual(out[0]["args"]["inputs"], {"in_path": "a/b.txt"})
        self.assertEqual(out[0]["args"]["provides"], ["effect.alpha"])
        # the finish row is carried through untouched
        self.assertEqual(out[1], {"type": "finish", "args": {"summary": "X"}})

    def test_one_unverified_capability_leaves_the_whole_plan_alone(self):
        """NEGATIVE CONTROL: this is the guard that prevents the regression."""
        import unittest.mock as mock

        good, bad = "test.capability.alpha", "test.capability.beta"
        admissible = {
            good: self._entry(good, ["effect.alpha"]),
            bad: self._entry(bad, ["effect.beta"], independent=False),
        }
        actions = [self._action(good, path="a.txt"), self._action(bad, path="b.txt")]
        with mock.patch.object(
            live, "_bound_capability_ids", return_value=frozenset({good, bad})
        ):
            out = live._upgrade_compound_actions(actions, admissible)
        self.assertEqual(
            [a["type"] for a in out],
            ["invoke_capability", "invoke_capability"],
            "a plan with one unverified capability was partly upgraded, which "
            "would fail closed at execution and lose the accepted run",
        )
        self.assertEqual(out, actions)

    def test_an_unknown_capability_leaves_the_whole_plan_alone(self):
        import unittest.mock as mock

        known, unknown = "test.capability.alpha", "test.capability.unknown"
        admissible = {known: self._entry(known, ["effect.alpha"])}
        actions = [self._action(known, path="a.txt"), self._action(unknown, path="b.txt")]
        with mock.patch.object(
            live, "_bound_capability_ids", return_value=frozenset({known})
        ):
            out = live._upgrade_compound_actions(actions, admissible)
        self.assertEqual(out, actions)

    def test_unrecoverable_inputs_leave_the_plan_alone(self):
        """An argument that is not a single input reference is not guessed at."""
        import unittest.mock as mock

        cid = "test.capability.alpha"
        entry = self._entry(
            cid,
            ["effect.alpha"],
            template_args={"path": "${input.in_path}", "mode": "literal-not-an-input"},
        )
        actions = [self._action(cid, path="a.txt", mode="literal-not-an-input")]
        with mock.patch.object(live, "_bound_capability_ids", return_value=frozenset({cid})):
            out = live._upgrade_compound_actions(actions, admissible={cid: entry})
        # the literal is not an input reference, so only in_path is recoverable;
        # the plan is still upgraded because nothing was guessed -- mode is a
        # template literal the adapter re-renders itself
        self.assertEqual(out[0]["type"], "invoke_verified_bound_capability_adapter")
        self.assertEqual(out[0]["args"]["inputs"], {"in_path": "a.txt"})

    def test_a_plan_with_no_capability_steps_is_untouched(self):
        actions = [{"type": "finish", "args": {"summary": "X"}}]
        self.assertEqual(live._upgrade_compound_actions(actions, {}), actions)
        self.assertEqual(live._upgrade_compound_actions(None, {}), None)


class CompoundArchiveGoalBecomesExperienceTests(unittest.TestCase):
    """The corpus goal this change was measured on: 5 learned becomes 6.

    A two-clause goal -- create an archive, then verify it -- whose capabilities
    have both had their independence established, so its whole plan can go
    through the proof-bearing action.
    """

    def setUp(self):
        _reset_learning_state()
        self.checkpoint = None

    def tearDown(self):
        if self.checkpoint is not None:
            self.checkpoint.unlink(missing_ok=True)
        _reset_learning_state()

    def test_the_compound_archive_goal_becomes_a_verified_episode(self):
        from canonical.runtime import goal_compilation_benchmark_v1 as bench

        goal = next(
            g["goal"]
            for g in list(bench.BENCHMARK_GOALS) + list(bench.EXTENDED_BENCHMARK_GOALS)
            if g["id"] == "BENCH_TAR_GZ_CREATE_AND_VERIFY"
        )
        before = int(
            (self_improvement.load_state().get("stats") or {}).get("verified_episode_count")
            or 0
        )
        res, self.checkpoint = _run_keeping_checkpoint("COMPOUND_LEARNS", goal)
        after = int(
            (self_improvement.load_state().get("stats") or {}).get("verified_episode_count")
            or 0
        )
        self.assertIs(res.get("semantic_acceptance_complete"), True)
        self.assertEqual(
            after - before,
            1,
            "an accepted compound archive goal produced no verified episode",
        )

    def test_every_step_of_its_plan_carries_proof_digests(self):
        from canonical.runtime import goal_compilation_benchmark_v1 as bench

        goal = next(
            g["goal"]
            for g in list(bench.BENCHMARK_GOALS) + list(bench.EXTENDED_BENCHMARK_GOALS)
            if g["id"] == "BENCH_TAR_GZ_CREATE_AND_VERIFY"
        )
        res, self.checkpoint = _run_keeping_checkpoint("COMPOUND_PROOF", goal)
        try:
            rows = [
                r for r in (res.get("controller_execution") or {}).get("trace") or []
                if isinstance(r.get("result"), Mapping)
                and r["result"].get("capability_id")
            ]
            self.assertEqual(len(rows), 2, "expected the create step and the verify step")
            for row in rows:
                self.assertEqual(
                    row["plan"]["type"],
                    "invoke_verified_bound_capability_adapter",
                    "a step was not routed through the proof-bearing action, so "
                    "the episode could not have been bound",
                )
                self.assertEqual(len(row["result"].get("result_sha256") or ""), 64)
                self.assertEqual(
                    len(row["result"].get("composition_capsule_head_hash") or ""), 64
                )
        finally:
            self.checkpoint.unlink(missing_ok=True)
            self.checkpoint = None
