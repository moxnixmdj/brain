#!/usr/bin/env python3
"""The self-model is fed a constant it already knows to be false.

WHY THIS FILE EXISTS
--------------------
Measured 2026-11-03, on the creature's own 112-obligation sovereign board:

  * `live_autonomous_cycle` called `predict_distribution` with
    `host_ready=True, grounding_complete=True, causal_precond_met=True,
    missing_dep_or_env_block=False, nested_cost_or_timeout_risk=False`
    for every candidate, unconditionally.
  * Result: ONE distinct `predicted_pass_probability` (0.813) and ONE distinct
    `epistemic_mi_nats` across the whole board.
  * The same engine, fed the flags `_extract_capability_feature_flags` already
    computes for the same candidates, produced FOUR distinct probabilities:
    0.062 for blocked candidates, 0.722 for ready ones.
  * 101 of those 112 candidates were blocked for a reason the creature had
    already worked out (`unknown_slot_type_on_surface` x35,
    `writes_fixed_repo_tmp_under_ro_input` x19, `media_or_network_precondition`
    x7, `upstream_coupled_artifact_required` x7, missing binaries/packages...).
    It announced 81.3% confidence on all of them, attempted one, failed it, and
    settled the prediction as a failure -- so its own scorer, correctly, called
    the model worse than a constant (skill -0.113).

The engine was never the problem. `predict_task_probability` already assembled
the honest feature vector, and was used only for *valuing* the board -- never on
the path that predicts, settles, and is scored. The self-model was predicting
with features it had already disproved.

These tests fail on the pre-change commit and pass after it. They are written so
that a re-introduction of a hardcoded all-true feature call fails them again.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

from canonical.runtime import creature_runtime_v1 as cr
from canonical.runtime import self_prediction_calibration_v1 as SPC
from canonical.swe_kernel import sentient_cognitive_core_v1 as scc

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _blocked_id() -> str:
    """An inspector id whose feature flags this host really reports as blocked.

    Chosen by asking the extractor rather than by guessing, so the test cannot rot
    into asserting a shape the host no longer produces.
    """
    for cid in ("auto.pypi.msgpack", "auto.apt.zint", "auto.npm.shelacek-ubjson",
                "CAP_FS_LIST_V1", "no.such.capability.exists"):
        flags = cr._extract_capability_feature_flags(cid)
        if not flags["host_ready"] or flags["missing_dep_or_env_block"]:
            return f"inspector:{cid}"
    raise unittest.SkipTest("host reports no blocked capability to test against")


def _ready_id() -> str:
    reg_ids, inspected = cr._registry_and_inspectors()
    for cid in sorted(reg_ids):
        flags = cr._extract_capability_feature_flags(cid)
        if flags["host_ready"] and flags["grounding_complete"] and flags["causal_precond_met"] \
                and not flags["missing_dep_or_env_block"]:
            return f"inspector:{cid}"
    raise unittest.SkipTest("host reports no ready capability to test against")


class TheSelfModelIsFedWhatTheCreatureKnows(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory(prefix="brain-selfmodel-diet-")
        self.root = pathlib.Path(self._td.name) / "creature"
        self.creature = cr.boot(self.root, identity="diet", life=12.0)

    def tearDown(self) -> None:
        self._td.cleanup()

    # ------------------------------------------------------------------ 1

    def test_a_blocked_and_a_ready_candidate_are_not_given_the_same_belief(self) -> None:
        """The load-bearing assertion: two candidates the creature knows differ, differ."""
        blocked, ready = _blocked_id(), _ready_id()
        kw_b = cr._sovereign_feature_kwargs(blocked, self.creature)
        kw_r = cr._sovereign_feature_kwargs(ready, self.creature)

        self.assertFalse(
            kw_b["causal_precond_met"] and kw_b["host_ready"] and kw_b["grounding_complete"]
            and not kw_b["missing_dep_or_env_block"],
            f"{blocked} is expected to be blocked on this host, but its flags were all-true: {kw_b}",
        )
        self.assertGreaterEqual(kw_r["host_ready"], True)

        belief = self.creature.cognitive_core.belief
        p_blocked = belief.predict_probability(blocked, **kw_b)
        p_ready = belief.predict_probability(ready, **kw_r)

        self.assertGreater(
            p_ready, p_blocked + 0.05,
            f"the belief engine gives a known-blocked candidate {p_blocked:.3f} and a known-ready "
            f"one {p_ready:.3f}; it is not being told what the creature knows",
        )

    # ------------------------------------------------------------------ 2

    def test_the_whole_board_does_not_collapse_to_one_probability(self) -> None:
        """One distinct probability over a heterogeneous board is the defect in one number."""
        reg_ids, _ = cr._registry_and_inspectors()
        belief = self.creature.cognitive_core.belief
        ps = {
            round(belief.predict_probability(
                f"inspector:{cid}", **cr._sovereign_feature_kwargs(f"inspector:{cid}", self.creature)), 6)
            for cid in sorted(reg_ids)
        }
        self.assertGreater(
            len(ps), 1,
            f"all {len(reg_ids)} registry candidates got the same predicted probability {ps}",
        )

    # ------------------------------------------------------------------ 3

    def test_the_hardcoded_all_true_call_is_what_the_test_is_measuring(self) -> None:
        """Negative control: restore the pre-change call and the defect must reappear.

        This is the falsifier for this whole file. If the assertions above still hold
        with every feature forced to `True`, then they are not measuring the wiring.
        """
        reg_ids, _ = cr._registry_and_inspectors()
        ps_known = set()
        ps_forced = set()
        for cid in sorted(reg_ids):
            wid = f"inspector:{cid}"
            ps_known.add(round(scc.EpistemicSelfBeliefEngine().predict_probability(
                wid, **cr._sovereign_feature_kwargs(wid, self.creature)), 6))
        for cid in sorted(reg_ids):
            wid = f"inspector:{cid}"
            ps_forced.add(round(scc.EpistemicSelfBeliefEngine().predict_probability(
                wid,
                host_ready=True,
                grounding_complete=True,
                causal_precond_met=True,
                memory_reflex_hit=False,
                strong_verifier=True,
            ), 6))
        self.assertEqual(len(ps_forced), 1, "the old all-true call no longer collapses to one value")
        self.assertGreater(len(ps_known), len(ps_forced))
        # And the collapsed value is the optimistic one, not the cautious one.
        self.assertGreater(max(ps_forced), max(ps_known) - 0.02)

    # ------------------------------------------------------------------ 4

    def test_a_miss_on_a_known_blocked_candidate_lowers_that_family_next_time(self) -> None:
        """The loop this file is about: the miss must reach the belief, not just the counter."""
        blocked = _blocked_id()
        belief = self.creature.cognitive_core.belief
        kw = cr._sovereign_feature_kwargs(blocked, self.creature)
        before = belief.predict_probability(blocked, **kw)

        ticket = belief.predict_before_act(
            blocked, calibration_ledger=self.creature.calibration_ledger, **kw)
        belief.settle_and_compute_surprise(
            ticket,
            outcome_pass=False,
            inspector="diet_test_independent_inspector",
            actual_cost=0.5,
            actual_gain=0.0,
            calibration_ledger=self.creature.calibration_ledger,
        )
        after = belief.predict_probability(blocked, **kw)
        self.assertLess(
            after, before,
            f"a settled miss did not lower the belief about the same candidate "
            f"({before:.4f} -> {after:.4f})",
        )
        rows = self.creature.calibration_ledger.settled_rows()
        self.assertEqual(len(rows), 1)
        self.assertIs(rows[0]["outcome_pass"], False)


class TheLivePathIsFedItToo(unittest.TestCase):
    """Tests 1-4 exercise `_sovereign_feature_kwargs` directly.

    Measured 2026-11-03: reverting the live call site back to
    `host_ready=True, grounding_complete=True, causal_precond_met=True` left all four of those
    tests GREEN, because none of them went through the code that actually predicts. A helper is
    only worth what the call site passes it. This test spies on `predict_distribution` during a
    real `run_sovereign_board` cycle and asserts the creature's own ranking and prediction calls
    carry a mixed feature picture rather than a constant one.
    """

    def test_the_act_path_feeds_a_known_blocked_candidate_its_blocked_flags(self) -> None:
        seen: list[dict] = []
        original = scc.EpistemicSelfBeliefEngine.predict_distribution

        def spy(self, task_id, features=None, **kwargs):  # noqa: ANN001
            if features is None:
                seen.append({"task_id": task_id, **dict(kwargs)})
            return original(self, task_id, features=features, **kwargs)

        blocked = _blocked_id()
        with tempfile.TemporaryDirectory(prefix="brain-selfmodel-act-") as td:
            creature = cr.boot(pathlib.Path(td) / "creature", identity="act_diet", life=8.0)
            work = cr.M.Work(id=blocked, value=1.0, cost=0.25)
            scc.EpistemicSelfBeliefEngine.predict_distribution = spy  # type: ignore[assignment]
            try:
                cr.sovereign_perform(work, creature)
            finally:
                scc.EpistemicSelfBeliefEngine.predict_distribution = original  # type: ignore[assignment]

        acted = [k for k in seen if k["task_id"] == blocked]
        self.assertGreater(len(acted), 0, f"sovereign_perform never predicted on {blocked}")
        got = acted[0]
        self.assertTrue(
            got.get("missing_dep_or_env_block") or got.get("host_ready") is False,
            f"the act path predicted {blocked} with {got}; on this host that candidate is blocked, "
            f"and the creature had already worked out why",
        )

    def test_a_real_board_cycle_does_not_rank_on_a_constant(self) -> None:
        """Secondary: the board cycle as a whole must not hand the engine one repeated feature row."""
        seen: list[dict] = []
        original = scc.EpistemicSelfBeliefEngine.predict_distribution

        def spy(self, task_id, features=None, **kwargs):  # noqa: ANN001
            if features is None:
                seen.append(dict(kwargs))
            return original(self, task_id, features=features, **kwargs)

        scc.EpistemicSelfBeliefEngine.predict_distribution = spy  # type: ignore[assignment]
        try:
            with tempfile.TemporaryDirectory(prefix="brain-selfmodel-live-") as td:
                cr.run_sovereign_board(pathlib.Path(td) / "creature", cycles=2,
                                       identity="live_diet", life=8.0, slice_size=24)
        finally:
            scc.EpistemicSelfBeliefEngine.predict_distribution = original  # type: ignore[assignment]

        rows = {
            (bool(k.get("host_ready", True)), bool(k.get("grounding_complete", True)),
             bool(k.get("causal_precond_met", True)), bool(k.get("missing_dep_or_env_block", False)),
             bool(k.get("nested_cost_or_timeout_risk", False)))
            for k in seen
        }
        self.assertGreater(len(rows), 1, f"every live prediction used the same flags {rows}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
