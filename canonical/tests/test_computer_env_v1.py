#!/usr/bin/env python3
"""The computer as an environment: find out by acting.

Every other channel needs something given -- a registered capability, a
format in a table, a module the goal named, a source that answered. This one
needs only a directory it may act in, and it discovers which program does
the job by running them and watching.

These use a real directory, real subprocesses and the real learner. A
sabotaged environment -- one that does not really reset, or whose state
ignores content -- must fail here.
"""

from __future__ import annotations

import bz2
import gzip
import lzma
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from canonical.runtime import computer_env_v1 as cenv

ROOT = pathlib.Path(__file__).resolve().parents[2]


class EnvCase(unittest.TestCase):
    def setUp(self) -> None:
        # Both modules resolve STATE_PATH at import time, so the env var is
        # useless once imported: patch the attribute, and never let a test
        # write into the repository's real state.
        from canonical.runtime import curriculum_v1
        from canonical.runtime import transfer_learning_v1
        self.tmp = tempfile.mkdtemp(prefix="brain-cenv-")
        self._saved = (curriculum_v1.STATE_PATH,
                       transfer_learning_v1.STATE_PATH)
        curriculum_v1.STATE_PATH = os.path.join(self.tmp, "curriculum.json")
        transfer_learning_v1.STATE_PATH = os.path.join(self.tmp, "transfer.json")

    def tearDown(self) -> None:
        from canonical.runtime import curriculum_v1
        from canonical.runtime import transfer_learning_v1
        curriculum_v1.STATE_PATH, transfer_learning_v1.STATE_PATH = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def env(self, **kw) -> cenv.ComputerEnv:
        e = cenv.ComputerEnv(**kw)
        self.addCleanup(e.close)
        return e


# --------------------------------------------------------------------------- #
# the environment must be real
# --------------------------------------------------------------------------- #
class EnvironmentTests(EnvCase):
    def test_programs_are_discovered_from_path_not_written_down(self):
        found = cenv.installed_programs(limit=400)
        self.assertGreater(len(found), 20, "almost nothing was discovered")
        for name in ("python3",):
            self.assertIn(name, found)

    def test_dangerous_programs_are_never_offered_as_actions(self):
        found = set(cenv.installed_programs(limit=400))
        for bad in ("rm", "shutdown", "mkfs", "dd"):
            self.assertNotIn(bad, found, "%s must never be an action" % bad)

    def test_reset_restores_the_same_state_every_time(self):
        e = self.env()
        first = e.state()
        e.act("run_true") if "run_true" in e.action_names else None
        e.reset()
        self.assertEqual(e.state(), first, "reset did not restore the state")

    def test_the_state_depends_on_content_not_only_names(self):
        """Two files with the same name and different bytes are not the same
        state. A learner that cannot tell them apart 'achieves' goals it
        never achieved."""
        e = self.env()
        (e.root / "x.txt").write_bytes(b"aaa")
        a = e.state()
        e.reset()
        (e.root / "x.txt").write_bytes(b"bbb")
        b = e.state()
        self.assertNotEqual(a, b, "content was ignored by the state")

    def test_snapshot_really_undoes_an_action(self):
        e = self.env()
        e.register(cenv.program_actions(e, programs=["gzip"],
                                        target="out.gz"))
        before = e.listing()
        token = e.snapshot()
        e.act("run_gzip")
        self.assertNotEqual(e.listing(), before, "the action changed nothing")
        e.restore(token)
        self.assertEqual(e.listing(), before, "restore did not undo it")

    def test_the_environment_reports_the_effect_it_really_had(self):
        """An action that produced the file must not report failure because
        the file is not called what we expected. A rule like "look for
        input.txt.gz" says no for bzip2, xz and every program not yet
        thought of -- and an environment that lies about its own effects
        teaches the learner a false model of the computer."""
        for prog, want in (("gzip", "out.gz"),
                           ("bzip2", "out.bz2"),
                           ("xz", "out.xz")):
            if shutil.which(prog) is None:
                continue
            with self.subTest(prog=prog):
                e = self.env()
                e.register(cenv.program_actions(e, programs=[prog],
                                                target=want))
                self.assertTrue(e.act("run_" + prog),
                                "%s did not produce %s" % (prog, want))
                self.assertIn(want, e.listing())

    def test_an_unknown_action_changes_nothing(self):
        e = self.env()
        before = e.state()
        self.assertFalse(e.act("no_such_action"))
        self.assertEqual(e.state(), before)

    def test_an_action_that_raises_is_data_not_a_crash(self):
        e = self.env()
        e.register([("boom", lambda env: (_ for _ in ()).throw(RuntimeError("x")))])
        self.assertFalse(e.act("boom"), "a raising action returned True")


