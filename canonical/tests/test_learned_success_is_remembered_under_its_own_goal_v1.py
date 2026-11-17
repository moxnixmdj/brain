"""A memory of success must be a memory of THIS goal.

The defect this pins
--------------------
`computer_env_v1._discover_impl` kept every closed goal in the transfer store
under the constant string ``"goal"``::

    gkey = "goal"                      # <-- every goal, one key

The fingerprint deliberately excludes the target (see ``fingerprint_key``),
which is right -- a fingerprint is a fact about the programs, not about the
name of the file.  But the goal's identity then appeared NOWHERE in the memory
key, so recall matched across goals.

Measured 2026-11-16 by asking this route for thirteen unrelated goals and
reading the store it wrote.  Twelve distinct goals produced twelve rows all
keyed ``"goal"``, each recording ``reached=True``, with plans consisting of
whatever single program happened to touch the target first::

    goal -> run_iconv                  (an encoding converter)
    goal -> run_gp-display-src         (a Ghostscript source dumper)
    goal -> run_x86_64-linux-gnu-cpp   (the C preprocessor)
    goal -> run_unexpand               (a whitespace tool)
    goal -> run_bzip2                  (this one really did compress)

The row for a wrong program looked exactly like the row for a right one.  What
saves the ANSWER in practice is that ``_verify_plan`` re-executes a recalled
plan against the target actually asked for, so a stale memory costs one trial
instead of producing a wrong answer.  That is a good property, and it is not a
reason to keep writing false successes to disk: every other reader of the
store (audits, similarity scoring, episode counts, the similarity bonus in
``transfer_learning_v1.recall``) sees a plan labelled correct that is not.

HOW THIS TEST IS BUILT
----------------------
An earlier version of this file re-derived the key with its own helper.  It
passed while the module was mutated back to ``gkey = "goal"`` -- it was testing
the test.  So nothing here recomputes the key: every assertion runs the real
``_discover_impl`` against a real ``ComputerEnv`` and reads what was actually
written to the store.

The store is redirected to a temporary directory, so the tests neither depend
on nor pollute the repository's episode file.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from canonical.runtime import computer_env_v1 as ce


class _StoreSandbox:
    """Point transfer_learning_v1's store at a temp file for one test."""

    def __init__(self) -> None:
        self.dir = tempfile.mkdtemp(prefix="goal_key_store_")

    def __enter__(self):
        from canonical.runtime import transfer_learning_v1 as tl
        self._patch = mock.patch.object(
            tl, "STATE_PATH", os.path.join(self.dir, "episodes.json"))
        self._patch.start()
        self.tl = tl
        return tl

    def __exit__(self, *exc):
        self._patch.stop()
        return False


class DistinctGoalsAreDistinctMemories(unittest.TestCase):
    def _rows_for(self, goals):
        with _StoreSandbox() as tl:
            for goal in goals:
                try:
                    ce.discover(goal, budget=8)
                except Exception:  # noqa: BLE001 - a refusal is a legal outcome
                    pass
            return list(tl._load() or [])

    def test_two_unrelated_goals_do_not_share_a_memory_key(self):
        rows = self._rows_for([
            "compress input.txt into out.gz",
            "hash input.txt into out.sha256",
        ])
        keys = {r.get("goal_key") for r in rows if r.get("plan")}
        self.assertGreaterEqual(
            len(rows), 1,
            msg="no episode was written at all, so this test proves nothing")
        if len(rows) < 2:
            self.skipTest("only one goal closed on this machine; "
                          "cannot compare two keys")
        self.assertGreater(
            len(keys), 1,
            msg="two different goals were remembered under one key: %r" % (keys,))

    def test_no_episode_uses_the_shared_constant(self):
        rows = self._rows_for([
            "compress input.txt into out.gz",
            "hash input.txt into out.sha256",
        ])
        self.assertGreaterEqual(len(rows), 1,
                                msg="no episode was written; nothing was checked")
        shared = [r for r in rows if r.get("goal_key") == "goal"]
        self.assertEqual(
            shared, [],
            msg="%d episode(s) still keyed on the constant 'goal': %r"
                % (len(shared), [r.get("plan") for r in shared]))


class TheSameGoalIsStillTheSameMemory(unittest.TestCase):
    """The fix must not defeat recall -- that is the point of the store."""

    def test_repeating_a_goal_reuses_its_key(self):
        with _StoreSandbox() as tl:
            for _ in range(2):
                try:
                    ce.discover("compress input.txt into out.gz", budget=8)
                except Exception:  # noqa: BLE001
                    pass
            rows = [r for r in (tl._load() or []) if r.get("plan")]
            self.assertGreaterEqual(len(rows), 1,
                                    msg="no episode written; nothing was checked")
            keys = {r.get("goal_key") for r in rows}
            self.assertEqual(
                len(keys), 1,
                msg="the same goal produced %d different keys: %r"
                    % (len(keys), keys))


if __name__ == "__main__":
    unittest.main()
