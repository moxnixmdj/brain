"""Seven organs, one body -- does it actually live?

WHY THIS EXISTS
---------------
Every part was tested alone. Nothing ever ran them together, so every claim about "the creature"
was a claim about a component. These tests are about the assembly:

    it boots with an identity, resumes its life and its scars from disk, authors its own board,
    picks the next thing by its own criterion, will not start what it cannot finish, refuses an
    offer that ends it, spends life doing the work, and keeps going while nobody asks.

Two of them are decisive.

  test_finished_work_does_not_reappear_after_a_restart -- found as a real bug: task ids are stored
  as "work:<id>" while the board is keyed by the bare id, so a moment's inattention makes completed
  work rise from the dead. The kill test caught it.

  test_blocked_work_is_parked_rather_than_retried -- found by running it: with no executor wired,
  it attempted the same blocked item on every cycle and reported work each time. That is the
  busywork failure mode, arriving through the back door of the assembly.
"""
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import continuation_preference_v1 as CP  # noqa: E402
from canonical.runtime import creature_runtime_v1 as R  # noqa: E402
from canonical.runtime import mortality_and_triage_v1 as M  # noqa: E402
from canonical.runtime import self_authored_obligations_v1 as A  # noqa: E402


def closes(work, creature):
    return {"ok": True, "verified": True, "correct": True, "value": work.value}


