#!/usr/bin/env python3
"""A plan that is never run is not a capability.

The composer could find chains of capabilities for years and prove nothing:
``plan()`` had no callers outside its own tests. These tests drive a sentence
all the way through to a file on disk, because the only evidence a chain
worked is the artifact it produced.

Everything here runs against the real registry and the real adapters.
A sabotaged link in the chain must fail these tests.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import tempfile
import unittest

from canonical.runtime import composer_route_v1 as croute
from canonical.runtime import curriculum_v1
from canonical.runtime import documentation_mining_v1
from canonical.runtime import program_synthesis_v1
from canonical.runtime import transfer_learning_v1

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRATCH = ROOT / "canonical" / "astra_runtime" / "state" / "composer_route_scratch"


class ScratchCase(unittest.TestCase):
    """Real writes into a real directory, cleaned up after."""

    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(SCRATCH, ignore_errors=True)

    def path_in(self, name: str) -> str:
        return str(SCRATCH.relative_to(ROOT) / name)

    def abs_path(self, name: str) -> pathlib.Path:
        return SCRATCH / name


# --------------------------------------------------------------------------- #
# reading a sentence as a typed goal
# --------------------------------------------------------------------------- #
class RoutingTests(unittest.TestCase):
    def test_writing_and_extracting_are_not_confused(self):
        """Both sentences contain the word 'text'. Only one asks to write.

        Stripping verbs as stopwords makes these the same sentence.
        """
        write_token = croute.route("write the text hello to out.txt").get("token")
        read_token = croute.route("extract text from a pdf file").get("token")
        self.assertNotEqual(write_token, read_token,
                            "both sentences share the word 'text' and were "
                            "routed to the same capability")
        self.assertEqual(write_token, "text.file.available")
        self.assertEqual(read_token, "pdf.extract.text")

    def test_the_router_says_which_token_it_read_the_goal_as(self):
        r = croute.route("write the text hello to out.txt")
        self.assertTrue(r["pass"], r)
        self.assertEqual(r["token"], "text.file.available")

    def test_an_unreachable_goal_is_reported_not_guessed(self):
        r = croute.route("xyzzy plugh frobnicate nothing at all here")
        self.assertFalse(r["pass"])
        self.assertEqual(r["status"], "OPEN__COMPOSER_NO_REACHABLE_TOKEN")

    def test_every_candidate_tried_is_reported(self):
        r = croute.route("write the text hello to out.txt")
        self.assertTrue(r["tried"], "the router must show its working")
        for row in r["tried"]:
            self.assertIn("token", row)
            self.assertIn("reachable", row)

    def test_the_content_is_not_the_filename(self):
        """The destination is not the payload."""
        self.assertEqual(croute.extract_content("write the text hello to out.txt"),
                         "hello")
        self.assertEqual(croute.extract_content("write the text goodbye into b.txt"),
                         "goodbye")

    def test_a_filename_anywhere_in_the_sentence_is_found(self):
        """The surface's own parser is anchored to the start and finds none
        of these, because the first word is a verb."""
        self.assertEqual(croute.extract_paths("compress notes.txt into out.gz"),
                         ["notes.txt", "out.gz"])


# --------------------------------------------------------------------------- #
# running the chain
# --------------------------------------------------------------------------- #
class ExecutionTests(ScratchCase):
    def test_a_goal_is_closed_by_a_chain_that_really_runs(self):
        goal = "write the text hello to " + self.path_in("a.txt")
        r = croute.route(goal)
        self.assertTrue(r["pass"], r)
        x = croute.execute_chain(r["chain"], goal)
        self.assertTrue(x["pass"], x)
        self.assertEqual(x["status"], "PASS__COMPOSER_CHAIN_EXECUTED")

    def test_the_file_really_exists_with_the_content_the_goal_asked_for(self):
        goal = "write the text hello to " + self.path_in("a.txt")
        x = croute.execute_chain(croute.route(goal)["chain"], goal)
        self.assertTrue(x["pass"], x)
        self.assertTrue(self.abs_path("a.txt").is_file())
        self.assertEqual(self.abs_path("a.txt").read_text(encoding="utf-8"),
                         "hello")

    def test_two_different_goals_produce_two_different_files(self):
        for word, name in (("hello", "a.txt"), ("goodbye", "b.txt")):
            goal = "write the text %s to %s" % (word, self.path_in(name))
            x = croute.execute_chain(croute.route(goal)["chain"], goal)
            self.assertTrue(x["pass"], x)
        self.assertEqual(self.abs_path("a.txt").read_text(), "hello")
        self.assertEqual(self.abs_path("b.txt").read_text(), "goodbye")

    def test_the_step_reports_the_arguments_it_actually_used(self):
        goal = "write the text hello to " + self.path_in("a.txt")
        x = croute.execute_chain(croute.route(goal)["chain"], goal)
        self.assertEqual(len(x["steps"]), 1)
        self.assertEqual(x["steps"][0]["args"]["content"], "hello")
        self.assertEqual(x["steps"][0]["capability_id"], "text.file.write")

    def test_a_capability_that_cannot_run_says_so_instead_of_pretending(self):
        """Nothing on this machine can open a pdf. The chain must fail."""
        goal = "extract text from " + self.path_in("nope.pdf")
        r = croute.route(goal)
        self.assertTrue(r["pass"], r)
        x = croute.execute_chain(r["chain"], goal)
        self.assertFalse(x["pass"])
        self.assertEqual(x["status"], "FAIL__COMPOSER_STEP_RAISED")
        self.assertIn("failed_step", x)

    def test_an_unfillable_slot_is_reported_not_secretly_skipped(self):
        """A chain run with a slot left empty is a chain that did nothing."""
        x = croute.execute_chain(["text.file.write"], "a goal with no path or words")
        self.assertFalse(x["pass"])
        self.assertEqual(x["status"], "OPEN__COMPOSER_SLOT_UNBOUND")
        self.assertTrue(x["failed_step"]["missing_slots"])

    def test_a_file_path_is_not_inferred_as_string_content(self):
        """A write-only adapter must not claim it summarized a source file."""
        goal = "summarize notes.txt into three sentences and save to summary.txt"
        x = croute.execute_chain(["text.file.write"], goal)
        self.assertFalse(x["pass"], x)
        self.assertEqual(x["status"], "OPEN__COMPOSER_SLOT_UNBOUND")
        self.assertIn("content", x["failed_step"]["missing_slots"])

    def test_a_capability_not_in_the_registry_is_a_closed_failure(self):
        x = croute.execute_chain(["no.such.capability"], "write the text hi to a.txt")
        self.assertFalse(x["pass"])
        self.assertEqual(x["status"], "FAIL__COMPOSER_STEP_NOT_IN_REGISTRY")

    def test_nothing_lands_outside_the_repository(self):
        goal = "write the text hello to ../../escaped.txt"
        x = croute.execute_chain(croute.route(goal)["chain"], goal)
        self.assertFalse(x["pass"], "escaping the repository must be refused")
        self.assertFalse((ROOT.parent / "escaped.txt").exists())


# --------------------------------------------------------------------------- #
# reachable from the live router
# --------------------------------------------------------------------------- #
class SolveIntegrationTests(ScratchCase):
    def test_solve_closes_a_goal_by_composing(self):
        from canonical.runtime import live_brain_route_admission_v1 as ra

        goal = "write the text hello to " + self.path_in("solved.txt")
        r = ra.solve({"task_id": "t", "goal": goal})
        self.assertTrue(r.get("pass"), r.get("status"))
        self.assertEqual(r.get("status"), "PASS__COMPOSED_CAPABILITY_CHAIN")

    def test_the_file_solve_promised_is_the_file_that_exists(self):
        from canonical.runtime import live_brain_route_admission_v1 as ra

        goal = "write the text hello to " + self.path_in("solved.txt")
        r = ra.solve({"task_id": "t", "goal": goal})
        self.assertTrue(r.get("pass"), r)
        self.assertTrue(self.abs_path("solved.txt").is_file())
        self.assertEqual(self.abs_path("solved.txt").read_text(), "hello")

    def test_composition_reports_what_it_superseded(self):
        from canonical.runtime import live_brain_route_admission_v1 as ra

        goal = "write the text hello to " + self.path_in("solved.txt")
        r = ra.solve({"task_id": "t", "goal": goal})
        self.assertTrue(r.get("pass"), r)
        self.assertIn("supersedes", r)
        self.assertTrue(r["supersedes"]["promised_artifact_errors"])


if __name__ == "__main__":
    unittest.main()


# --------------------------------------------------------------------------- #
# the last resort: nothing registered, nothing in a table, nothing documented
# --------------------------------------------------------------------------- #
class DiscoveryFallbackTests(unittest.TestCase):
    """Every earlier fallback is given something. This one is given only a
    directory to act in, so it is the one that still works when the format
    was never written down anywhere."""

    def setUp(self) -> None:
        from canonical.runtime import (curriculum_v1,
                                       documentation_mining_v1,
                                       program_synthesis_v1,
                                       transfer_learning_v1)
        self.tmp = tempfile.mkdtemp(prefix="brain-route-discover-")
        self.mods = (curriculum_v1, documentation_mining_v1,
                     program_synthesis_v1, transfer_learning_v1)
        # STATE_PATH is bound at import time, so patch the attribute. A test
        # that writes into the repository's real memory is not a test.
        self.saved = [m.STATE_PATH for m in self.mods]
        for m in self.mods:
            m.STATE_PATH = os.path.join(self.tmp, type(m).__name__ + ".json")
        # remove the format from the hand-written table so the only way left
        # is to find out by acting
        self.table = dict(program_synthesis_v1.CANDIDATES)
        for key in (".gz", ".bz2"):
            program_synthesis_v1.CANDIDATES.pop(key, None)

    def tearDown(self) -> None:
        program_synthesis_v1.CANDIDATES.clear()
        program_synthesis_v1.CANDIDATES.update(self.table)
        for m, path in zip(self.mods, self.saved):
            m.STATE_PATH = path
        shutil.rmtree(self.tmp, ignore_errors=True)

    def route(self, goal: str) -> dict:
        # seed=[] -- with nothing to compose from, no registered chain is
        # reachable, so reaching the goal means it was actually discovered
        return croute.route(goal, seed=[])

    def test_a_format_no_table_knows_is_still_reached(self):
        r = self.route("compress the input into out.gz")
        self.assertTrue(r["pass"], r)
        self.assertEqual(r["status"], "PASS__DISCOVERED_BY_ACTING")

    def test_what_is_discovered_is_a_real_plan_not_a_guess(self):
        r = self.route("compress the input into out.gz")
        self.assertTrue(r["pass"], r)
        self.assertEqual(r.get("plan"), ["run_gzip"],
                         "the plan must name the program that worked")

    def test_a_different_format_discovers_a_different_program(self):
        gz = self.route("compress the input into out.gz")
        bz2 = self.route("make a bzip2 archive out.bz2 from the input")
        self.assertTrue(gz["pass"] and bz2["pass"])
        self.assertEqual(bz2.get("plan"), ["run_bzip2"])
        self.assertNotEqual(gz.get("plan"), bz2.get("plan"))

    def test_it_really_tried_programs_rather_than_naming_one(self):
        r = self.route("compress the input into out.gz")
        self.assertGreater(r.get("actions_tried", 0), 1,
                           "a single candidate is a guess, not a search")

    def test_the_second_ask_is_answered_from_memory(self):
        first = self.route("compress the input into out.gz")
        second = self.route("compress the input into out.gz")
        self.assertTrue(first["pass"] and second["pass"])
        self.assertEqual(first.get("plan"), second.get("plan"))

    def test_discovery_is_the_last_resort_not_the_first(self):
        """When a table does know the format, acting is never reached --
        it is the slowest way to learn what is already written down."""
        from canonical.runtime import program_synthesis_v1 as synth
        synth.CANDIDATES.clear()
        synth.CANDIDATES.update(self.table)
        r = croute.route("compress the input into out.gz", seed=[])
        self.assertTrue(r["pass"], r)
        self.assertNotEqual(r["status"], "PASS__DISCOVERED_BY_ACTING")


class PerformedTests(unittest.TestCase):
    """A sentence naming a real file must leave a real file behind.

    Discovering which program could do the job is knowledge. The goal asked
    for the job.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="brain-performed-")
        self.work = pathlib.Path(self.tmp) / "work"
        self.work.mkdir()
        (self.work / "notes.txt").write_bytes(b"real content\n" * 200)
        mods = (curriculum_v1, documentation_mining_v1,
                program_synthesis_v1, transfer_learning_v1)
        self.mods = mods
        self.saved = [m.STATE_PATH for m in mods]
        for m in mods:
            m.STATE_PATH = os.path.join(self.tmp, type(m).__name__ + ".json")
        self.table = dict(program_synthesis_v1.CANDIDATES)
        for key in (".gz", ".bz2", ".zip"):
            program_synthesis_v1.CANDIDATES.pop(key, None)

    def tearDown(self) -> None:
        program_synthesis_v1.CANDIDATES.clear()
        program_synthesis_v1.CANDIDATES.update(self.table)
        for m, path in zip(self.mods, self.saved):
            m.STATE_PATH = path
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_sentence_about_a_real_file_actually_does_it(self):
        r = croute.route("compress notes.txt into notes.txt.gz", seed=[],
                         cwd=str(self.work))
        self.assertTrue(r["pass"], r)
        self.assertEqual(r["status"], "PASS__PERFORMED_ON_REAL_FILE")
        self.assertTrue((self.work / "notes.txt.gz").is_file(),
                        "the file was not left behind")

    def test_what_is_left_behind_really_is_that_format(self):
        r = croute.route("compress notes.txt into notes.txt.gz", seed=[],
                         cwd=str(self.work))
        self.assertTrue(r["pass"], r)
        import gzip
        self.assertEqual(
            gzip.decompress((self.work / "notes.txt.gz").read_bytes()),
            (self.work / "notes.txt").read_bytes())

    def test_a_job_named_in_a_zip_is_done_with_zip(self):
        r = croute.route("archive notes.txt into notes.txt.zip", seed=[],
                         cwd=str(self.work))
        self.assertTrue(r["pass"], r)
        import zipfile
        with zipfile.ZipFile(self.work / "notes.txt.zip") as z:
            self.assertEqual(z.read("notes.txt"),
                             (self.work / "notes.txt").read_bytes())

    def test_a_goal_naming_a_file_that_is_not_there_is_not_performed(self):
        r = croute.route("compress absent.txt into absent.txt.gz", seed=[],
                         cwd=str(self.work))
        self.assertFalse((self.work / "absent.txt.gz").exists(),
                         "it invented an input to look capable")
