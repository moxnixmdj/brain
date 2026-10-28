# PROJECT_BRAIN
"""A route must be IDENTIFIED by the sentence, not merely REACHABLE from it.

The 43-act probe found nine sentences answered by a capability that had no business
answering them; five of the nine were routed to `document.convert.markdown_pdf` on the
single word "report", and when no token produced a chain the fallback recalled a learned
program by output file suffix alone -- `json_dump` "verified" for "Fuzz the function add".

These pins nail the three laws that closed it, and the two directions that must not
regress while it is closed: a real format write must still route, and a real format write
must still be recalled from memory the second time.

Run: python -m pytest canonical/tests/test_a_route_must_be_identified_not_merely_reachable_v1.py -q
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import composer_route_v1 as route
from canonical.runtime import program_synthesis_v1 as synthesis


class RouteIdentificationTests(unittest.TestCase):
    """An artefact word, a medium word, a request verb or a version stamp is not the act."""

    NOT_IDENTIFIED = [
        "Fuzz the function add in pkg/calc.py and report it to out/fuzz.json.",
        "Build a wheel for the project in repo and report it to out/build.json.",
        "Add logging and metrics to pkg/calc.py and report it to out/obs.json.",
        "Inline the function sub in pkg/calc.py and report it to out/inline.json.",
        "Add the dependency requests to the project in repo and report it to out/deps.json.",
    ]

    def test_no_chain_is_accepted_for_an_act_nothing_owns(self):
        for goal in self.NOT_IDENTIFIED:
            result = route.route(goal, max_candidates=3)
            self.assertFalse(
                result.get("pass") and result.get("chain"),
                "a chain was accepted for %r: %r" % (goal, result.get("chain")))

    def test_an_artefact_word_alone_never_identifies_a_token(self):
        # `report` is a keyword of the markdown-to-pdf producer, and every sentence in this
        # repository ends "and report it to <O>".
        self.assertFalse(route.is_identified(
            "Fuzz the function add in pkg/calc.py and report it to out.json.",
            "document.convert.markdown_pdf"))

    def test_a_version_stamp_and_a_request_verb_are_not_evidence(self):
        # "run <unknown-capability-id>" was admitted to python.test.measurement.objective on
        # the two "content" words `run` and `v1`.
        self.assertFalse(route.is_identified(
            "run brain.module.function.invoke_renamed.py.auto.v1",
            "python.test.measurement.objective"))

    def test_a_sentence_writing_text_is_still_identified(self):
        self.assertTrue(route.is_identified(
            "Write the text 'hello patch' to out/note.txt.", "text.file.available"))


class SynthesisMayOnlyAnswerAFormatWriteTests(unittest.TestCase):

    def setUp(self):
        self._old_state = synthesis.STATE_PATH
        self.state = Path(tempfile.mkdtemp(prefix="synth_pin_")) / "state.json"
        synthesis.STATE_PATH = str(self.state)
        self.addCleanup(setattr, synthesis, "STATE_PATH", self._old_state)

    def test_a_request_to_fuzz_is_refused_and_names_the_act(self):
        result = synthesis.synthesize_or_recall(
            "Fuzz the function add in pkg/calc.py and report it to out/fuzz.json.")
        self.assertFalse(result.get("pass"))
        self.assertEqual(result.get("status"), "REFUSED__NOT_A_FORMAT_WRITE")
        self.assertIn("fuzz", result.get("reason", ""))
        self.assertFalse(self.state.exists(), "a refusal must not remember anything")

    def test_a_real_format_write_is_still_answered_and_still_remembered(self):
        first = synthesis.synthesize_or_recall("compress the report into out.gz")
        self.assertTrue(first.get("pass"), first)
        self.assertFalse(first.get("from_memory"))
        second = synthesis.synthesize_or_recall("compress the report into out.gz")
        self.assertTrue(second.get("from_memory"), second)
        self.assertEqual(second.get("status"), "PASS__RECALLED_VERIFIED_PROGRAM")

    def test_recall_does_not_answer_an_unrelated_job_with_the_same_suffix(self):
        synthesis.synthesize_or_recall("compress the report into out.gz")
        # same format, different act: the remembered gzip writer must not be claimed
        self.assertIsNone(synthesis.recall(".gz", "fuzz the parser and shrink it"))

    def test_a_format_write_that_states_no_format_is_refused(self):
        allowed, why = synthesis.claims_the_request("Write the text hello.")
        self.assertFalse(allowed)
        self.assertEqual(why, "NO_FORMAT_STATED")


if __name__ == "__main__":
    unittest.main()
