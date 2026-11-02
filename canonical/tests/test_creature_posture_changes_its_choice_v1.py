"""Does the creature's history change what it chooses, or only what it reports?

WHY THIS EXISTS
---------------
`creature_stakes_and_initiative_v1` proves posture is real in isolation: a creature that has been
wrong twice declines the best-paying work it cannot check (`test_erasing_its_history_changes_what_it_does`).
But the assembly never consulted it. `Creature.step` picked work through
`mortality_and_triage_v1.choose_next(life, work)`, which takes no standing, and `author_board`
converted `Obligation` (which carries `checkable`) into `Work` (which does not), so the one input
the posture gate needs was dropped on the way in.

Measured before this change, on a board whose best-paying item is uncheckable:

    standalone S.choose : newborn MEASURED -> uncheckable   burned CAUTIOUS -> checkable  (causal)
    assembled step()    : newborn MEASURED -> uncheckable   burned CAUTIOUS -> uncheckable (NOT causal)

So the pillar "what happened to it changes what it attempts next" was true of an organ and false of
the organism -- posture was recorded, reported and persisted, and never once consulted. That is the
decoration the stakes module's own docstring warns about, arriving through the back door of the
assembly, the same way busywork did.

These tests pin the fix and, more importantly, pin what the fix must NOT do:

  DECISIVE   test_a_burned_creature_declines_work_it_cannot_check
             The two creatures differ only in history. If they now choose the same thing, the
             wiring is absent again and this module should be deleted.

  CONTROL    test_on_an_all_checkable_board_history_changes_nothing
             The difference must come from the posture gate, not from a new preference baked into
             selection. With nothing unverifiable to decline, both must choose identically.

  INVARIANT  test_caution_never_makes_it_start_what_it_cannot_finish
             Affordability belongs to the mortality organ and must survive the added gate. This is
             the regression a naive swap to S.choose would cause: S.choose takes no Life argument,
             so replacing choose_next with it starts unaffordable work.

  HONEST     test_caution_does_not_make_it_refuse_to_work
             Caution is a preference, not paralysis. With only unverifiable work available it still
             acts, matching `test_caution_does_not_refuse_to_work` in the stakes suite.

  BOUND      test_this_does_not_make_it_able_to_do_its_own_board
             Stated so nobody quotes this change as progress on the 112. Posture changes which work
             is preferred; it does not create an executor. The board still closes 0.
"""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import creature_runtime_v1 as R  # noqa: E402
from canonical.runtime import self_authored_obligations_v1 as A  # noqa: E402

# Two failures is the organ's own threshold for caution (FAILURES_FOR_CAUTION).
BURN = 2


def board(*items):
    """(id, value, cost, checkable) -> defended proposals plus the worlds that admit them.

    Same admission shape as the assembly suite: the check is false on `before`, true on `done`, so
    a real gap exists and the proposal is admitted rather than refused as already satisfied.
    """
    proposals, before, done = [], {}, {}
    for pid, value, cost, checkable in items:
        proposals.append(A.Proposal(
            id=pid, claim=f"{pid} is done", source="test",
            check=(lambda w, _p=pid: (w.get("inspected") or {}).get(_p) == "ok"),
            value=value, cost=cost, checkable=checkable))
        before.setdefault("inspected", {})[pid] = "no"
        done.setdefault("inspected", {})[pid] = "ok"
    return proposals, before, done


def fails(work, creature):
    """An outcome that is checked and wrong -- the thing that earns caution."""
    return {"ok": False, "verified": True, "correct": False}


class PostureChangesChoiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _creature(self, *items, life=100.0, burned=False, identity="creature"):
        creature = R.boot(self.root / identity, identity=identity, life=life)
        proposals, before, done = board(*items)
        creature.author_board(proposals, before=before, done=done)
        if burned:
            # Recorded through the organ's own public path, and without spending work: two real
            # steps would park the item they failed on, and then choosing it or not would no longer
            # be about posture. History is the only difference between the two creatures.
            for _ in range(BURN):
                creature._standing.record(verified=True, correct=False)
        return creature

    def _pick(self, creature):
        step = creature.step(fails)
        return step.get("work"), step.get("status")

    # ------------------------------------------------------- the decisive test

    def test_a_burned_creature_declines_work_it_cannot_check(self):
        """Best pay is unverifiable. A newborn takes it; a creature with two verified failures
        behind it does not. If these agree, the posture gate is not wired into the assembly."""
        items = [("uncheckable-best", 100.0, 1.0, False), ("checkable-ok", 70.0, 1.0, True)]
        newborn = self._creature(*items, identity="newborn")
        burned = self._creature(*items, burned=True, identity="burned")

        self.assertEqual(newborn.report()["posture"], "MEASURED")
        self.assertEqual(burned.report()["posture"], "CAUTIOUS")

        newborn_pick, newborn_status = self._pick(newborn)
        burned_pick, burned_status = self._pick(burned)

        self.assertEqual(newborn_status, "WORKED")
        self.assertEqual(burned_status, "WORKED")
        self.assertEqual(newborn_pick, "uncheckable-best")
        self.assertEqual(burned_pick, "checkable-ok")
        self.assertNotEqual(newborn_pick, burned_pick)

    def test_caution_costs_it_value_and_that_is_the_point(self):
        """Not a bug: declining the best-paying unverifiable work realises less. Having something at
        stake is supposed to cost something, or it is not a stake."""
        items = [("uncheckable-best", 100.0, 1.0, False), ("checkable-ok", 70.0, 1.0, True)]
        newborn = self._creature(*items, identity="newborn-value")
        burned = self._creature(*items, burned=True, identity="burned-value")

        def closes(work, creature):
            return {"ok": True, "verified": True, "correct": True, "value": work.value}

        self.assertEqual(newborn.step(closes)["work"], "uncheckable-best")
        self.assertEqual(burned.step(closes)["work"], "checkable-ok")
        self.assertGreater(newborn.report()["value_realised"], burned.report()["value_realised"])

    # ---------------------------------------------------------- the controls

    def test_on_an_all_checkable_board_history_changes_nothing(self):
        """Control: with nothing unverifiable to decline, the burned creature must choose exactly
        what a newborn chooses. Otherwise the gate is a preference in disguise, not posture."""
        items = [("best", 100.0, 1.0, True), ("other", 70.0, 1.0, True)]
        newborn = self._creature(*items, identity="newborn-ctl")
        burned = self._creature(*items, burned=True, identity="burned-ctl")
        self.assertEqual(burned.report()["posture"], "CAUTIOUS")
        self.assertEqual(self._pick(newborn)[0], self._pick(burned)[0])

    def test_caution_never_makes_it_start_what_it_cannot_finish(self):
        """Affordability is the mortality organ's gate and must survive the added posture gate. A
        naive swap of choose_next for S.choose fails here: S.choose takes no Life argument, so it
        would start the unaffordable item."""
        items = [("huge-checkable", 100.0, 50.0, True)]
        creature = self._creature(*items, life=3.0, burned=True, identity="poor")
        self.assertEqual(creature.report()["posture"], "CAUTIOUS")
        work, status = self._pick(creature)
        self.assertIsNone(work)
        self.assertEqual(status, "IDLE")
        self.assertEqual(creature.report()["life_spent"], 0.0)

    def test_caution_does_not_make_it_refuse_to_work(self):
        """With only unverifiable work on the board there is nothing to prefer, so a cautious
        creature still acts. Caution that stopped all work would be paralysis, not judgement."""
        items = [("only-uncheckable", 10.0, 1.0, False)]
        creature = self._creature(*items, burned=True, identity="burned-only")
        self.assertEqual(creature.report()["posture"], "CAUTIOUS")
        work, status = self._pick(creature)
        self.assertEqual(work, "only-uncheckable")
        self.assertEqual(status, "WORKED")

    def test_caution_prefers_checkable_work_it_can_finish_over_unaffordable_checkable(self):
        """The gate filters by affordability before it prefers: an unaffordable checkable item must
        not crowd out affordable work, or caution would idle a creature that could still act."""
        items = [("huge-checkable", 100.0, 50.0, True),
                 ("small-uncheckable", 90.0, 1.0, False)]
        creature = self._creature(*items, life=3.0, burned=True, identity="mixed")
        work, status = self._pick(creature)
        self.assertEqual(work, "small-uncheckable")
        self.assertEqual(status, "WORKED")

    # ------------------------------------------------------------- the bound

    def test_this_does_not_make_it_able_to_do_its_own_board(self):
        """Stated so nobody quotes this change as progress on the 112. Wiring posture changes which
        work is preferred; it does not create an executor. With no executor the real board still
        closes nothing, and the creature still says so."""
        with tempfile.TemporaryDirectory() as tmp:
            row = R.run_its_own_board(tmp, cycles=6)
        self.assertGreater(row["authored"]["admitted"], 100)
        self.assertEqual(row["run"]["closed"], 0)

    def test_the_flag_survives_being_authored_and_reloaded(self):
        """`checkable` is kept beside the board, so it must be rebuilt whenever the board is. A
        creature that authors a second board must gate on the new flags, not stale ones."""
        creature = self._creature(("u", 100.0, 1.0, False), burned=True, identity="reauthor")
        self.assertEqual(creature.report()["posture"], "CAUTIOUS")
        self.assertEqual(creature._checkable, {"u": False})
        proposals, before, done = board(("c", 70.0, 1.0, True))
        creature.author_board(proposals, before=before, done=done)
        self.assertEqual(creature._checkable, {"c": True})
        self.assertEqual(self._pick(creature)[0], "c")


if __name__ == "__main__":
    unittest.main(verbosity=2)