# --------------------------------------------------------------------------- #
# learning by acting
# --------------------------------------------------------------------------- #
class LearningTests(EnvCase):
    """What the machine can find out with nothing given but a directory."""

    def discover(self, goal: str) -> dict:
        from canonical.runtime import computer_env_v1 as env_mod
        return env_mod.discover(goal)

    def test_the_machine_finds_which_program_makes_the_format(self):
        r = self.discover("compress the input into out.gz")
        self.assertTrue(r["closed"], r)
        self.assertEqual(r.get("plan"), ["run_gzip"], r)

    def test_the_plan_it_finds_is_the_shortest_that_can_exist(self):
        """One action is the shortest possible plan; a longer one would be
        waste, and 'fastest way with minimal actions' is the standing rule."""
        r = self.discover("compress the input into out.gz")
        self.assertTrue(r["closed"], r)
        self.assertEqual(len(r.get("plan") or []), 1)

    def test_a_different_format_finds_a_different_program(self):
        self.assertEqual(self.discover("compress the input into out.gz").get("plan"),
                         ["run_gzip"])
        self.assertEqual(self.discover("make a bzip2 archive out.bz2").get("plan"),
                         ["run_bzip2"])

    def test_a_program_needing_the_output_name_is_still_found(self):
        """'zip out.zip input.txt' does nothing without the name, so a machine
        that only ever runs 'prog input' can never use zip at all."""
        r = self.discover("archive these files into out.zip")
        self.assertTrue(r["closed"], r)
        self.assertEqual(r.get("plan"), ["run_zip"], r)

    def test_what_is_made_is_really_that_format(self):
        """A file CALLED out.zip is not a zip: gzip -c will write gzip bytes
        under any name we like. Opening it with the library that owns the
        format is the only thing that settles it."""
        for goal in ("compress the input into out.gz",
                     "archive these files into out.zip",
                     "compress the data into out.xz"):
            with self.subTest(goal=goal):
                r = self.discover(goal)
                self.assertTrue(r["closed"], r)
                self.assertEqual(r.get("verification"), "ROUND_TRIP_OK", r)

    def test_a_goal_no_program_can_reach_is_reported_not_invented(self):
        r = self.discover("turn the input into out.png")
        self.assertFalse(r["closed"], r)
        self.assertIsNone(r.get("plan") or None)

    def test_the_goal_names_the_file_and_that_is_the_file_made(self):
        r = self.discover("compress the input into out.gz")
        self.assertTrue(r["closed"], r)
        self.assertEqual(r.get("target"), "out.gz",
                         "the goal said out.gz; inventing input.txt.gz "
                         "ignores what was actually asked for")

    def test_the_search_itself_is_real_not_a_guessed_name(self):
        """With the one-action shortcut removed, the learner has to explore.
        Prove it explores rather than reciting an answer."""
        from canonical.runtime import environment_learning_v1 as el
        e = self.env()
        e.register(cenv.program_actions(e, programs=["gzip", "bzip2", "xz"],
                                        target="out.gz"))
        r = el.drive(e, e.action_names,
                     is_goal=lambda snap: "out.gz" in str(snap),
                     budget=120, seed=11)
        self.assertTrue(r.get("reached"), r.get("status"))
        learned = r.get("learned") or {}
        self.assertGreater(learned.get("transition_count", 0), 1,
                           "the learner recorded no transitions")
        self.assertGreater(learned.get("state_count", 0), 1,
                           "the learner only ever saw one state")


class TransferTests(EnvCase):
    def study(self, goal):
        from canonical.runtime import curriculum_v1 as cur
        return cur.study(goal, channels=["explore"])

    def test_the_first_time_learns_and_the_second_does_not(self):
        first = self.study("compress the input into out.gz")
        self.assertTrue(first["pass"], first)
        self.assertFalse(first["attempts"][0].get("from_memory"),
                         "the first attempt cannot come from memory")

        second = self.study("compress the input into out.gz")
        self.assertTrue(second["pass"], second)
        self.assertTrue(second["attempts"][0].get("from_memory"),
                        "the same problem was learned twice")

    def test_what_was_learned_is_replayed_not_guessed(self):
        first = self.study("compress the input into out.gz")
        second = self.study("compress the input into out.gz")
        self.assertEqual(first["attempts"][0].get("plan"),
                         second["attempts"][0].get("plan"))

    def test_the_channel_reports_how_many_actions_it_tried(self):
        r = self.study("compress the input into out.gz")
        self.assertGreater(r["attempts"][0].get("actions_tried", 0), 1)

    def test_a_goal_naming_no_format_is_refused_by_the_channel(self):
        r = self.study("extract text from a pdf file")
        self.assertFalse(r["pass"])
        self.assertEqual(r["attempts"][0]["status"],
                         "OPEN__NO_OUTPUT_FORMAT_IN_GAP")


if __name__ == "__main__":
    unittest.main()


