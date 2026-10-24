"""The text a request states must be the text that reaches the disk.

Measured on ``4d859af`` (the commit that made the request's own text stop choosing
the capability), eight ordinary write requests were each reported as
``PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED``.  Exactly one of
the eight files contained what the sentence said::

    "Write the text the results are in the attachment to the file X"
        -> X contained "results are"

Two independent defects produced that, and both are ordinary English:

* ``composer_route_v1._CONTENT`` ended the payload at the first ``to|into|in|at``.
  Those four words introduce a destination sometimes and belong to the payload far
  more often, so "the results are **in** the attachment" stopped at "the results
  are".  13 of 18 sampled payloads were truncated this way.
* ``extract_content`` then ran ``re.sub(r"^(?:the|a|an)\\s+", "", body)``.  A stated
  payload is a quotation, not a noun phrase, so "the archive manifest listing"
  became "archive manifest listing".  That strip alone altered 7 of the 13.

Neither defect could be caught, and the reason is the more serious half of this
file.  The exact-semantic re-inspector compares the bytes on disk against
``args["content"]`` -- the already-altered value.  The file and the argument agreed,
so the check passed.  A verification that compares an artifact to the argument that
produced it can only ever prove the writer did what the plan said; it cannot prove
the plan said what was asked.  Both are needed, and only the first existed.

So this file pins both halves: the binder returns the stated text unchanged, and the
acceptance verifier independently re-derives the payload from the sentence and
refuses to certify a step whose payload the sentence does not state.  Reverting
either half turns these tests red, and reverting the binder alone turns the
end-to-end verdict from a false 8 of 8 into an honest 1 of 8.
"""

from __future__ import annotations

import sys
import time
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RUNTIME = ROOT / "canonical" / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from canonical.runtime.composer_route_v1 import extract_content  # noqa: E402
import canonical.runtime.raw_goal_trace_acceptance_v1 as _acceptance  # noqa: E402

# Looked up rather than imported so that a tree without it produces a failing test
# with a reason instead of a module-level ImportError that hides every assertion in
# this file.  On 4d859af the acceptance verifier had no way to re-derive a payload
# at all, and that absence is itself the defect.
_PAYLOAD_GROUNDING = getattr(_acceptance, "_payload_runs_to_the_destination", None)


def _grounded(goal: str, payload: str) -> bool:
    if _PAYLOAD_GROUNDING is None:
        raise AssertionError(
            "raw_goal_trace_acceptance_v1 cannot re-derive a stated payload from the "
            "sentence, so nothing stops it certifying bytes the request never asked "
            "for.  It compares the file to args['content'], the already-altered "
            "value, and the two always agree."
        )
    return bool(_PAYLOAD_GROUNDING(goal, payload))

# Deliberately carries no English words.  Every component of a path in the request
# becomes a goal token, so a scratch directory named for the behaviour under test
# ("payload_verbatim") is scored against the capability registry alongside the
# sentence itself.  Measured: with that name the same goal selects
# python.software.request.semantic_behavior.compile.v1 and dies on
# R3_WEAK_EVIDENCE, so the test would fail for a reason unrelated to anything it
# is trying to prove.
SCRATCH = "canonical/astra_runtime/tmp/x7f3a"

# Ordinary English payloads.  Each one is a sentence fragment a person would really
# ask to have written, and each contains a word that the old terminator set treated
# as the start of a destination, or begins with an article the old code stripped.
STATED_TEXTS = (
    "the archive manifest listing",
    "a plain sentence about nothing in particular",
    "an important note",
    "the results are in the attachment",
    "items in stock at the warehouse",
    "the first line in the file header",
    "text in the middle of it",
    "a note about the meeting at noon",
    "write this at the top",
    "rank the source candidates by objective relevance",
    "hello world",
    "the quick brown fox",
    "convert the markdown document to pdf",
    "compile the semantic behavior of this module",
    "audit the python source and extract the evidence",
    "verify the docx document intent",
    "fetch the http json state",
    "generate a qr image from this string",
)


def _write_goal(content: str, output_path: str) -> str:
    return "Write the text %s to the file %s" % (content, output_path)


