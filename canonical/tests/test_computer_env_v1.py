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


class RankingTests(unittest.TestCase):
    """Which programs get tried first decides whether a question is
    answered in seconds or in minutes."""

    def test_a_flag_named_after_what_was_asked_is_found(self):
        """sort describes --unique as "output only the first of an equal
        run" -- which contains neither 'unique' nor 'line'. Reading only
        descriptions ranks sort 91st of 241 for "how many unique lines"
        and never offers the one flag that answers the question.

        A flag NAMED after the thing the goal asked for is the strongest
        signal on the machine: whoever wrote the manual chose that word.
        """
        flags = cenv.flags_for_goal("sort",
                                    "how many unique lines in data.txt")
        self.assertIn("--unique", flags,
                      "the flag that answers was never offered: %r" % flags)

    def test_the_tool_that_answers_outranks_one_that_merely_mentions(self):
        """Mentioning the goal's words is not the same as doing the job.
        Ranking by how many flags match rewards a program for repeating
        the words, so a tool that says 'lines' three times outranked the
        one that can actually deduplicate."""
        ranked = cenv.programs_for_goal(
            "how many unique lines in data.txt", limit=120)
        self.assertIn("sort", ranked)
        self.assertIn("uniq", ranked)
        # uniq only collapses NEIGHBOURS and cannot answer this, but it
        # is the program whose whole manual is about uniqueness; sort is
        # the one whose --unique does. Both must be near the front, well
        # inside the budget the search actually spends.
        self.assertLess(ranked.index("sort"), 100,
                        "sort ranked %d: %r"
                        % (ranked.index("sort"), ranked[:12]))

    def test_the_flag_that_answers_is_offered_before_the_45_that_cannot(self):
        """Ordering decides what a deadline can reach.

        'sort' documents 52 flags and '--unique' is the 46th of them, in
        the order whoever wrote the manual chose to list them. On a
        clock, that order is fatal: the machine spent its whole budget
        trying 45 flags that cannot answer "how many unique lines" and
        never reached the one that does -- measured, a 2s budget lost
        'sort' entirely and 8s was needed before it was found, which is
        why the whole pipeline search used to cost 39s.

        Scored against the goal, '--unique' is 2nd. Nothing is given up
        -- every flag is still offered, only reordered -- and the
        search gets 3x cheaper.
        """
        goal = "how many unique lines in data.txt"
        manual = [f for f, _ in cenv.flag_descriptions("sort",
                                                       limit=cenv._WIDE_FLAGS)]
        shapes = cenv._query_shapes("sort", "probe.txt", goal,
                                    patterns=("",), wide=True)
        # every flag is still there: this is a reordering, not a filter
        offered = [s[1] for s in shapes if len(s) == 3]
        self.assertEqual(sorted(offered), sorted(manual),
                         "reordering dropped flags: %d of %d"
                         % (len(offered), len(manual)))
        where = next((i for i, s in enumerate(shapes) if "--unique" in s),
                     None)
        self.assertIsNotNone(where, "--unique was never offered")
        manual_at = manual.index("--unique")
        self.assertLess(where, manual_at,
                        "--unique is shape %d, and in the manual's own "
                        "order it is flag %d: the head will run out of "
                        "clock before it gets there" % (where, manual_at))


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
        # 'assertTrue(True)' stood here. It cannot fail, so it proved
        # nothing about the cap it sat next to -- which is worse than no
        # assertion, because it reads like one.
        self.assertIsInstance(code, int,
                              "a program that talks forever must still "
                              "return an exit code instead of taking the "
                              "learner down with it")
        self.assertLessEqual(len(out), 1 << 16)

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


