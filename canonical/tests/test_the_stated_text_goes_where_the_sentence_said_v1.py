"""The destination of a stated text is the one the sentence puts after it.

A request can name two destinations with two different roles:

    "Write the text 'hello patch' to the file out.txt
     and save the report to report.json."

The binder took the LAST path in the sentence as the output, because for
"compress notes.txt into notes.txt.gz" the last path is the right answer. Measured
on e00d2d5 that put the stated text into report.json and left out.txt -- the file
the sentence actually asked for -- uncreated, and the artifact gate correctly
refused with PROMISED_ARTIFACT_MISSING:out.txt. The gate was right; the binding was
wrong, and the user's text was sitting in a file they had named for something else.

The destination a payload runs to is the path the sentence puts immediately after
it. That is the same notion the acceptance side already verifies, and it is
consulted only when content was actually stated -- so a sentence with no payload
keeps binding exactly as it always did.
"""

import unittest

from canonical.runtime import composer_route_v1 as cr


class TestTheDestinationOfAStatedTextIsFound(unittest.TestCase):

    def test_the_destination_following_the_payload_is_returned(self):
        for goal, want in (
            ("Write the text 'hello patch' to the file c/x/out.txt "
             "and save the report to c/x/report.json.", "c/x/out.txt"),
            ("Write the text 'hi' to the file c/x/w.txt", "c/x/w.txt"),
            ('Write the text "hi" into c/x/w.txt', "c/x/w.txt"),
            ("Write the text 'a b c' to the file c/x/w.txt.", "c/x/w.txt"),
            ("Put the content 'abc' at c/x/w.txt", "c/x/w.txt"),
        ):
            self.assertEqual(
                cr.extract_content_destination(goal), want,
                "wrong destination for %r" % goal,
            )

    def test_a_sentence_that_states_no_destination_for_its_text_returns_none(self):
        """These must keep binding the way they always did."""
        for goal in (
            "compress notes.txt into notes.txt.gz",
            "Create the file c/x/w.txt containing the text 'hi'",
            "Copy the file c/x/a.txt to c/x/b.txt",
            "Read the file c/x/a.txt",
            "",
        ):
            self.assertIsNone(
                cr.extract_content_destination(goal),
                "invented a destination for %r" % goal,
            )

    def test_the_destination_is_only_consulted_when_content_was_stated(self):
        """The guard that keeps this from changing sentences that already worked."""
        self.assertIsNone(cr.extract_content("compress notes.txt into notes.txt.gz"))
        self.assertEqual(
            cr.extract_content("Write the text 'hi' to the file c/x/w.txt"), "hi")


class TestABindingTakesTheDestinationTheSentenceStated(unittest.TestCase):

    def test_the_output_slot_gets_the_content_destination_not_the_last_path(self):
        sig = {"content": "STRING", "output_path": "PATH_OUTPUT"}
        goal = ("Write the text 'hello patch' to the file c/x/out.txt "
                "and save the report to c/x/report.json.")
        args = cr.bind(sig, goal, None, {})
        self.assertEqual(args.get("output_path"), "c/x/out.txt")

    def test_with_no_content_stated_the_last_path_still_binds(self):
        """The rule this replaced is still the rule for every sentence with no payload."""
        sig = {"output_path": "PATH_OUTPUT"}
        args = cr.bind(sig, "compress notes.txt into notes.txt.gz", None, {})
        self.assertEqual(args.get("output_path"), "notes.txt.gz")


if __name__ == "__main__":
    unittest.main()
