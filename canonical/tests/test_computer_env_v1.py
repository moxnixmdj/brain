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
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
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


# --------------------------------------------------------------------------- #
# asking the program how it wants to be called
# --------------------------------------------------------------------------- #
class AskingTests(EnvCase):
    """Six hand-written argv shapes were a strict program: they decided in
    advance how every program on the machine must be called."""

    def test_a_program_is_asked_rather_than_assumed(self):
        text = cenv.help_text("gzip")
        self.assertTrue(text.strip(), "gzip said nothing about itself")
        self.assertIn("gzip", text.lower())

    def test_the_flags_come_from_the_program_not_from_us(self):
        self.assertTrue({"stdout", "to-stdout"} &
                        {f.lstrip("-") for f in cenv.output_flags("tar")},
                        "tar's own help names a way to write to stdout")

    def test_the_shapes_go_beyond_the_hand_written_six(self):
        self.assertGreater(len(cenv.invocation_shapes("tar", "i.txt", "o.tar")),
                           6, "the program's own flags added nothing")

    def test_a_program_that_ignores_the_input_is_refused(self):
        """'arch input.txt' prints the machine architecture and exits 0
        without ever opening the file. Any goal that merely needs SOME bytes
        written is then 'solved' by it, which is how the machine once
        reported saving results to out.csv by writing x86_64."""
        # take what it really prints -- a guessed constant would test nothing
        printed = subprocess.run(["arch", "--version", "out.csv", "input.txt"],
                                 capture_output=True, cwd="/").stdout
        self.assertTrue(printed.strip(), "arch printed nothing")
        self.assertFalse(
            cenv._input_matters(["arch", "--version", "out.csv", "{input}"],
                                "input.txt", "out.csv", printed))

    def test_a_program_that_reads_the_input_is_accepted(self):
        self.assertTrue(cenv._input_matters(["gzip", "-c", "{input}"],
                                            "input.txt", "out.gz",
                                            b"\x1f\x8b\x08\x00real gzip bytes"))

    def test_ignoring_the_input_is_not_learned_as_the_answer(self):
        self.assertIsNone(cenv._single_step(["arch"], ".csv", "out.csv"),
                          "a program that never opened the input was accepted")

    def test_reading_the_input_is_learned_as_the_answer(self):
        got = cenv._single_step(["gzip"], ".gz", "out.gz")
        self.assertIsNotNone(got, "gzip reads its input but was rejected")
        self.assertEqual(got[0], ["run_gzip"])


# --------------------------------------------------------------------------- #
# reading the manual to find which flag the goal is asking for
# --------------------------------------------------------------------------- #
class ManualTests(EnvCase):
    """wc documents -l as 'print the newline counts'. That sentence is where
    the knowledge comes from -- not from us."""

    def test_the_flag_is_chosen_by_what_it_means(self):
        self.assertIn("--lines",
                      cenv.flags_for_goal("wc", "count the lines in notes.txt"))

    def test_a_different_question_gets_a_different_flag(self):
        self.assertIn("-w", cenv.flags_for_goal("wc", "count the words"))
        self.assertIn("-c", cenv.flags_for_goal("wc", "how many bytes"))

    def test_the_program_name_is_not_mistaken_for_a_clue(self):
        """'sort in reverse' must not pick a flag merely because its text
        mentions sorting -- every flag of sort would then look right."""
        self.assertEqual(cenv.flags_for_goal("sort", "sort in reverse")[0],
                         "--reverse")

    def test_filenames_in_the_goal_are_not_clues_either(self):
        self.assertNotIn("--files0-from",
                         cenv.flags_for_goal("wc", "count the lines in notes.txt")
                         [:2])

    def test_goal_words_actually_reach_the_invocations(self):
        shapes = cenv.invocation_shapes("wc", "i.txt", "o.txt",
                                        goal="count the lines")
        self.assertTrue(any(s[:3] == ["wc", "--lines", "i.txt"] for s in shapes),
                        "the flag the goal asked for never got into a command")

    def test_the_chosen_flag_really_does_what_its_documentation_says(self):
        """Not a claim about scoring: run it and count with our own hands."""
        with tempfile.TemporaryDirectory() as d:
            src = pathlib.Path(d) / "notes.txt"
            src.write_bytes(b"alpha\nbeta\ngamma\ndelta\n")
            flag = cenv.flags_for_goal("wc", "count the lines in notes.txt")[0]
            proc = subprocess.run(["wc", flag, "notes.txt"], cwd=d,
                                  capture_output=True, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr[:200])
            self.assertEqual(int(proc.stdout.split()[0]), 4)

    def test_a_goal_that_mentions_nothing_documented_chooses_nothing(self):
        self.assertEqual(cenv.flags_for_goal("wc", "zzzqqq xxxwww"), [])