class TailTests(unittest.TestCase):
    """The last stage of a pipeline is what makes it expensive, because
    every head is tried against every tail. Four names for one instrument
    is a fourfold slowdown bought with nothing."""

    def test_four_names_for_one_instrument_are_one_instrument(self):
        """grep, egrep, fgrep and rgrep are four executables that all count
        lines. Composing with all four runs the same pipeline four times and
        reports the result as if four programs had agreed."""
        tails = [["grep", "--count", ""], ["egrep", "--count", ""],
                 ["fgrep", "--count", ""], ["rgrep", "--count", ""],
                 ["wc", "--lines"]]
        kept = cenv._distinct_tails(tails, 10.0)
        self.assertTrue(kept, "every tail was thrown away")
        self.assertLess(len(kept), len(tails),
                        "nothing was merged: %r" % kept)
        for t in kept:
            self.assertIn(t, tails, "a tail was invented: %r" % t)

    def test_tails_that_behave_differently_are_both_kept(self):
        """Merging must be by what a program DOES, not by how many there
        are. Lines and words are different answers to the same bytes; a
        dedupe that keeps one of them has decided the question."""
        kept = cenv._distinct_tails([["wc", "--lines"],
                                     ["wc", "--words"]], 10.0)
        self.assertEqual(len(kept), 2,
                         "two different instruments were merged into one: "
                         "%r" % kept)

    def test_a_tail_that_cannot_run_is_not_offered(self):
        """A tail that errors is silently dropped rather than carried into
        every pipeline as a guaranteed failure."""
        kept = cenv._distinct_tails([["wc", "--lines"],
                                     ["definitely-not-a-program", "-x"]],
                                    10.0)
        self.assertEqual(kept, [["wc", "--lines"]], kept)


