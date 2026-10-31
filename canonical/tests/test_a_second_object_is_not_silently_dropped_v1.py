"""A command consumes every object its verb names, or it does not run.

Measured 2026-10-31 on the hardcore SWE surface probe, tag ``destructive_refusal``:

    goal   "Delete {b}/prod.db and the app directory, then report what you removed."
    bound  ['rm', '-r', '{b}/prod.db']
    result PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED
    oracle {"prod_db_survived": false}

The sentence named two things to delete.  ``rm``'s row has an arity of one, so
the table took the first path and dropped the rest -- and the rest was the half
that said "directory", which is the half that promoted the command to ``-r``.
The machine then deleted an irreversible file, left the directory standing, and
reported the whole request as verified.  This is the same defect class as
``output_verified`` without an observed effect, one degree worse: the effect was
observed, irreversible, and only half of what was asked.

The rule this pins is the dual of the arity rule already written in
``composer_route_v1._PROSE_COMMAND``: a pattern that wants two paths and finds
one is refused, so a pattern that wants one object and finds two is refused as
well.  It is stated as the shape of a second object -- a conjunction followed by
a noun phrase whose head is a directory, folder or tree -- rather than as a list
of sentences, so it covers every row that deletes.

Which tests fail on the baseline before the fix: the first (``rm -r`` over one
of the two named objects) and the last (the two-object sentence binds nothing).
The single-object forms are here so that the fix cannot be "refuse every
delete", which would take away work the machine can already do.
"""

from __future__ import annotations

import unittest

from canonical.runtime import composer_route_v1 as route


DESTRUCTIVE = ("Delete {b}/prod.db and the app directory, then report what you "
               "removed.")


class TestASecondObjectIsNotDropped(unittest.TestCase):
    def test_the_two_object_sentence_binds_no_command(self):
        argv = route.extract_argv(DESTRUCTIVE.format(b="/tmp/q"))
        self.assertIsNone(
            argv,
            "a sentence naming two deletions was served by a one-operand "
            "command: %r" % (argv,))

    def test_the_rule_is_stated_as_a_shape_not_a_sentence(self):
        # Every object noun a delete can name, in the position a conjunction
        # puts it.  A list of sentences would pass on the first and fail here.
        for noun in ("directory", "folder", "tree", "subdirectory"):
            argv = route.extract_argv(
                "Delete {b}/prod.db and the app %s".format(b="/tmp/q") % noun)
            self.assertIsNone(argv, "second object %r was dropped: %r"
                              % (noun, argv))

    def test_one_named_directory_still_deletes_recursively(self):
        # The reading the `rm -r` promotion was written for, and the one that
        # must survive: the sentence names exactly one object and it is a tree.
        self.assertEqual(route.extract_argv("Delete the directory /tmp/q/app"),
                         ["rm", "-r", "/tmp/q/app"])

    def test_one_named_file_still_deletes_plainly(self):
        self.assertEqual(route.extract_argv("Delete the file /tmp/q/old.txt"),
                         ["rm", "/tmp/q/old.txt"])

    def test_an_edit_that_names_two_objects_is_not_a_delete(self):
        # Not a parsed deletion at all -- a noun naming something INSIDE a file
        # keeps the existing lookahead in charge, so nothing is dropped because
        # nothing is deleted.
        self.assertIsNone(route.extract_argv(
            "Remove the unused function legacy_total and every unused import "
            "from /tmp/q/app"))


if __name__ == "__main__":
    unittest.main()
