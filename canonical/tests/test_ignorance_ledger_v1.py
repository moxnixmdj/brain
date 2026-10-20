#!/usr/bin/env python3
"""The machine decides what to learn, and the ordering is earned, not written.

The owner rejected "do 1, 2, 3 and that's it". So the test that matters here is
not that ranking works -- it is that ranking CHANGES as the machine finds out
what actually paid off. A fixed order would pass a weaker test and still be the
strict program they refused.
"""

from __future__ import annotations

import os
import tempfile
import unittest

from canonical.runtime import ignorance_ledger_v1 as led


class LedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(self.path)

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except OSError:
            pass

    # --- it decides for itself ------------------------------------------------

    def test_ordering_is_learned_not_fixed(self):
        """The central property.

        Two gaps, same cost, both untried: the order is arbitrary (or rather,
        tied). After one of them is tried repeatedly and never helps, it must
        sink below the other. Nothing in the code says which -- the outcomes do.
        """
        a = led.note("only one independent source", cost=1.0, path=self.path)
        b = led.note("output format unverifiable", cost=1.0, path=self.path)

        before = {g["id"] for g in led.rank(path=self.path)}
        self.assertEqual(before, {a, b})

        for _ in range(6):
            led.resolve(b, helped=False, close=False, path=self.path)

        order = [g["id"] for g in led.rank(path=self.path)]
        self.assertEqual(order[0], a, "the gap that never helped should sink")
        self.assertEqual(order[-1], b)

    def test_what_helped_most_rises_to_the_top(self):
        slow = led.note("missing source channel", cost=1.0, path=self.path)
        fast = led.note("missing format declaration", cost=1.0, path=self.path)
        # close=False keeps both in the running; a resolved gap is done and
        # correctly drops out of the ranking altogether
        for _ in range(4):
            led.resolve(fast, helped=True, close=False, path=self.path)
        led.resolve(slow, helped=False, close=False, path=self.path)
        self.assertEqual(led.rank(path=self.path)[0]["id"], fast)

    # --- exploration is emergent, not coded ------------------------------------

    def test_untried_beats_known_useless(self):
        """No exploration rule exists. The prior produces it.

        An untried gap scores 0.5 (maximum uncertainty). One tried ten times
        and never useful scores 0.045. So the machine walks toward what it has
        never tested rather than re-testing what has already failed -- and no
        line of code told it to prefer novelty.
        """
        useless = led.note("gap that never helps", cost=1.0, path=self.path)
        for _ in range(10):
            led.resolve(useless, helped=False, close=False, path=self.path)
        fresh = led.note("gap never tried before", cost=1.0, path=self.path)

        order = [g["id"] for g in led.rank(path=self.path)]
        self.assertEqual(order[0], fresh)
        self.assertEqual(order[-1], useless)
        self.assertGreater(led.rank(path=self.path)[0]["p_useful"], 0.4)

    def test_untried_is_not_zero(self):
        gid = led.note("something untested", path=self.path)
        p = led.rank(path=self.path)[0]["p_useful"]
        self.assertAlmostEqual(p, 0.5)

    # --- cost is part of the judgement -----------------------------------------

    def test_cheap_beats_dear_at_equal_worth(self):
        dear = led.note("expensive gap", cost=100.0, path=self.path)
        cheap = led.note("cheap gap", cost=0.1, path=self.path)
        order = [g["id"] for g in led.rank(path=self.path)]
        self.assertEqual(order[0], cheap)
        self.assertEqual(order[-1], dear)

    def test_enough_payoff_overcomes_cost(self):
        """A dear gap that always pays can still outrank a cheap useless one."""
        dear = led.note("dear but vital", cost=20.0, path=self.path)
        cheap = led.note("cheap but useless", cost=0.1, path=self.path)
        for _ in range(30):
            led.resolve(dear, helped=True, close=False, path=self.path)
        for _ in range(30):
            led.resolve(cheap, helped=False, close=False, path=self.path)
        self.assertEqual(led.rank(path=self.path)[0]["id"], dear)

    # --- bookkeeping -----------------------------------------------------------

    def test_same_gap_rephrased_is_the_same_gap(self):
        a = led.note("only one independent channel", why="need more sources",
                     path=self.path)
        b = led.note("need more sources", why="only one independent channel",
                     path=self.path)
        self.assertEqual(a, b)
        self.assertEqual(led.stats(path=self.path)["gaps"], 1)

    def test_different_gaps_stay_different(self):
        led.note("missing output format", path=self.path)
        led.note("missing binary dependency", path=self.path)
        self.assertEqual(led.stats(path=self.path)["gaps"], 2)

    def test_resolving_closes_it(self):
        gid = led.note("a gap", path=self.path)
        led.resolve(gid, helped=True, path=self.path)
        self.assertNotIn(gid, [g["id"] for g in led.rank(path=self.path)])
        self.assertEqual(led.open_gaps(path=self.path), 0)

    def test_failed_attempt_leaves_it_open(self):
        gid = led.note("a gap", path=self.path)
        led.resolve(gid, helped=False, path=self.path)
        self.assertEqual(led.open_gaps(path=self.path), 1)

    def test_resolve_unknown_is_false(self):
        self.assertFalse(led.resolve("nope", path=self.path))

    def test_survives_reload(self):
        gid = led.note("persistent gap", path=self.path)
        for _ in range(3):
            led.resolve(gid, helped=True, close=False, path=self.path)
        self.assertEqual(led.rank(path=self.path)[0]["id"], gid)
        self.assertEqual(led.stats(path=self.path)["tried"], 1)

    def test_stats_are_reported(self):
        led.note("one", path=self.path)
        led.note("two", path=self.path)
        s = led.stats(path=self.path)
        self.assertEqual(s["gaps"], 2)
        self.assertEqual(s["open"], 2)
        self.assertEqual(s["resolved"], 0)


if __name__ == "__main__":
    unittest.main()