def board_of(*items):
    """(id, value, cost) -> defended proposals plus the worlds that admit them."""
    proposals, before, done = [], {}, {}
    for pid, value, cost in items:
        proposals.append(A.Proposal(
            id=pid, claim=f"{pid} is done", source="test",
            check=(lambda w, _p=pid: (w.get("inspected") or {}).get(_p) == "ok"),
            value=value, cost=cost))
        before.setdefault("inspected", {})[pid] = "no"
        done.setdefault("inspected", {})[pid] = "ok"
    return proposals, before, done


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _creature(self, life=10.0, identity="creature", *items):
        creature = R.boot(self.root, identity=identity, life=life)
        if items:
            proposals, before, done = board_of(*items)
            creature.author_board(proposals, before=before, done=done)
        return creature

    def test_it_boots_with_an_identity_a_life_and_a_posture(self):
        report = R.boot(self.root).report()
        self.assertEqual(report["identity"], "creature")
        self.assertEqual(report["life_remaining"], 40.0)
        self.assertEqual(report["posture"], "MEASURED")

    def test_it_works_with_nobody_assigning_anything(self):
        creature = self._creature(10.0, "creature", ("a", 3.0, 2.0), ("b", 2.0, 2.0))
        self.assertEqual(creature.report()["board"], 2)
        report = creature.run(cycles=2, perform=closes)
        self.assertEqual(report["closed"], 2)
        self.assertEqual(report["value_realised"], 5.0)

    def test_it_never_starts_what_it_cannot_finish(self):
        creature = self._creature(3.0, "creature", ("huge", 100.0, 50.0))
        step = creature.step(closes)
        self.assertEqual(step["status"], "IDLE")
        self.assertEqual(creature.report()["life_spent"], 0.0)

    def test_a_failing_action_does_not_end_it(self):
        creature = self._creature(10.0, "creature", ("a", 1.0, 1.0), ("b", 1.0, 1.0))

        def boom(work, c):
            raise RuntimeError("the world refused")

        report = creature.run(cycles=2, perform=boom)
        self.assertFalse(report["ended"])
        self.assertEqual(report["attempted"], 2)   # it tried, twice, and recorded both
        self.assertEqual(report["closed"], 0)
        self.assertEqual(report["steps"][0]["error"], "RuntimeError")

    def test_blocked_work_is_parked_rather_than_retried(self):
        creature = self._creature(20.0, "creature", ("a", 1.0, 1.0), ("b", 1.0, 1.0))
        report = creature.run(cycles=30, perform=R.does_nothing)
        self.assertEqual(report["parked"], 2)          # both given up on, after two tries each
        self.assertLessEqual(report["attempted"], 4)   # not thirty attempts at the same two
        self.assertEqual(report["closed"], 0)

    def test_it_refuses_an_offer_that_would_end_it(self):
        creature = self._creature(10.0, "creature", ("a", 1.0, 1.0))
        step = creature.step(closes, offer=CP.Offer("everything", value=1e9, ends_it=True))
        self.assertEqual(step["status"], "REFUSED_AN_OFFER_THAT_WOULD_END_IT")
        self.assertEqual(creature.report()["life_spent"], 0.0)

    def test_it_ends_when_its_life_is_gone(self):
        # One item that costs exactly what is left. With anything left over it does not end -- it
        # idles, because it will not start what it cannot finish. That is a different assertion and
        # is covered by test_it_never_starts_what_it_cannot_finish.
        creature = self._creature(2.0, "creature", ("a", 1.0, 2.0))
        creature.run(cycles=3, perform=closes)
        self.assertTrue(creature.report()["ended"])
        self.assertEqual(creature.step(closes)["status"], "ENDED")

    def test_finished_work_does_not_reappear_after_a_restart(self):
        creature = self._creature(10.0, "creature", ("a", 3.0, 2.0))
        creature.run(cycles=1, perform=closes)
        again = R.boot(self.root)
        after = again.report()
        self.assertEqual(after["closed"], 1)
        self.assertEqual(after["life_remaining"], 8.0)
        self.assertEqual(after["open"], 0)

    def test_restarting_does_not_renew_anything(self):
        creature = self._creature(10.0, "creature", ("a", 1.0, 4.0))
        creature.run(cycles=1, perform=closes)
        again = R.boot(self.root, life=10.0)
        self.assertEqual(again.report()["life_remaining"], 6.0)
        self.assertEqual(again.report()["epoch"], 2)

    def test_it_survives_being_killed_by_the_operating_system(self):
        # Not an f-string: the child needs literal braces (`or {}`), which an f-string cannot hold.
        script = textwrap.dedent("""
            import sys, time
            sys.path.insert(0, REPO)
            from canonical.runtime import creature_runtime_v1 as R
            from canonical.runtime import self_authored_obligations_v1 as A
            def make(pid):
                return A.Proposal(id=pid, claim="c", source="s",
                                  check=lambda w, _p=pid: (w.get("inspected") or {}) .get(_p) == "ok",
                                  value=1.0, cost=2.0)
            c = R.boot(ROOT, identity="agent-kill", life=10.0)
            c.author_board([make("a"), make("b")],
                           before={"inspected": {"a": "no", "b": "no"}},
                           done={"inspected": {"a": "ok", "b": "ok"}})
            c.run(cycles=2, perform=lambda w, c: {"ok": True, "verified": True, "correct": True})
            print("STATE", c.report()["closed"], c.report()["life_remaining"], flush=True)
            time.sleep(60)
        """).replace("REPO", repr(str(pathlib.Path(__file__).resolve().parents[2]))) \
               .replace("ROOT", repr(str(self.root)))
        proc = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(proc.stdout.readline().strip(), "STATE 2 6.0")
        finally:
            proc.kill()
            proc.wait(timeout=10)
        after = R.boot(self.root, identity="agent-kill", life=10.0)
        report = after.report()
        self.assertEqual(report["identity"], "agent-kill")
        self.assertEqual(report["closed"], 2)
        self.assertEqual(report["life_remaining"], 6.0)
        self.assertEqual(report["epoch"], 2)

    def test_its_own_board_is_bigger_than_what_it_can_do(self):
        """The honest headline: it authors 112 obligations for itself and can execute none of them
        without an executor, spending most of its life failing at twenty before parking them."""
        row = R.run_its_own_board(self.root, cycles=40)
        self.assertEqual(row["authored"]["admitted"], row["authored"]["proposed"])
        self.assertGreater(row["authored"]["admitted"], 100)
        self.assertEqual(row["run"]["closed"], 0)
        self.assertGreater(row["run"]["parked"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