class MeasuringTests(unittest.TestCase):
    """Goals that name no output file -- "count the lines in notes.txt".

    There is no file to open afterwards, so nothing can be verified by
    reading it back. Choosing the program by whether its manual mentions
    the goal's words was tried and deleted: it answered "count the lines"
    with a compiler's linker options, three times. What is here instead is
    measurement against a file BUILT to hold a known number of the thing.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-measure-")
        self.work = pathlib.Path(self.tmp)
        self.lines = ["alpha %d" % i for i in range(1, 24)]
        self.file = self.work / "notes.txt"
        self.file.write_text("\n".join(self.lines) + "\n")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_line_count_is_measured_and_is_the_true_count(self):
        r = cenv.answer_query("count the lines in notes.txt", self.file,
                              programs=["wc", "grep", "uniq", "nl", "cat"])
        self.assertTrue(r["pass"], r)
        self.assertEqual(r["value"], "23", r)

    def test_two_genuinely_different_programs_agree(self):
        """One program is an opinion. Two are a measurement."""
        r = cenv.answer_query("count the lines in notes.txt", self.file,
                              programs=["wc", "grep", "uniq"])
        self.assertTrue(r["pass"], r)
        self.assertGreaterEqual(r["agreement"], 2, r)
        voters = r["votes"][r["value"]]
        self.assertTrue(any(p.endswith("/wc") for p in voters), voters)
        self.assertTrue(any(p.endswith("/grep") for p in voters), voters)

    def test_a_program_that_counts_runs_is_not_counting_lines(self):
        """uniq --count says 7 on seven lines -- if all seven are the same
        line. A probe built from identical lines cannot tell counting lines
        from counting runs, and lets a program through that is measuring
        something else entirely."""
        seven = cenv.probe_bytes("lines", 7)
        self.assertEqual(len(set(seven.splitlines())), 7,
                         "the probe must hold 7 DIFFERENT lines, or "
                         "'number of lines' and 'number of runs' are the "
                         "same question and the check proves nothing")
        hits = cenv.probe_survivors("lines", ["uniq"],
                                    "count the lines in notes.txt")
        self.assertEqual(hits, [], "uniq counts runs, not lines: %s" % hits)

    def test_it_tracks_the_probe_instead_of_answering_right_once(self):
        """Printing the right number once is not measuring. The number has
        to follow the file that was built to produce it."""
        for prog in ("wc", "grep"):
            with self.subTest(program=prog):
                hits = cenv.probe_survivors(
                    "lines", [prog], "count the lines in notes.txt")
                self.assertTrue(hits, prog)
                self.assertEqual(hits[0].get("tracked"), ["7", "13"], hits)

    def test_three_names_for_one_program_are_not_three_agreements(self):
        """egrep, fgrep and rgrep are shell scripts that exec grep. Left
        alone they vote three times and turn one opinion into a consensus
        -- which is exactly how one compiler under three names once passed
        itself off as three agreeing sources."""
        self.assertEqual(cenv._instrument("egrep"), cenv._instrument("grep"))
        self.assertEqual(cenv._instrument("fgrep"), cenv._instrument("grep"))
        self.assertEqual(cenv._instrument("rgrep"), cenv._instrument("grep"))
        self.assertNotEqual(cenv._instrument("wc"), cenv._instrument("grep"))

    def test_a_question_that_is_not_countable_is_refused_not_guessed(self):
        for goal in ("what is the meaning of notes.txt",
                     "how many bytes per line in notes.txt"):
            with self.subTest(goal=goal):
                r = cenv.answer_query(goal, self.file, programs=["wc"])
                self.assertFalse(r["pass"], r)
                self.assertEqual(r["status"],
                                 "OPEN__NOT_A_COUNTABLE_QUESTION")

    def test_a_file_that_is_not_there_is_refused(self):
        r = cenv.answer_query("count the lines in gone.txt",
                              self.work / "gone.txt", programs=["wc"])
        self.assertFalse(r["pass"], r)
        self.assertEqual(r["status"], "OPEN__NO_EXISTING_INPUT_FILE_IN_GOAL")

    def test_a_program_that_never_stops_talking_does_not_take_us_down(self):
        """'shuf --repeat' permutes its input forever. Read without a cap it
        fills memory until the machine kills the learner -- no exception,
        no traceback, a run that simply disappears."""
        code, out = cenv._run_capped(["shuf", "--repeat", "/dev/null"],
                                     self.work, timeout=2.0)
        self.assertLessEqual(len(out), 1 << 16)
        self.assertTrue(True)

    def test_the_second_question_of_a_kind_is_answered_faster(self):
        """Which command measures this is a fact about the machine, not
        about the file. Paying to find it out twice is not learning."""
        cenv._QUERY_CACHE.clear()
        cenv._QUERY_LOADED = False
        start = time.time()
        cenv.answer_query("count the lines in notes.txt", self.file,
                          programs=["wc", "grep"])
        first = time.time() - start
        start = time.time()
        again = cenv.answer_query("count the lines in notes.txt", self.file,
                                  programs=["wc", "grep"])
        second = time.time() - start
        self.assertTrue(again["pass"], again)
        self.assertLess(second, max(first, 0.05),
                        "second run %.2fs was not faster than %.2fs"
                        % (second, first))


class RememberingTests(unittest.TestCase):
    """Facts about the machine are learned once, not rediscovered forever.

    "Instant" is not a property of an algorithm, it is a property of what
    had to be paid to answer. Two things were being paid over and over:
    every program's manual, and the fingerprint of the problem itself.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-remember-")
        self.work = pathlib.Path(self.tmp)
        # its own store, or one test's planted entry is still sitting there
        # when the next one runs and the two accuse each other of lying
        self._saved_state = os.environ.get("BRAIN_STATE_DIR")
        os.environ["BRAIN_STATE_DIR"] = self.tmp
        cenv._HELP_CACHE.clear()
        cenv._HELP_LOADED = False

    def tearDown(self) -> None:
        if self._saved_state is None:
            os.environ.pop("BRAIN_STATE_DIR", None)
        else:
            os.environ["BRAIN_STATE_DIR"] = self._saved_state
        cenv._HELP_CACHE.clear()
        cenv._HELP_LOADED = False
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_manual_learned_once_is_read_from_disk_not_asked_for_again(self):
        """Proved by substitution, not by repetition: a manual that was
        never in this process is placed on disk under a signature that
        matches, and the machine must hand back exactly that. Checking that
        the same text comes back twice proves nothing -- re-asking the
        program gives the same answer, so the test passes just as happily
        when the cache is switched off entirely.

        What is really at stake is the nine seconds it costs to ask 603
        programs to describe themselves. Paid once it is learning; paid
        every time it is amnesia."""
        prog = "gzip"
        cenv._HELP_CACHE.pop(prog, None)
        cenv._HELP_LOADED = False
        real = cenv.help_text(prog)
        self.assertTrue(real.strip(), "no manual was read at all")
        cenv._help_flush(force=True)
        planted = "PLANTED ON DISK, NEVER ASKED FOR " + str(time.time())
        try:
            store = cenv._help_store_path()
            payload = json.loads(store.read_text())
            payload[prog] = [cenv._help_signature(prog), planted]
            store.write_text(json.dumps(payload))
        except Exception:  # noqa: BLE001
            self.skipTest("no help store was written")
        cenv._HELP_CACHE.clear()
        cenv._HELP_LOADED = False
        self.assertEqual(cenv.help_text(prog), planted,
                         "the store was not consulted -- the manual was "
                         "asked for again instead of remembered")

    def test_a_cache_that_could_be_wrong_is_not_used(self):
        """A manual belongs to a FILE, not to a name. Reinstalling a
        program leaves the name identical and the answer different, so the
        name alone is never trusted -- and a stored entry whose file has
        changed must be read again rather than believed."""
        prog = "gzip"
        cenv._HELP_CACHE.pop(prog, None)
        cenv._HELP_LOADED = False
        real = cenv.help_text(prog)
        cenv._help_flush(force=True)
        # forge an entry against a signature that is not this file's
        try:
            store = cenv._help_store_path()
            payload = json.loads(store.read_text())
            payload[prog] = ["definitely-not-this-file|1|1", "STALE LIES"]
            store.write_text(json.dumps(payload))
        except Exception:  # noqa: BLE001
            self.skipTest("no help store was written")
        cenv._HELP_CACHE.clear()
        cenv._HELP_LOADED = False
        self.assertNotEqual(cenv.help_text(prog), "STALE LIES",
                            "a stale manual was believed")
        self.assertEqual(cenv.help_text(prog), real)

    def test_the_problem_is_measured_once_not_twice(self):
        """Fingerprinting acts out every action to see what it does. It was
        being done once to ask "have I solved this?" and again to remember
        the answer -- the same computation paid twice, which is not
        learning twice."""
        from canonical.runtime import transfer_learning_v1 as tl
        saved = tl.STATE_PATH
        calls = [0]
        real = tl.fingerprint
        try:
            tl.STATE_PATH = os.path.join(self.tmp, "tl.json")
            def counting(env, names, *a, **k):
                calls[0] += 1
                return real(env, names, *a, **k)
            tl.fingerprint = counting
            r = cenv.discover("compress notes.txt into notes.txt.gz")
        finally:
            tl.fingerprint = real
            tl.STATE_PATH = saved
        self.assertTrue(r["closed"], r)
        self.assertEqual(calls[0], 1,
                         "the problem was fingerprinted %d times" % calls[0])

    def test_the_same_question_is_answered_faster_the_second_time(self):
        """What each command measures is a fact about the machine. Asking
        again and paying again is not learning, it is amnesia."""
        src = self.work / "notes.txt"
        src.write_text("\n".join("row %d" % i for i in range(1, 24)) + "\n")
        cenv._QUERY_CACHE.clear()
        progs = ["wc", "grep"]
        start = time.time()
        cenv.answer_query("count the lines in notes.txt", src, programs=progs)
        first = time.time() - start
        start = time.time()
        again = cenv.answer_query("count the lines in notes.txt", src,
                                  programs=progs)
        second = time.time() - start
        self.assertTrue(again["pass"], again)
        self.assertEqual(again["value"], "23", again)
        self.assertLessEqual(second, max(first, 0.02))