class TestStatedTextIsReturnedUnchanged(unittest.TestCase):
    """Half one: the binder must hand back the sentence, not an edit of it."""

    def test_every_stated_text_survives_the_binder_verbatim(self):
        altered = [
            (text, extract_content(_write_goal(text, SCRATCH + "/o.txt")))
            for text in STATED_TEXTS
            if extract_content(_write_goal(text, SCRATCH + "/o.txt")) != text
        ]
        self.assertEqual(
            altered,
            [],
            "%d of %d stated texts were altered by the binder; the request asks for "
            "these bytes and the file must receive them unchanged." % (len(altered), len(STATED_TEXTS)),
        )

    def test_a_quoted_payload_keeps_its_article(self):
        self.assertEqual(
            extract_content(_write_goal("the quick brown fox", SCRATCH + "/o.txt")),
            "the quick brown fox",
        )

    def test_a_payload_containing_a_destination_word_is_not_truncated(self):
        self.assertEqual(
            extract_content(_write_goal("the results are in the attachment", SCRATCH + "/o.txt")),
            "the results are in the attachment",
        )


class TestPayloadGroundingInTheAcceptanceVerifier(unittest.TestCase):
    """Half two: the verifier re-derives the payload instead of trusting the binder."""

    GROUNDED = (
        ("the results are in the attachment",
         "Write the text the results are in the attachment to the file a/b.txt"),
        ("the archive manifest listing",
         "Write the text the archive manifest listing to the file a/b.txt"),
        ("hello world", "Write the text hello world to the file a/b.txt"),
        ("items in stock at the warehouse",
         "Write the text items in stock at the warehouse to the file a/b.txt"),
    )

    # Each of these is a truncation of a payload the sentence really stated, and
    # each is still a substring of that sentence.  Substring containment accepts all
    # of them, which is why containment is not the check.
    UNGROUNDED = (
        ("results are",
         "Write the text the results are in the attachment to the file a/b.txt"),
        ("archive manifest listing",
         "Write the text the archive manifest listing to the file a/b.txt"),
        ("items", "Write the text items in stock at the warehouse to the file a/b.txt"),
        ("first line", "Write the text the first line in the file header to the file a/b.txt"),
        ("the source candidates",
         "Create the file a/b.txt containing the text rank the source candidates"),
    )

    def test_a_payload_the_sentence_states_is_accepted(self):
        for payload, goal in self.GROUNDED:
            self.assertTrue(
                _grounded(goal, payload),
                "refused a payload the sentence plainly states: %r" % payload,
            )

    def test_a_truncated_payload_is_refused_even_though_it_is_a_substring(self):
        for payload, goal in self.UNGROUNDED:
            self.assertIn(payload, goal, "test is void unless the payload is a substring")
            self.assertFalse(
                _grounded(goal, payload),
                "certified a payload the sentence never stated: %r" % payload,
            )

    def test_a_payload_that_ends_the_sentence_is_accepted(self):
        goal = "Create the file a/b.txt containing the text rank the source candidates"
        self.assertTrue(_grounded(goal, "rank the source candidates"))


class TestEndToEndTheFileMatchesTheSentence(unittest.TestCase):
    """The claim that matters: the bytes on disk are the bytes the sentence asked for."""

    CASES = (
        "the results are in the attachment",
        "items in stock at the warehouse",
        "the archive manifest listing",
        "an important note",
    )

    def test_verified_requests_wrote_exactly_what_was_asked(self):
        import shutil

        from canonical.runtime.live_brain_route_admission_v1 import solve

        root = ROOT / SCRATCH
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        try:
            wrong = []
            for content in self.CASES:
                output_path = "%s/o_%s_%x.txt" % (SCRATCH, uuid.uuid4().hex[:8], time.perf_counter_ns())
                result = solve(
                    {
                        "task_id": "PAYLOAD_VERBATIM_%x" % time.perf_counter_ns(),
                        "goal": _write_goal(content, output_path),
                    }
                )
                written_path = ROOT / output_path
                on_disk = written_path.read_text(encoding="utf-8") if written_path.is_file() else None
                if on_disk != content:
                    wrong.append((content, on_disk))
            self.assertEqual(
                wrong,
                [],
                "the file did not contain the stated text: %r" % wrong,
            )
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