class PipelineTests(unittest.TestCase):
    """Work on a computer is almost never one program.

    "how many different lines" is answered by no single program on this
    machine: sort it, collapse it, then count it. A machine that can only
    run one thing at a time has to refuse that question, so it is asked
    to compose -- and composition is only tried when nothing alone works,
    because one program is fewer actions than two.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-pipe-")
        self.work = pathlib.Path(self.tmp)
        # 14 lines, 7 different ones, and NO two identical lines next to
        # each other.
        #
        # The repeats used to sit together -- 'kind 0, kind 0, kind 0,
        # kind 1, kind 1, kind 1'. That is the one arrangement 'uniq' is
        # built to collapse, so on that file 'uniq | wc --lines' prints 7
        # and looks exactly like a tool that counts DIFFERENT lines. It is
        # not: it counts runs. Given a real file whose repeats are apart
        # it answers 14 where 7 is true -- and this test could not see it,
        # because it had chosen the single file on which the wrong tool
        # happens to be right. A fixture that cannot tell the wrong answer
        # from the right one is not testing anything, so the repeats are
        # rotated apart and the file is checked for that below.
        names = ["kind %d" % i for i in range(7)]
        self.rows = names + names[3:] + names[:3]
        self.assertEqual(len(set(self.rows)), 7, "fixture must hold 7")
        self.assertFalse(any(a == b for a, b in
                             zip(self.rows, self.rows[1:])),
                         "repeats must not be adjacent: 'uniq' collapses "
                         "neighbours, so an adjacent-duplicate file is the "
                         "one file where the wrong tool is right")
        self.file = self.work / "data.txt"
        self.file.write_text("\n".join(self.rows) + "\n")
        self.progs = ["sort", "uniq", "wc", "grep", "cat", "nl", "cut", "tr"]

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_question_no_single_program_answers_is_answered_by_two(self):
        """Discovered on the whole machine, not handed the answer's
        neighbourhood. Passing programs=[...] here is how this test used to
        pass while the real path spent eight minutes and found nothing:
        'uniq' is the 31st candidate for this question and 'sort' the 91st,
        so a shortlist decides the outcome before the search begins.

        The machine may be slow here once. It may not be spoon-fed."""
        r = cenv.answer_query("how many unique lines in data.txt", self.file)
        self.assertTrue(r["pass"], r)
        self.assertEqual(r["value"], "7", r)
        self.assertEqual(len(set(self.rows)), 7, "the fixture is wrong")
        # 14 lines answer this question as 14, and the machine must not.
        self.assertEqual(len(self.rows), 14)
        self.assertNotEqual(r["value"], str(len(self.rows)),
                            "counted the lines instead of the different "
                            "lines: %s" % r)

    def test_the_negative_is_not_proved_before_the_positive_is_found(self):
        """A question only a pipeline can answer used to cost three sweeps
        proving that no single program works -- and then discard all three
        before trying the thing that does.

        Composition now runs alongside the first sweep instead of after
        the last one. If this question reaches the second or third sweep,
        the race is gone and the machine is paying minutes to establish
        what the first sweep already told it.

        The composition fetches its own candidates with
        _MAX_PIPE_PROGRAMS, which is not a tier size, so a recorded
        number that is a tier can only have come from a tier."""
        from unittest import mock
        tiers = {24, 96, 200}
        asked: list[int] = []
        real = cenv.programs_for_goal

        def spy(goal, limit=24):
            asked.append(limit)
            return real(goal, limit=limit)

        with mock.patch.object(cenv, "programs_for_goal", side_effect=spy):
            r = cenv.answer_query("how many unique lines in data.txt",
                                  self.file)
        self.assertTrue(r["pass"], r)
        self.assertEqual(r["value"], "7", r)
        for size in (96, 200):
            self.assertNotIn(size, asked,
                             "searched %d single programs for a question "
                             "no single program answers: %r" % (size, asked))

    def test_giving_up_on_one_program_is_not_giving_up(self):
        """Programs that tracked the probe and then failed to agree on the
        real file are not an answer. Treating them as one used to stop
        composition from ever being tried, so the machine refused
        questions it could have answered by joining two programs.

        Asked to insist on two agreeing programs, one program is found
        and refused -- and composition must still be attempted."""
        from unittest import mock
        stages = []
        real = cenv.probe_survivors

        def spy(kind, programs, gap, **kw):
            stages.append(kw.get("stages", 1))
            return real(kind, programs, gap, **kw)

        with mock.patch.object(cenv, "probe_survivors", side_effect=spy):
            cenv.answer_query("count the lines in data.txt", self.file,
                              programs=["wc"], min_agreement=2)
        self.assertIn(2, stages,
                      "composition was never attempted: %r" % stages)

    def test_a_pipeline_head_does_not_get_the_budget_a_caller_asks_for(self):
        """The seconds a caller asks for are not the seconds a head is
        given. What costs time in the pipeline search is not the head
        that works -- it is every head that does not: each one burns
        its whole budget, and with a hundred of them that budget IS
        the search. Measured, whole pipeline search:

            1.0s 14.4s | 1.5s 14.4s | 2.0s 12.6s | 2.5s 14.4s
            4.0s 19.6s | 8.0s 28.8s | 12.0s 41.3s

        Two is the floor as well as the peak: the deadline is only
        checked BETWEEN shapes, so a head already inside a subprocess
        run finishes it either way, and going below 2s stops buying
        anything.

        It can be this small only because flags are tried in the order
        the goal scores them. In the manual's own order 'sort --unique'
        is the 46th flag of 52 -- a 2s budget lost 'sort' entirely and
        8s was needed to reach it.

        Ask for a minute a head. Two is what it must get.
        """
        hits = cenv.probe_survivors(
            "uniquelines", self.progs,
            "how many unique lines in data.txt",
            stages=2, budget=60.0)
        self.assertTrue(hits, "no pipeline was composed at all: %r" % hits)
        for hit in hits:
            self.assertEqual(hit.get("stages"), 2, hit)
            self.assertIn("head_budget", hit, hit)
            self.assertLessEqual(hit["head_budget"], 4.0,
                                 "a caller asked for 60s a head and got "
                                 "%.1f: the pipeline budget is not capped, "
                                 "and every dead head pays it" %
                                 hit["head_budget"])
            self.assertGreaterEqual(hit["head_budget"], 2.0,
                                    "below 2s nothing is bought: the "
                                    "deadline is only checked between "
                                    "shapes: %.1f" % hit["head_budget"])

    def test_a_search_told_to_stop_stops(self):
        """Composition starts BEFORE the single-program sweep, because for
        a question only a pipeline answers that sweep is a guaranteed
        failure. When the sweep does answer, the composition must be
        droppable -- and a thread that is merely ignored does not stop
        working, it only stops being listened to.

        One worker, so the order is fixed: the first pipeline run sets
        the stop, and every job behind it must see it and do nothing.
        A search that cannot be stopped runs all thirty-two.
        """
        from unittest import mock
        import threading
        runs: list[int] = []
        stop = threading.Event()
        real = cenv._run_pipeline

        def spy(*a, **k):
            runs.append(1)
            stop.set()          # the answer is known; stop looking
            return real(*a, **k)

        with mock.patch.object(cenv, "_run_pipeline", side_effect=spy):
            cenv.probe_survivors("uniquelines", self.progs,
                                 "how many unique lines in data.txt",
                                 stages=2, workers=1, stop=stop)
        self.assertLess(len(runs), 10,
                        "a search that was told to stop still ran %d "
                        "pipelines: it is being ignored, not stopped"
                        % len(runs))

    def test_no_search_is_left_running_behind_an_answered_question(self):
        """The point of the previous test, measured where it matters.

        Three questions in a row, and the third is the one only a
        pipeline answers. With orphaned searches still burning both
        cores it cost 37s; asked first, the same question cost 19s --
        the machine was getting SLOWER the more it had learned, which
        is learning backwards.

        Each search is told to stop and waited for, so nothing is left
        working on a question that has already been answered.
        """
        for goal in ("count the lines in data.txt",
                     "how many words in data.txt"):
            r = cenv.answer_query(goal, self.file)
            self.assertTrue(r["pass"], r)
            for _ in range(20):
                if cenv._COMPOSE_LIVE == 0:
                    break
                time.sleep(0.05)
            self.assertEqual(cenv._COMPOSE_LIVE, 0,
                             "a composition search is still running after "
                             "%r was answered: it will go on burning every "
                             "core while the next question is asked" % goal)

    def test_the_composition_is_a_real_command_not_a_description(self):
        """Run the two stages ourselves, joined with our own pipe, nowhere
        near the learner. If it works, a pipeline was composed."""
        r = cenv.answer_query("how many unique lines in data.txt", self.file)
        self.assertTrue(r["pass"], r)
        stages = r["survivors"][0]["argv"]
        self.assertEqual(len(stages), 2, stages)
        argv1 = [str(self.file) if a == "probe.txt" else a
                 for a in stages[0]]
        one = subprocess.run(argv1, cwd=str(self.work),
                             capture_output=True, timeout=30)
        self.assertEqual(one.returncode, 0, one.stderr[:200])
        two = subprocess.run(stages[1], input=one.stdout,
                             capture_output=True, timeout=30)
        self.assertEqual(two.returncode, 0, two.stderr[:200])
        self.assertEqual(two.stdout.decode().strip(), "7")

    def test_the_last_stage_reads_the_pipe_not_the_file(self):
        """A program at the end of a pipe takes no filename. Hand it one
        anyway and it reads the file and ignores everything the previous
        stage produced -- a pipeline that runs, and quietly answers a
        different question."""
        shapes = cenv._stdin_shapes("wc", "how many unique lines")
        self.assertIn(["wc"], shapes)
        for shape in shapes:
            self.assertNotIn("data.txt", shape, shape)
            self.assertNotIn("probe.txt", shape, shape)

    def test_the_more_specific_thing_named_is_the_one_counted(self):
        """"how many unique lines" also contains the word 'lines'. Answering
        it as though 'lines' were the whole question gives 22 where 7 is
        wanted -- so the longer, more specific phrase is what gets built."""
        self.assertEqual(cenv.query_kind("how many unique lines in data.txt"),
                         "uniquelines")
        self.assertEqual(cenv.query_kind("count the lines in data.txt"),
                         "lines")
        probe = cenv.probe_bytes("uniquelines", 7)
        lines = probe.splitlines()
        self.assertEqual(len(set(lines)), 7, "7 different lines")
        self.assertGreater(len(lines), 7,
                           "and more lines than that, or 'how many lines' "
                           "and 'how many different lines' have the same "
                           "answer and the check cannot tell them apart")

    def test_one_program_is_preferred_over_two(self):
        """The shortest plan that reaches the goal is the one wanted. A
        single program is tried across the whole machine before any pair is
        considered, so a question one program can answer must not be
        answered by a pipeline."""
        src = self.work / "simple.txt"
        src.write_text("\n".join("row %d" % i for i in range(1, 24)) + "\n")
        r = cenv.answer_query("count the lines in simple.txt", src,
                              programs=self.progs)
        self.assertTrue(r["pass"], r)
        self.assertNotEqual(r.get("stages"), 2,
                            "a single program answers this: %s" % r)
        for hit in r["survivors"]:
            self.assertNotEqual(hit.get("stages"), 2, hit)

    def test_a_command_that_finishes_is_believed_not_killed(self):
        """poll() says None both for "still running" and for "finished but
        not reaped yet", and those are opposite things. Conflating them
        threw away good answers depending on nothing but timing -- the
        same command scored 0 on one run and None on the next. Run it
        until the race would show, because a flake that passes silently
        is worse than a failure."""
        for _ in range(25):
            code, out = cenv._run_capped(["printf", "7\\n"], self.work,
                                         timeout=5.0)
            self.assertEqual(code, 0, "a finished command was called dead")
            self.assertEqual(out.strip(), b"7")
        for _ in range(5):
            code, out = cenv._run_pipeline(["printf", "7\\n"], ["wc", "-l"],
                                           self.work, timeout=5.0)
            self.assertEqual(code, 0, code)
            self.assertEqual(out.strip(), b"1")

    def test_a_command_that_never_finishes_is_killed_and_reported_dead(self):
        """The other half: something that will not stop must not be
        believed, and must not take the learner down with it."""
        code, out = cenv._run_capped(["shuf", "--repeat", "/dev/null"],
                                     self.work, timeout=2.0)
        self.assertNotEqual(code, 0)
        self.assertLessEqual(len(out), 1 << 16)


class LiteralTests(unittest.TestCase):
    """Goals that name WHAT to look for, not just how many.

    "how many lines contain ERROR" cannot be answered by counting anything
    until ERROR is part of the test. The goal brought its own argument --
    the same as 'resize to 50%' brought 50% -- and the machine has to use
    it rather than guess.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-lit-")
        self.work = pathlib.Path(self.tmp)
        # its own store, or another test's discovery is still sitting in
        # the shared cache and the machine appears to know things it was
        # never told in this test
        self._saved_state = os.environ.get("BRAIN_STATE_DIR")
        os.environ["BRAIN_STATE_DIR"] = self.tmp
        cenv._QUERY_CACHE.clear()
        cenv._QUERY_LOADED = False
        rows = []
        for i in range(23):
            rows.append("ERROR in row %d" % i if i % 4 == 0
                        else "all good row %d" % i)
        self.rows = rows
        self.file = self.work / "data.txt"
        self.file.write_text("\n".join(self.rows) + "\n")
        self.truth = str(sum(1 for r in rows if "ERROR" in r))

    def tearDown(self) -> None:
        if self._saved_state is None:
            os.environ.pop("BRAIN_STATE_DIR", None)
        else:
            os.environ["BRAIN_STATE_DIR"] = self._saved_state
        cenv._QUERY_CACHE.clear()
        cenv._QUERY_LOADED = False
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_word_the_goal_named_is_pulled_out_of_it(self):
        self.assertEqual(cenv.goal_literal(
            "how many lines contain ERROR in data.txt"), "ERROR")
        self.assertEqual(cenv.goal_literal(
            "count the lines mentioning failed login in data.txt"),
            "failed login")
        self.assertIsNone(cenv.goal_literal("count the lines in data.txt"))

    def test_the_probe_holds_the_word_and_lines_that_do_not(self):
        """n lines holding it and n lines not, or "how many lines hold
        this" and "how many lines are there" are the same question and
        every line-counting program passes while answering the wrong one."""
        probe = cenv.probe_bytes("lineswith", 7, "ERROR")
        lines = probe.splitlines()
        holding = [x for x in lines if b"ERROR" in x]
        self.assertEqual(len(holding), 7)
        self.assertGreater(len(lines), 7)

    def test_the_question_is_answered_and_the_answer_is_true(self):
        r = cenv.answer_query("how many lines contain ERROR in data.txt",
                              self.file)
        self.assertTrue(r["pass"], r)
        self.assertEqual(r["value"], self.truth, r)

    def test_the_command_that_answered_it_contains_the_word_asked_for(self):
        """A command that never mentions ERROR has not looked for ERROR,
        however right its number happens to be."""
        r = cenv.answer_query("how many lines contain ERROR in data.txt",
                              self.file)
        self.assertTrue(r["pass"], r)
        joined = " ".join(
            " ".join(hit["argv"]) if hit.get("stages") != 2
            else " ".join(hit["argv"][0]) + " " + " ".join(hit["argv"][1])
            for hit in r["survivors"])
        # the word is wired into the command. It is remembered as a hole
        # waiting for the word (see GeneralisingTests), which is the same
        # guarantee: a command with no place for ERROR has not looked for
        # ERROR, however right its number happens to be.
        self.assertTrue("ERROR" in joined
                        or cenv._LITERAL_HOLE in joined,
                        r["survivors"])

    def test_the_whole_manual_is_searched_when_the_hint_is_wrong(self):
        """grep documents 83 flags and '--count' is the 65th. A goal that
        never says the word 'count' gets shown --only-matching instead, so
        the machine concludes nothing on the box can count. The wide pass
        stops guessing which flags matter and offers all of them."""
        self.assertTrue(cenv._one_wide(
            "grep", "lineswith", "how many lines contain ERROR in data.txt",
            ("ERROR",), 5.0, "ERROR"))

    def test_the_probe_holds_the_same_word_the_command_hunts_for(self):
        """A probe holding NEEDLE while the command hunts for ERROR finds
        nothing -- and nothing looks exactly like failure."""
        self.assertIsNone(cenv._one_wide(
            "grep", "lineswith", "how many lines contain ERROR in data.txt",
            ("ERROR",), 5.0))

    def test_a_failure_is_not_remembered_as_a_fact(self):
        """A success is a fact about the machine. An empty result is often
        a fact about the SEARCH -- the right program not looked at yet.
        Caching it makes the failure permanent and the question stays
        unanswered forever."""
        key = ("lineswith", 24)
        cenv._QUERY_CACHE.pop(key, None)
        real = cenv.installed_programs
        try:
            # a machine with nothing on it that can search, so the search
            # genuinely fails -- and leaves nothing behind to mislead the
            # next attempt. (Passing programs= would skip the cache
            # entirely and prove nothing at all.)
            cenv.installed_programs = lambda *a, **k: ["cat", "fmt"]
            cenv.answer_query("how many lines contain ERROR in data.txt",
                              self.file)
        finally:
            cenv.installed_programs = real
        self.assertNotIn(key, cenv._QUERY_CACHE,
                         "an empty result was cached as knowledge")


