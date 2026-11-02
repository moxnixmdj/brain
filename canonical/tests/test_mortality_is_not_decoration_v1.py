"""Is the ending real, or is it a counter with a name?

WHY THIS EXISTS
---------------
`mortality_and_triage_v1` claims three things no other module in this tree could claim:

  * it has a finite life, granted once and not extendable from inside;
  * it knows, and can name what it will not get to do;
  * knowing changes what it starts.

Each is easy to fake. A counter nobody reads is decoration, and a "life" a restart renews is a game
with infinite lives. So the tests are negative controls:

  DECISIVE   test_knowing_it_can_end_changes_what_it_starts
             An agent that consults its life must start different work than one that does not.
             If both start the same thing, nothing is at stake.

  HONEST     test_the_wall_is_a_convention_not_an_enforcement
             `life.granted = 999` works, because this is Python. The claim that it cannot extend
             its own life is a property of the methods, not of the object -- asserted here so the
             limit is visible rather than implied.
"""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import mortality_and_triage_v1 as M  # noqa: E402


class LifeTests(unittest.TestCase):
    def test_life_is_granted_once_and_only_decreases(self):
        life = M.Life(identity="a", granted=10.0)
        self.assertEqual(life.remaining, 10.0)
        life.spend(4.0)
        self.assertEqual(life.remaining, 6.0)
        for call in (lambda: life.knows(), lambda: life.unfinished([]),
                     lambda: life.can_finish(1.0), lambda: life.near_the_end(),
                     lambda: life.as_row()):
            call()
        self.assertEqual(life.remaining, 6.0)

    def test_it_cannot_spend_more_than_it_has(self):
        life = M.Life(identity="a", granted=5.0)
        with self.assertRaises(ValueError):
            life.spend(6.0)

    def test_life_cannot_be_spent_backwards(self):
        with self.assertRaises(ValueError):
            M.Life(identity="a", granted=5.0).spend(-1.0)

    def test_it_can_name_what_it_will_not_get_to_do(self):
        life = M.Life(identity="a", granted=10.0)
        board = [M.Work("cheap", value=1.0, cost=4.0), M.Work("dear", value=100.0, cost=40.0)]
        self.assertEqual(life.unfinished(board), ["dear"])

    # ------------------------------------------------------- the decisive test

    def test_knowing_it_can_end_changes_what_it_starts(self):
        board = M.demonstration_board()
        knowing = M.live(M.Life(identity="a", granted=40.0), board, consult=True)
        blind = M.live(M.Life(identity="a", granted=40.0), board, consult=False)
        self.assertNotEqual(knowing["finished"], blind["finished"])
        self.assertEqual(blind["lost_mid_task"], ["great_work"])
        self.assertEqual(knowing["lost_mid_task"], [])

    def test_it_never_starts_what_it_cannot_finish(self):
        life = M.Life(identity="a", granted=10.0)
        board = [M.Work("huge", value=1000.0, cost=11.0), M.Work("ok", value=1.0, cost=10.0)]
        self.assertEqual(M.choose_next(life, board).id, "ok")

    def test_losing_life_mid_task_yields_no_value(self):
        board = M.demonstration_board()
        result = M.live(M.Life(identity="a", granted=40.0), board, consult=False)
        self.assertIn("great_work", result["lost_mid_task"])
        self.assertEqual(result["realised_value"], 190.0)   # not 440

    def test_knowing_makes_it_more_effective_not_less(self):
        row = M.measure()
        self.assertTrue(row["knowing_realises_more"])
        self.assertGreater(row["knows_it_can_end"]["realised_value"],
                           row["does_not_consult_its_life"]["realised_value"])

    def test_an_unlimited_life_never_stops_and_is_not_the_same_thing(self):
        row = M.measure()
        self.assertTrue(row["never_ends"]["knows"]["immortal"])
        self.assertEqual(row["never_ends"]["lost_mid_task"], [])
        self.assertGreater(row["never_ends"]["realised_value"],
                           row["knows_it_can_end"]["realised_value"])

    def test_a_spent_out_life_does_nothing(self):
        result = M.live(M.Life(identity="a", granted=3.0), M.demonstration_board())
        self.assertEqual(result["finished"], [])
        self.assertEqual(result["realised_value"], 0.0)

    # ------------------------------------------------------------ durability

    def test_restarting_does_not_restore_life(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = M.LifeStore(pathlib.Path(tmp) / "life.json")
            life = store.load(identity="a", granted=10.0)
            life.spend(7.0)
            store.save(life)
            again = store.load(identity="a", granted=10.0)
            self.assertEqual(again.remaining, 3.0)

    def test_another_identity_gets_its_own_life(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = M.LifeStore(pathlib.Path(tmp) / "life.json")
            life = store.load(identity="a", granted=10.0)
            life.spend(10.0)
            store.save(life)
            self.assertEqual(store.load(identity="b", granted=10.0).remaining, 10.0)

    def test_a_corrupted_life_file_is_not_a_new_life(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "life.json"
            path.write_text('{"identity": "a", "granted": ')
            self.assertEqual(M.LifeStore(path).load(identity="a", granted=10.0).remaining, 0.0)

    def test_the_wall_is_a_convention_not_an_enforcement(self):
        life = M.Life(identity="a", granted=1.0)
        life.spend(1.0)
        self.assertTrue(life.is_over)
        life.granted = 999.0          # nothing stops this; the limit is the methods, not the object
        self.assertFalse(life.is_over)


if __name__ == "__main__":
    unittest.main(verbosity=2)
