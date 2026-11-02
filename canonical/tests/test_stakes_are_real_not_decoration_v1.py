"""Are the stakes real, or is the posture decoration?

WHY THIS EXISTS
---------------
`creature_stakes_and_initiative_v1` claims two things a diary does not have:

  * what happened to it changes what it will attempt next, and
  * when nobody assigns it anything it chooses its own work and does it.

Both are easy to fake. A posture that never changes a choice is a label; an "initiative" that picks
uniformly is a random number generator. So the tests below are written as negative controls:

  DECISIVE   test_erasing_its_history_changes_what_it_does
             Two creatures, identical except that one has been wrong twice. If they choose the same
             thing, nothing was affected by anything and the module should be deleted.

  CONTROL    test_a_newborn_and_a_burned_creature_differ_only_where_checking_matters
             The difference must come from the posture, not from a preference baked into `choose`.

  HONEST     test_a_saturated_budget_cannot_distinguish_any_chooser
             Found while building: given more steps than the ledger costs, every chooser closes
             everything and the ratio is 1.0. A comparison that cannot fail is not a comparison, so
             the scarcity requirement is asserted rather than assumed.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import creature_stakes_and_initiative_v1 as C  # noqa: E402


def ledger(*, uncheckable_best=True):
    """obl-4 pays best per unit of work and cannot be checked."""
    rows = [(90, 2, True), (70, 3, True), (85, 4, True), (40, 2, True),
            (100, 1, not uncheckable_best), (60, 3, True), (30, 5, True)]
    return [C.Obligation(f"obl-{i}", value=float(v), cost=float(c), checkable=chk)
            for i, (v, c, chk) in enumerate(rows)]


class StakesTests(unittest.TestCase):
    def test_a_newborn_is_not_cautious_and_not_bold(self):
        self.assertEqual(C.Standing(identity="a").posture(), C.DEFAULT_POSTURE)
        self.assertTrue(C.Standing(identity="a").will_trade_on_the_unverifiable())

    def test_caution_is_earned_by_verified_failures(self):
        s = C.Standing(identity="a")
        s.record(verified=True, correct=False)
        self.assertEqual(s.posture(), "MEASURED")  # one mistake is not a reputation
        s.record(verified=True, correct=False)
        self.assertEqual(s.posture(), "CAUTIOUS")
        self.assertFalse(s.will_trade_on_the_unverifiable())

    def test_caution_is_released_by_being_right_twice(self):
        s = C.Standing(identity="a", verified_wrong=2)
        s.record(verified=True, correct=True)
        self.assertEqual(s.posture(), "CAUTIOUS")
        s.record(verified=True, correct=True)
        self.assertEqual(s.posture(), "MEASURED")

    def test_bold_requires_a_streak_and_one_mistake_ends_it(self):
        s = C.Standing(identity="a")
        for _ in range(3):
            s.record(verified=True, correct=True)
        self.assertEqual(s.posture(), "BOLD")
        s.record(verified=True, correct=False)
        self.assertNotEqual(s.posture(), "BOLD")

    def test_claiming_things_it_cannot_check_makes_it_cautious(self):
        s = C.Standing(identity="a")
        s.record(verified=False, correct=None)
        s.record(verified=False, correct=None)
        self.assertEqual(s.posture(), "CAUTIOUS")

    def test_accuracy_is_unknown_before_anything_is_judged(self):
        self.assertIsNone(C.Standing(identity="a").accuracy())

    # ------------------------------------------------------- the decisive test

    def test_erasing_its_history_changes_what_it_does(self):
        """If a creature with two failures behind it chooses what a newborn chooses, nothing is
        at stake. This is the test that decides whether the module earns its place."""
        board = ledger()
        newborn = C.Standing(identity="a")
        burned = C.Standing(identity="a", verified_wrong=2)
        self.assertEqual(newborn.posture(), "MEASURED")
        self.assertEqual(burned.posture(), "CAUTIOUS")
        first = C.choose(newborn, board)
        second = C.choose(burned, board)
        self.assertEqual(first.id, "obl-4")   # best pay, unverifiable
        self.assertEqual(second.id, "obl-0")  # declines it
        self.assertNotEqual(first.id, second.id)

    def test_the_difference_comes_from_the_posture_not_the_chooser(self):
        """Control: with nothing to be cautious about, the burned creature would choose the same."""
        board = ledger(uncheckable_best=False)  # every obligation checkable
        newborn = C.Standing(identity="a")
        burned = C.Standing(identity="a", verified_wrong=2)
        self.assertEqual(burned.posture(), "CAUTIOUS")
        self.assertEqual(C.choose(newborn, board).id, C.choose(burned, board).id)
        # The stakes bite only where checkable and uncheckable work compete -- stated, not hidden.

    def test_caution_does_not_refuse_to_work(self):
        board = [C.Obligation(f"u{i}", value=10.0, cost=2.0, checkable=False) for i in range(3)]
        burned = C.Standing(identity="a", verified_wrong=2)
        self.assertIsNotNone(C.choose(burned, board))

    # --------------------------------------------------------------- initiative

    def test_its_own_criterion_beats_random_selection(self):
        result = C.compare_selection(C.Standing(identity="a"), C.demonstration_ledger(),
                                     steps=C.SCARCE_STEPS)
        self.assertTrue(result["own_beats_random"], result)
        self.assertGreater(result["ratio_vs_random"], 1.5, result)

    def test_a_saturated_budget_cannot_distinguish_any_chooser(self):
        """Honest limitation: with more steps than the ledger costs, everything closes and the two
        choosers tie at 1.0. Found while building; asserted so nobody quotes that tie as a failure
        or a success."""
        big = C.compare_selection(C.Standing(identity="a"), C.demonstration_ledger(), steps=400)
        self.assertEqual(big["ratio_vs_random"], 1.0)
        self.assertEqual(big["own_criterion"]["value_left_open"], 0.0)
        # ...which is why the real comparison is run under scarcity.
        self.assertLess(C.SCARCE_STEPS, sum(o.cost for o in C.demonstration_ledger()))

    def test_it_works_when_nobody_assigns_anything(self):
        """Initiative: no task arrives, work happens anyway."""
        board = C.demonstration_ledger()
        standing = C.Standing(identity="a")
        chosen = []
        result = C.work(board, steps=C.SCARCE_STEPS,
                        pick=lambda pool: chosen.append(C.choose(standing, pool))
                        or chosen[-1])
        self.assertGreaterEqual(result["closed"], 1)
        self.assertEqual(result["idle_steps"], 0)

    def test_a_burned_creature_realises_less_on_this_ledger(self):
        """Not a bug: caution costs it value. That is what having something at stake looks like."""
        board = C.demonstration_ledger()
        newborn = C.work([C.Obligation(o.id, o.value, o.cost, o.checkable) for o in board],
                         steps=C.SCARCE_STEPS, pick=lambda pool: C.choose(C.Standing("a"), pool))
        burned_board = [C.Obligation(o.id, o.value, o.cost, o.checkable) for o in board]
        burned = C.work(burned_board, steps=C.SCARCE_STEPS,
                        pick=lambda pool: C.choose(C.Standing("a", verified_wrong=2), pool))
        self.assertGreater(newborn["realised_value"], burned["realised_value"])

    # -------------------------------------------------------------- durability

    def test_standing_persists_and_is_not_adopted_by_another_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = C.StandingStore(pathlib.Path(tmp) / "standing.json")
            s = store.load(identity="agent-a")
            s.record(verified=True, correct=False)
            s.record(verified=True, correct=False)
            store.save(s)
            self.assertEqual(store.load(identity="agent-a").posture(), "CAUTIOUS")
            self.assertEqual(store.load(identity="agent-b").posture(), C.DEFAULT_POSTURE)

    def test_what_it_learned_about_itself_survives_being_killed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "standing.json"
            script = textwrap.dedent(f"""
                import sys, time
                sys.path.insert(0, {str(pathlib.Path(__file__).resolve().parents[2])!r})
                from canonical.runtime import creature_stakes_and_initiative_v1 as C
                store = C.StandingStore({str(path)!r})
                s = store.load(identity="agent-kill")
                s.record(verified=True, correct=False)
                s.record(verified=True, correct=False)
                store.save(s)
                print("SAVED", s.posture(), flush=True)
                time.sleep(60)
            """)
            proc = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE,
                                    text=True)
            try:
                self.assertEqual(proc.stdout.readline().strip(), "SAVED CAUTIOUS")
            finally:
                proc.kill()
                proc.wait(timeout=10)
            restarted = C.StandingStore(path).load(identity="agent-kill")
            self.assertEqual(restarted.posture(), "CAUTIOUS")
            self.assertEqual(restarted.caution_episodes, 1)

    def test_a_torn_standing_file_is_not_a_standing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "standing.json"
            path.write_text('{"identity": "a", "attempts": ')
            self.assertEqual(C.StandingStore(path).load(identity="a").posture(), C.DEFAULT_POSTURE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