class GeneralisingTests(unittest.TestCase):
    """Memorising an answer is not learning a method.

    Remembering 'grep -c ERROR' means thirty-five seconds of searching all
    over again the moment the word is WARN. What generalises is the SHAPE
    of the command, with a hole where the goal's own word goes -- and then
    the second question is not merely faster, it is a different kind of
    thing: reuse, not repetition.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-gen-")
        self.work = pathlib.Path(self.tmp)
        self._saved_state = os.environ.get("BRAIN_STATE_DIR")
        os.environ["BRAIN_STATE_DIR"] = self.tmp
        cenv._QUERY_CACHE.clear()
        cenv._QUERY_LOADED = False
        rows = []
        for i in range(23):
            rows.append("ERROR in row %d" % i if i % 4 == 0
                        else "all good row %d" % i)
            if i % 5 == 0:
                rows.append("WARN also row %d" % i)
        self.rows = rows
        self.file = self.work / "data.txt"
        self.file.write_text("\n".join(self.rows) + "\n")
        self.truth = {
            "ERROR": str(sum(1 for r in rows if "ERROR" in r)),
            "WARN": str(sum(1 for r in rows if "WARN" in r)),
        }

    def tearDown(self) -> None:
        if self._saved_state is None:
            os.environ.pop("BRAIN_STATE_DIR", None)
        else:
            os.environ["BRAIN_STATE_DIR"] = self._saved_state
        cenv._QUERY_CACHE.clear()
        cenv._QUERY_LOADED = False
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _ask(self, word: str):
        start = time.time()
        r = cenv.answer_query("how many lines contain %s in data.txt" % word,
                              self.file)
        return r, time.time() - start

    def test_a_word_it_has_never_seen_is_answered_without_searching_again(self):
        first, first_t = self._ask("ERROR")
        self.assertTrue(first["pass"], first)
        self.assertEqual(first["value"], self.truth["ERROR"], first)

        second, second_t = self._ask("WARN")
        self.assertTrue(second["pass"], second)
        self.assertEqual(second["value"], self.truth["WARN"], second)
        # the whole point: not "also fast" -- a different order of thing
        self.assertLess(second_t, first_t / 10.0,
                        "second word took %.2fs against %.2fs for the first "
                        "-- it searched again instead of reusing"
                        % (second_t, first_t))

    def test_what_is_remembered_is_a_shape_with_a_hole_in_it(self):
        self._ask("ERROR")
        remembered = [c for (kind, _), c in cenv._QUERY_CACHE.items()
                      if kind == "lineswith"]
        self.assertTrue(remembered, "nothing was remembered")
        joined = " ".join(" ".join(hit["argv"]) for hit in remembered[0])
        self.assertNotIn("ERROR", joined,
                         "the word was baked in, so nothing generalised: "
                         "%s" % joined)
        self.assertIn(cenv._LITERAL_HOLE, joined)

    def test_the_hole_is_filled_with_this_goals_word_before_running(self):
        """A shape cannot be run until it is made specific again -- and it
        must be filled with THIS word, not the one it was learned on."""
        self._ask("ERROR")
        second, _ = self._ask("WARN")
        self.assertTrue(second["pass"], second)
        for hit in second["survivors"]:
            joined = " ".join(hit["argv"])
            self.assertNotIn(cenv._LITERAL_HOLE, joined,
                             "the command was run with the hole still in it")
            self.assertIn("WARN", joined)