# --------------------------------------------------------------------------- #
# knowing is not doing: run what was learned on a file never seen before
# --------------------------------------------------------------------------- #
class RealFileCase(unittest.TestCase):
    """A real directory with real files in it, written and read for real.

    These are not fixtures standing in for the world -- the filesystem, the
    programs and the bytes are the real ones.
    """

    def setUp(self) -> None:
        from canonical.runtime import curriculum_v1
        from canonical.runtime import transfer_learning_v1
        self.tmp = tempfile.mkdtemp(prefix="brain-perform-")
        self.work = pathlib.Path(self.tmp) / "work"
        self.work.mkdir()
        self.mods = (curriculum_v1, transfer_learning_v1)
        self.saved = [m.STATE_PATH for m in self.mods]
        for m in self.mods:
            m.STATE_PATH = os.path.join(self.tmp, type(m).__name__ + ".json")
        self.text = ("the machine must do this to a file it has never seen\n"
                     * 40).encode()
        (self.work / "notes.txt").write_bytes(self.text)

    def tearDown(self) -> None:
        for m, path in zip(self.mods, self.saved):
            m.STATE_PATH = path
        shutil.rmtree(self.tmp, ignore_errors=True)

    def learn(self, goal: str) -> dict:
        return cenv.discover(goal)

    def test_a_command_learned_on_a_stand_in_runs_on_a_real_file(self):
        r = self.learn("compress notes.txt into notes.txt.gz")
        self.assertTrue(r["closed"], r)
        done = cenv.apply(r["recipe"], self.work / "notes.txt")
        self.assertTrue(done["pass"], done)
        self.assertEqual(pathlib.Path(done["output"]).name, "notes.txt.gz")

    def test_what_it_made_really_contains_the_original_bytes(self):
        """Not "a file exists" -- the file opens and gives back exactly what
        went in. Anything less and the machine has only learned a name."""
        for suf, opener in (("gz", gzip.decompress),
                            ("bz2", bz2.decompress),
                            ("xz", lzma.decompress)):
            with self.subTest(format=suf):
                r = self.learn("compress notes.txt into notes.txt." + suf)
                self.assertTrue(r["closed"], r)
                done = cenv.apply(r["recipe"], self.work / "notes.txt")
                self.assertTrue(done["pass"], done)
                back = opener(pathlib.Path(done["output"]).read_bytes())
                self.assertEqual(back, self.text,
                                 "%s did not give back the original" % suf)

    def test_the_recipe_is_a_real_command_not_a_description(self):
        """Run the argv ourselves, with our own subprocess, nowhere near the
        learner. If it works, the recipe is a command and not a story."""
        r = self.learn("compress notes.txt into notes.txt.gz")
        argv = [str(self.work / "notes.txt") if a == "{input}" else a
                for a in r["recipe"]["argv"]]
        proc = subprocess.run(argv, cwd=str(self.work), capture_output=True,
                              timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr[:200])
        self.assertEqual(gzip.decompress(proc.stdout), self.text)

    def test_it_works_on_a_different_file_than_it_practised_on(self):
        """It learned on a synthetic stand-in. A second, different file proves
        the lesson generalised instead of being memorised."""
        r = self.learn("compress notes.txt into notes.txt.gz")
        other = self.work / "report.txt"
        other.write_bytes(b"a completely different file\n" * 300)
        done = cenv.apply(r["recipe"], other)
        self.assertTrue(done["pass"], done)
        self.assertEqual(gzip.decompress(pathlib.Path(done["output"])
                                         .read_bytes()),
                         other.read_bytes())

    def test_perform_really_leaves_the_file_behind(self):
        done = cenv.perform("compress notes.txt into notes.txt.gz",
                            cwd=str(self.work))
        self.assertTrue(done["pass"], done)
        out = self.work / "notes.txt.gz"
        self.assertTrue(out.is_file(), "the goal was not actually done")
        self.assertEqual(gzip.decompress(out.read_bytes()), self.text)

    def test_perform_refuses_a_file_that_is_not_there(self):
        """A goal about a file that does not exist is a gap, not a task.
        Inventing an input to look capable is worse than stopping."""
        done = cenv.perform("compress missing.txt into missing.txt.gz",
                            cwd=str(self.work))
        self.assertFalse(done["pass"])
        self.assertEqual(done["status"], "OPEN__NO_EXISTING_INPUT_FILE_IN_GOAL")
        self.assertFalse((self.work / "missing.txt.gz").exists())

    def test_the_second_time_is_answered_from_memory_and_still_does_it(self):
        first = cenv.perform("compress notes.txt into notes.txt.gz",
                             cwd=str(self.work))
        self.assertTrue(first["pass"], first)
        (self.work / "notes.txt.gz").unlink()
        second = cenv.perform("compress notes.txt into notes.txt.gz",
                              cwd=str(self.work))
        self.assertTrue(second["pass"], second)
        self.assertTrue(second.get("from_memory"),
                        "the same job was learned twice")
        self.assertTrue((self.work / "notes.txt.gz").is_file())

    def test_apply_reports_a_command_that_produced_nothing(self):
        broken = {"program": "true", "argv": ["true", "{input}"],
                  "stdout_to": "out.gz", "target": "out.gz"}
        done = cenv.apply(broken, self.work / "notes.txt")
        self.assertFalse(done["pass"])
        self.assertEqual(done["status"], "OPEN__COMMAND_PRODUCED_NO_FILE")
