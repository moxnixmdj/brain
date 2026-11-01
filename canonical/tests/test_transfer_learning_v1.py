"""Experience carries over. An environment is not the first one ever seen.

The measurable claim: seven three-dial locks cost 72 trials with transfer
against 112 without, and the model carried forward grows each time --
0, 158, 207, 283, 330, 379, 420 transitions. Each encounter makes the next
cheaper, which is what "instant" has to mean to be worth anything.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest

from canonical.runtime import transfer_learning_v1 as tl


class Lock:
    """Three dials. The machine is never told this."""

    def __init__(self) -> None:
        self.d = [0, 0, 0]

    def reset(self) -> None:
        self.d = [0, 0, 0]

    def state(self):
        return tuple(self.d)  # type: ignore[return-value]

    def act(self, a) -> None:
        i = int(str(a)[1])
        self.d[i] = (self.d[i] + 1) % 10

    def snapshot(self):
        return list(self.d)

    def restore(self, v) -> None:
        self.d = list(v)


class Grid:
    """A different shape entirely, to prove transfer refuses to overreach."""

    def __init__(self) -> None:
        self.p = (0, 0)

    def reset(self) -> None:
        self.p = (0, 0)

    def state(self):
        return self.p

    def act(self, a) -> None:
        x, y = self.p
        m = {"up": (x, y - 1), "down": (x, y + 1),
             "left": (x - 1, y), "right": (x + 1, y)}[str(a)]
        if 0 <= m[0] < 4 and 0 <= m[1] < 4:
            self.p = m

    def snapshot(self):
        return self.p

    def restore(self, v) -> None:
        self.p = v


def h(target):
    return lambda s: sum(abs(a - b) for a, b in zip(s, target))


class _Store:
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="brain-transfer-")
        self._saved = tl.STATE_PATH
        tl.STATE_PATH = os.path.join(self._tmp, "episodes.json")

    def tearDown(self) -> None:
        tl.STATE_PATH = self._saved
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #
# the transfer itself
# --------------------------------------------------------------------------- #
class TransferTests(_Store, unittest.TestCase):
    def test_a_first_encounter_must_learn(self):
        r = tl.drive(Lock(), ["+0", "+1", "+2"],
                     is_goal=lambda s: s == (7, 2, 9),
                     budget=40, max_depth=24, heuristic=h((7, 2, 9)))
        self.assertTrue(r["pass"])
        self.assertFalse(r["transferred"])
        self.assertEqual(r["prior_transitions"], 0)

    def test_a_second_encounter_costs_fewer_trials(self):
        """This is the whole point, measured."""
        first = tl.drive(Lock(), ["+0", "+1", "+2"],
                         is_goal=lambda s: s == (7, 2, 9),
                         budget=40, max_depth=24, heuristic=h((7, 2, 9)))
        second = tl.drive(Lock(), ["+0", "+1", "+2"],
                          is_goal=lambda s: s == (1, 1, 1),
                          budget=40, max_depth=24, heuristic=h((1, 1, 1)))
        self.assertTrue(second["pass"])
        self.assertLess(second["trials_spent"], first["trials_spent"])

    def test_the_carried_model_grows_with_each_encounter(self):
        sizes = []
        for target in ((7, 2, 9), (1, 1, 1), (4, 5, 6)):
            r = tl.drive(Lock(), ["+0", "+1", "+2"],
                         is_goal=lambda s, t=target: s == t,
                         budget=40, max_depth=24, heuristic=h(target))
            self.assertTrue(r["pass"])
            sizes.append(r["prior_transitions"])
        self.assertEqual(sizes[0], 0)
        self.assertGreater(sizes[1], 0)
        self.assertGreater(sizes[2], sizes[1])

    def test_transfer_carries_rules_not_just_a_plan(self):
        """A plan for (7,2,9) cannot reach (1,1,1). Only the rules transfer."""
        tl.drive(Lock(), ["+0", "+1", "+2"], is_goal=lambda s: s == (7, 2, 9),
                 budget=40, max_depth=24, heuristic=h((7, 2, 9)))
        r = tl.drive(Lock(), ["+0", "+1", "+2"], is_goal=lambda s: s == (3, 3, 3),
                     budget=40, max_depth=24, heuristic=h((3, 3, 3)))
        self.assertTrue(r["pass"])
        self.assertEqual(r["plan_length"], 9)      # 3+3+3, minimal

    def test_transfer_saves_trials_across_many_encounters(self):
        total = 0
        for target in ((7, 2, 9), (1, 1, 1), (4, 5, 6), (2, 3, 4)):
            r = tl.drive(Lock(), ["+0", "+1", "+2"],
                         is_goal=lambda s, t=target: s == t,
                         budget=40, max_depth=24, heuristic=h(target))
            total += r["trials_spent"]
        self.assertLess(total, 4 * 16)          # cheaper than relearning each

    def test_transfer_can_be_turned_off(self):
        r = tl.drive(Lock(), ["+0", "+1", "+2"], is_goal=lambda s: s == (1, 1, 1),
                     budget=20, max_depth=12, heuristic=h((1, 1, 1)),
                     use_transfer=False)
        self.assertEqual(r.get("recall_candidates"), 0)


# --------------------------------------------------------------------------- #
# refusing to overreach
# --------------------------------------------------------------------------- #
class RefusalTests(_Store, unittest.TestCase):
    def test_different_action_names_never_transfer(self):
        """A plan written for +0/+1/+2 cannot be replayed as up/down/left."""
        fp_lock = tl.fingerprint(Lock(), ["+0", "+1", "+2"])
        fp_grid = tl.fingerprint(Grid(), ["up", "down", "left", "right"])
        self.assertEqual(tl.similarity(fp_lock, fp_grid), 0.0)

    def test_different_state_shapes_never_transfer(self):
        class Str:
            def reset(self): self.s = ""
            def state(self): return self.s
            def act(self, a): self.s += str(a)
        fp_lock = tl.fingerprint(Lock(), ["+0", "+1", "+2"])
        fp_str = tl.fingerprint(Str(), ["+0", "+1", "+2"])
        self.assertEqual(tl.similarity(fp_lock, fp_str), 0.0)

    def test_identical_environments_are_fully_similar(self):
        a = tl.fingerprint(Lock(), ["+0", "+1", "+2"])
        b = tl.fingerprint(Lock(), ["+0", "+1", "+2"])
        self.assertGreater(tl.similarity(a, b), 0.9)

    def test_nothing_is_recalled_from_an_empty_store(self):
        fp = tl.fingerprint(Lock(), ["+0", "+1", "+2"])
        self.assertEqual(tl.recall(fp, "g"), [])

    def test_a_goal_with_no_prior_is_not_recalled(self):
        tl.drive(Lock(), ["+0", "+1", "+2"], is_goal=lambda s: s == (1, 1, 1),
                 budget=20, max_depth=12, heuristic=h((1, 1, 1)))
        fp = tl.fingerprint(Lock(), ["+0", "+1", "+2"])
        self.assertEqual(tl.recall(fp, "a_goal_never_solved"), [])


# --------------------------------------------------------------------------- #
# the store
# --------------------------------------------------------------------------- #
class StoreTests(_Store, unittest.TestCase):
    def test_remembering_persists(self):
        fp = tl.fingerprint(Lock(), ["+0", "+1", "+2"])
        tl.remember(fp, "g", ["+0", "+0"], reached=True)
        self.assertEqual(tl.stats()["episodes"], 1)

    def test_a_remembered_model_is_stored(self):
        fp = tl.fingerprint(Lock(), ["+0", "+1", "+2"])
        tl.remember(fp, "g", ["+0"], reached=True, model={"s0": {"+0": "s1"}})
        recalled = tl.recall(fp, "g")
        self.assertEqual(recalled[0]["model"], {"s0": {"+0": "s1"}})

    def test_repeating_the_same_lesson_increments_not_duplicates(self):
        fp = tl.fingerprint(Lock(), ["+0", "+1", "+2"])
        tl.remember(fp, "g", ["+0"], reached=True)
        tl.remember(fp, "g", ["+0"], reached=True)
        self.assertEqual(tl.stats()["episodes"], 1)
        self.assertEqual(tl.stats()["total_trials"], 2)

    def test_failure_is_remembered_too(self):
        fp = tl.fingerprint(Lock(), ["+0", "+1", "+2"])
        tl.remember(fp, "g", ["+0"], reached=False)
        self.assertEqual(tl.stats()["disproven"], 1)
        self.assertEqual(tl.stats()["proven"], 0)

    def test_a_proven_plan_ranks_above_an_unproven_one(self):
        fp = tl.fingerprint(Lock(), ["+0", "+1", "+2"])
        tl.remember(fp, "g", ["+0"], reached=False)
        tl.remember(fp, "g", ["+1"], reached=True)
        order = [r["plan"] for r in tl.recall(fp, "g")]
        self.assertEqual(order[0], ["+1"])

    def test_shape_of_recognises_the_kind_of_state(self):
        self.assertEqual(tl.shape_of((1, 2, 3)), "seq[number]3")
        self.assertEqual(tl.shape_of("abc"), "str")
        self.assertEqual(tl.shape_of(5), "number")

    def test_fingerprint_is_cheap(self):
        """It is taken before learning, so it cannot be an exploration."""
        fp = tl.fingerprint(Lock(), ["+0", "+1", "+2"])
        self.assertLessEqual(fp["probes"], tl.DEFAULT_PROBES)


if __name__ == "__main__":
    unittest.main()


class MemorySurvivesADifferentMachine(unittest.TestCase):
    """Learn on one machine; be fast on the next one.

    Measured 2026-11-01, before this class existed: the same computer, the same goal, and
    ONE extra binary on ``PATH`` changed which programs the fingerprint acts out, so
    ``similarity`` was **0.0** and ``recall`` was **[]**.  Everything learned on one image
    was invisible on the next -- "learn it once, permanently" was true only for a machine
    that never changes.

    A fingerprint is a SAMPLE of the machine's vocabulary (this image exposes 623 programs;
    no goal can afford to execute 623 actions to take a signature), so two fingerprints of
    the same machine taken under different goals must still recognise each other.  What
    makes that safe is that a recalled plan is only TRIED, and only if every action it
    names exists here.
    """

    def setUp(self):
        from canonical.runtime import transfer_learning_v1 as tl_
        self.tl = tl_
        self.store = tempfile.mkdtemp(prefix="brain-xmachine-")
        self._saved = tl_.STATE_PATH
        tl_.STATE_PATH = os.path.join(self.store, "episodes.json")

    def tearDown(self):
        self.tl.STATE_PATH = self._saved
        shutil.rmtree(self.store, ignore_errors=True)

    @staticmethod
    def _fp(actions, shape="str", growth=1.0, revisits=0):
        return {"actions": sorted(actions), "shapes": [shape],
                "growth": growth, "revisits": revisits, "probes": 6}

    def test_one_more_program_on_the_machine_does_not_erase_its_memory(self):
        before = self._fp(["run_gzip", "run_gunzip", "run_tar", "run_cp"])
        after = self._fp(["run_gzip", "run_gunzip", "run_tar", "run_cp", "run_xz"])
        self.assertGreater(self.tl.similarity(before, after), 0.5)

    def test_a_narrow_sample_of_the_same_machine_recognises_a_wide_one(self):
        """16 actions seen for one goal, 40 for another, same machine."""
        wide = ["run_%02d" % i for i in range(38)] + ["copy_input", "copy_to_out"]
        narrow = wide[:14] + ["copy_input", "copy_to_out"]
        self.assertGreater(self.tl.similarity(self._fp(wide), self._fp(narrow)), 0.5)

    def test_a_different_kind_of_environment_still_refuses(self):
        lock = self._fp(["+0", "+1", "+2"], shape="seq[int]3")
        grid = self._fp(["up", "down", "left", "right"], shape="seq[int]2")
        self.assertEqual(self.tl.similarity(lock, grid), 0.0)

    def test_a_plan_naming_a_program_this_machine_lacks_is_not_replayed(self):
        self.assertFalse(self.tl.replayable(["run_bzip2"], ["run_gzip", "copy_input"]))
        self.assertTrue(self.tl.replayable(["run_gzip"], ["run_gzip", "copy_input"]))

    def test_the_learned_plan_is_recalled_on_the_next_machine(self):
        first = self._fp(["+0", "+1", "+2"])
        self.tl.remember(first, "dial", ["+1", "+2"], reached=True)
        second = self._fp(["+0", "+1", "+2", "+3"])     # one more action available
        got = self.tl.recall(second, "dial")
        self.assertEqual([r["plan"] for r in got], [["+1", "+2"]])
