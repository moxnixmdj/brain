#!/usr/bin/env python3
"""The creature was given 40 attempts for its entire life, and then died.

WHY THIS FILE EXISTS
--------------------
`boot()`, `run_sovereign_board()`, `run_awake_creature_pulse()` and
`run_unattended_inspector_investigation()` all defaulted to `life=40.0` against
an attempt cost of 1.0, and `Life` has no earn or credit method. So a creature
got exactly FORTY attempts in its entire existence.

Its own predictor refuses to issue a verdict below `MIN_SETTLED = 20` settled
predictions. It was therefore given ten times the minimum sample, spent all of it
within four or five sessions, and then sat in a state where `can_finish` was
false for every obligation on its board: alive, and permanently unable to act.
Every session after that was a no-op that re-reported a cumulative counter.

Measured 2026-11-04, same creature and board, only the grant changed:

    life  40 ->  40 attempts,  40 settled, own-scorer skill +0.465, CALIBRATED
    life 160 -> 162 attempts, 162 settled, own-scorer skill +0.671, CALIBRATED
    life 480 -> 201 attempts, 201 settled, own-scorer skill +0.681, CALIBRATED

Three turns of this work concluded "the learning loop does not work" from
measurements taken inside that budget. The loop was starved, not broken.

WHAT THIS FILE DOES NOT CLAIM -- the falsifier result, recorded honestly
-----------------------------------------------------------------------
Feeding it does NOT give it a capability. Measured at the fed default: 23
distinct capabilities closed out of 155 registered, 89 parked, and raising
`max_attempts` from 2 to 4 to 6 produced 379 / same / same closes with skill
+0.681 / +0.690 / +0.610. Every additional ladder step is a RETRY of something
already failed, because a settled pass is never re-attempted. So the grant is a
sample-size fix and a fault-tolerance fix, and the capability ceiling lives
somewhere else entirely. `max_attempts` is therefore UNCHANGED at 2 -- the
measurement rejected that half of the change -- and the test below asserts it
stayed put, so re-raising it as a "fix" fails here.
"""
from __future__ import annotations

import unittest

from canonical.runtime import creature_runtime_v1 as cr


class TheCreatureIsNotStarved(unittest.TestCase):
    def test_the_default_grant_covers_more_than_the_predictor_needs(self) -> None:
        """The named default must dominate the cost of producing a verdict."""
        from canonical.runtime import self_prediction_calibration_v1 as SP

        min_samples = SP.MIN_SETTLED
        grant = cr.DEFAULT_LIFE_GRANT
        # Cheapest obligation on a real board, from self_authored_obligations_v1.
        cheapest_attempt = 1.0
        attempts_available = grant / cheapest_attempt
        self.assertGreater(
            attempts_available, 5 * min_samples,
            f"grant {grant} buys only {attempts_available:.0f} attempts against "
            f"MIN_SETTLED={min_samples}; the creature cannot reach a verdict and keep living",
        )

    def test_boot_and_every_runner_use_the_named_grant(self) -> None:
        """One constant, so a runner cannot silently re-starve it."""
        import inspect

        for fn in (cr.boot, cr.run_sovereign_board, cr.run_awake_creature_pulse,
                   cr.run_unattended_inspector_investigation):
            default = inspect.signature(fn).parameters["life"].default
            self.assertEqual(
                default, cr.DEFAULT_LIFE_GRANT,
                f"{fn.__name__} still defaults life to {default!r}",
            )

    def test_booting_actually_receives_it(self) -> None:
        import pathlib
        import tempfile

        with tempfile.TemporaryDirectory(prefix="brain-not-starved-") as td:
            report = cr.boot(pathlib.Path(td) / "c").report()
        self.assertEqual(report["life_remaining"], cr.DEFAULT_LIFE_GRANT)

    # ------------------------------------------------------------------ 4
    # The half of the proposal that the measurement REJECTED. This asserts the
    # rejection, so anyone who "fixes" it back to 4 by intuition fails here.

    def test_more_failure_tolerance_is_not_smuggled_back_in_as_a_fix(self) -> None:
        self.assertEqual(
            cr.Creature.max_attempts, 2,
            "max_attempts was raised. Measured 2026-11-04 at a fed grant: 2/4/6 all close the "
            "same 23 capabilities (skill +0.681/+0.690/+0.610). It re-attempts known failures and "
            "is not a capability lever; the anti-busywork design at 2 is deliberate.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
