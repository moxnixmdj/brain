"""The machine must not stop at $100 when the goal was $1,000,000.

The driver alone is correct but terminal: STUCK and BOUND are OPEN statuses --
they mean *these actions* stopped moving the number, not that the goal is
reached. Treating them as the end abandons the goal at whatever was reached.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from execution_guard import goal_chase_v1 as gc
from execution_guard import target_chase_driver_v1 as chase


class _Balance:
    """A number on disk that only the machine's current ability can move."""

    def __init__(self, tmp: str, start: float = 0.0) -> None:
        self.path = os.path.join(tmp, "balance.json")
        self.write(start)

    def write(self, v: float) -> None:
        with open(self.path, "w") as fh:
            json.dump(float(v), fh)

    def measure(self):
        try:
            with open(self.path) as fh:
                return float(json.load(fh))
        except (OSError, ValueError):
            return None


class NoStoppingShortTests(unittest.TestCase):
    """What happens between 'stalled' and 'done' is the whole requirement."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-nostop-")
        self.bal = _Balance(self.tmp, 0.0)
        from canonical.runtime import ignorance_ledger_v1 as led
        from canonical.runtime import associative_memory_v1 as mem
        self.led, self.mem = led, mem
        self._lp, self._mp = led.DEFAULT_STATE, mem.DEFAULT_STATE
        led.DEFAULT_STATE = os.path.join(self.tmp, "ledger.json")
        mem.DEFAULT_STATE = os.path.join(self.tmp, "mem.json")
        # learning can REGISTER into the registry -- the source of truth for
        # what the machine can do. A test must never touch the real one.
        from canonical.runtime import capability_type_surface_v1 as ts
        self.ts, self._rp = ts, ts.REGISTRY
        self.regp = os.path.join(self.tmp, "REGISTRY.json")
        with open(ts.REGISTRY, encoding="utf-8") as fh:
            src = fh.read()
        with open(self.regp, "w", encoding="utf-8") as fh:
            fh.write(src)

    def tearDown(self) -> None:
        self.led.DEFAULT_STATE, self.mem.DEFAULT_STATE = self._lp, self._mp
        self.ts.REGISTRY = self._rp
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- the contrast that proves the point ----------------------------

    def test_plain_run_abandons_the_goal_at_what_it_reached(self):
        """This is the behaviour being fixed, pinned so it cannot come back."""
        calls = {"n": 0}

        def act(_ctx):
            calls["n"] += 1
            if calls["n"] <= 2:
                self.bal.write(self.bal.measure() + 100)
            return {"ok": True}

        r = gc.run("grow the balance to 1000000 dollars",
                   measure=self.bal.measure, act=act, target=1000000.0,
                   direction="maximize", unit="dollars",
                   max_rounds=6, patience=2, widen_options=False)
        self.assertNotEqual(r["status"], chase.MET)
        self.assertEqual(r["chase"]["best_measurement"], 200.0)

    def test_chase_until_met_does_not_leave_it_there(self):
        """It resumes, and it says how far short it still is."""
        calls = {"n": 0}

        def act(_ctx):
            calls["n"] += 1
            if calls["n"] <= 2:
                self.bal.write(self.bal.measure() + 100)
            return {"ok": True}

        r = gc.chase_until_met("grow the balance to 1000000 dollars",
                               measure=self.bal.measure, act=act,
                               target=1000000.0, direction="maximize",
                               unit="dollars", max_rounds=6, patience=2,
                               max_learn_attempts=2,
                               registry_path=self.regp, widen_options=False)
        self.assertTrue(r["resumed"])
        self.assertEqual(r["learning_attempts"], 2)
        # 200 reached, 1,000,000 wanted, and it says so instead of claiming it
        self.assertEqual(r["chase"]["best_measurement"], 200.0)
        self.assertEqual(r["shortfall"], 999800.0)
        self.assertNotEqual(r["status"], chase.MET)

    # -- honesty about the stall ---------------------------------------

    def test_every_stall_is_recorded_as_a_ranked_gap(self):
        def act(_ctx):
            return {"ok": True}

        r = gc.chase_until_met("grow the balance to 1000000 dollars",
                               measure=self.bal.measure, act=act,
                               target=1000000.0, direction="maximize",
                               unit="dollars", max_rounds=4, patience=2,
                               max_learn_attempts=2,
                               registry_path=self.regp, widen_options=False)
        self.assertEqual(len(r["stalls"]), 2)
        for s in r["stalls"]:
            self.assertTrue(s["gap"]["recorded"], s)
            self.assertTrue(s["gap"]["gap_id"])
        self.assertTrue(self.led.rank(limit=5))

    def test_the_stall_names_how_far_it_got(self):
        calls = {"n": 0}

        def act(_ctx):
            calls["n"] += 1
            if calls["n"] <= 2:
                self.bal.write(self.bal.measure() + 100)
            return {"ok": True}

        r = gc.chase_until_met("grow the balance to 1000000 dollars",
                               measure=self.bal.measure, act=act,
                               target=1000000.0, direction="maximize",
                               unit="dollars", max_rounds=6, patience=2,
                               max_learn_attempts=1,
                               registry_path=self.regp, widen_options=False)
        self.assertIn("200.0", r["stalls"][0]["gap"]["detail"])

    # -- it must still finish ------------------------------------------

    def test_it_stops_when_the_target_is_actually_met(self):
        """Persistence is not an infinite loop: MET ends it at once."""

        def act(_ctx):
            self.bal.write(self.bal.measure() + 50)
            return {"ok": True}

        r = gc.chase_until_met("grow the balance to 200 dollars",
                               measure=self.bal.measure, act=act,
                               target=200.0, direction="maximize",
                               unit="dollars", max_rounds=8, patience=2,
                               max_learn_attempts=3,
                               registry_path=self.regp, widen_options=False)
        self.assertEqual(r["status"], chase.MET)
        self.assertEqual(r["chase"]["best_measurement"], 200.0)
        self.assertEqual(r["shortfall"], 0.0)
        self.assertEqual(r["learning_attempts"], 0)
        self.assertFalse(r["resumed"])

    def test_resuming_continues_from_where_the_number_is(self):
        """A resumed chase must not restart the count from zero."""
        calls = {"n": 0}

        def act(_ctx):
            calls["n"] += 1
            if calls["n"] <= 2:
                self.bal.write(self.bal.measure() + 100)
            return {"ok": True}

        r = gc.chase_until_met("grow the balance to 1000000 dollars",
                               measure=self.bal.measure, act=act,
                               target=1000000.0, direction="maximize",
                               unit="dollars", max_rounds=6, patience=2,
                               max_learn_attempts=2,
                               registry_path=self.regp, widen_options=False)
        self.assertEqual(self.bal.measure(), 200.0)  # not reset to 0
        self.assertGreaterEqual(r["chase"]["best_measurement"], 200.0)

    def test_learning_attempts_are_bounded(self):
        """Stubborn is not endless: it stops when learning stops yielding."""

        def act(_ctx):
            return {"ok": True}

        r = gc.chase_until_met("grow the balance to 1000000 dollars",
                               measure=self.bal.measure, act=act,
                               target=1000000.0, direction="maximize",
                               unit="dollars", max_rounds=3, patience=1,
                               max_learn_attempts=2,
                               registry_path=self.regp, widen_options=False)
        self.assertLessEqual(r["learning_attempts"], 2)

    def test_zero_learning_attempts_is_allowed(self):
        """max_learn_attempts=0 must reproduce the plain driver exactly."""

        def act(_ctx):
            return {"ok": True}

        r = gc.chase_until_met("grow the balance to 1000000 dollars",
                               measure=self.bal.measure, act=act,
                               target=1000000.0, direction="maximize",
                               unit="dollars", max_rounds=4, patience=2,
                               max_learn_attempts=0,
                               registry_path=self.regp, widen_options=False)
        self.assertFalse(r["resumed"])
        self.assertEqual(r["stalls"], [])
        self.assertEqual(r["learning_attempts"], 0)

    def test_a_terminal_stall_is_not_retried(self):
        """Unmeasurable is a fact about the goal, not a lack of trying."""
        r = gc.chase_until_met("grow the balance to 1000000 dollars",
                               measure=lambda: None, act=lambda _c: {"ok": True},
                               target=1000000.0, direction="maximize",
                               unit="dollars", max_learn_attempts=3,
                               registry_path=self.regp, widen_options=False)
        self.assertEqual(r["status"], chase.NOT_MEASURABLE)
        self.assertEqual(r["learning_attempts"], 0)
        self.assertFalse(r["resumed"])

    def test_learning_records_the_goal_it_tried(self):
        def act(_ctx):
            return {"ok": True}

        r = gc.chase_until_met("grow the balance to 1000000 dollars",
                               measure=self.bal.measure, act=act,
                               target=1000000.0, direction="maximize",
                               unit="dollars", max_rounds=4, patience=2,
                               max_learn_attempts=1,
                               registry_path=self.regp, widen_options=False)
        self.assertEqual(r["stalls"][0]["learning"].get("goal")
                         or r["stalls"][0]["learning"].get("status") is not None,
                         True)

    def test_no_terminal_authority_is_claimed(self):
        def act(_ctx):
            return {"ok": True}

        r = gc.chase_until_met("grow the balance to 1000000 dollars",
                               measure=self.bal.measure, act=act,
                               target=1000000.0, direction="maximize",
                               unit="dollars", max_rounds=4, patience=2,
                               max_learn_attempts=1,
                               registry_path=self.regp, widen_options=False)
        self.assertFalse(r["terminal_authority"])
        self.assertEqual(r["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main()
