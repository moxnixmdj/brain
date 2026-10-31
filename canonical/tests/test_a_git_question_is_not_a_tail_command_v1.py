"""A git question is not a tail command, and a stated count is not the default.

Measured on main 9f808230, 2026-10-31, before this fix:

    "Show the last three git commits in <other repo>."
        -> ['tail', '-n', '2', '<that directory>']
    "Show the last three git commits and save the list to X."
        -> ['tail', '-n', '2', 'X']          # the last two lines OF THE OUTPUT FILE
    "Show the last three lines of <file>."
        -> ['tail', '-n', '2', '<file>']     # the sentence said three

Three separate readings were wrong at once, and each one is a different law:

  1. `_prose_argv` refused the git question in `git_argv` (correctly -- another
     repository cannot be stated yet) and then fell through to the FILE command
     table, which answered it with `tail`.  A sentence that names git is not a
     file question; answering it with another program is a wrong answer, not a
     fallback.  The same table cannot verify git at all: `git` is absent from
     `raw_goal_trace_acceptance_v1._READ_ONLY_COMMANDS`, so the adapter is never
     told to write stdout to the bound output and there is no git postcondition
     to judge.  The row that does verify git is `git.repository.operate.v1`, and
     the composer's token path reaches it once the file table stops claiming the
     sentence.

  2. `_COUNT_RE` read digits only, so "three" was not a count and `_prose_count`
     returned its documented default of 2 -- a default overriding a number the
     sentence had already stated.

  3. `git_argv`'s log rule required "recent commits" / "commit history" / "last
     commit", so "the last three git commits" matched nothing and a git read the
     machine can perform refused.

The oracles here never read the runtime's own report: they read the argv, and
they read the repository's real history through `git log`.
"""
from __future__ import annotations

import pathlib
import subprocess
import unittest

from canonical.runtime import composer_route_v1 as route
from canonical.runtime import live_brain_route_admission_v1 as door

ROOT = pathlib.Path(__file__).resolve().parents[2]


class AStatedCountIsReadAsStatedTests(unittest.TestCase):
    def test_a_number_written_as_a_word_is_the_count(self):
        target = "canonical/runtime/availability_v1.py"
        self.assertEqual(route.extract_argv("Show the last three lines of %s." % target),
                         ["tail", "-n", "3", target])
        self.assertEqual(route.extract_argv("Show the last two lines of %s." % target),
                         ["tail", "-n", "2", target])

    def test_a_sentence_that_states_no_count_still_gets_the_documented_default(self):
        target = "canonical/runtime/availability_v1.py"
        self.assertEqual(route.extract_argv("Show the last lines of %s." % target),
                         ["tail", "-n", "2", target])
        self.assertEqual(route.extract_argv("Show the last line of %s." % target),
                         ["tail", "-n", "1", target])


class AGitQuestionIsNotAFileQuestionTests(unittest.TestCase):
    def test_a_repository_the_reader_cannot_state_is_not_answered_with_tail(self):
        argv = route.extract_argv("Show the last three git commits in /tmp/not-this-repository.")
        self.assertIsNone(argv, "a refused git read must not become a file command: %r" % (argv,))

    def test_a_destination_does_not_turn_git_history_into_the_files_last_lines(self):
        argv = route.extract_argv(
            "Show the last three git commits and save the list to canonical/astra_runtime/tmp/g.txt.")
        self.assertIsNone(argv, "the report path must not become tail's operand: %r" % (argv,))

    def test_the_log_read_is_stated_by_the_git_reader(self):
        self.assertEqual(route.git_argv("Show the last two commits."),
                         ["git", "log", "--oneline", "-n", "2"])
        self.assertEqual(route.git_argv("Show the last three git commits."),
                         ["git", "log", "--oneline", "-n", "3"])


class TheGitRowAnswersTheGitQuestionTests(unittest.TestCase):
    def test_the_last_commits_are_answered_by_the_row_that_verifies_git(self):
        result = door.solve({"task_id": "GIT_last_three",
                             "goal": "Show the last three git commits."})
        self.assertIs(result.get("pass"), True, result.get("status"))
        self.assertEqual(result.get("compiled_capability_id") or result.get("capability_id"),
                         "git.repository.operate.v1")
        # Independent oracle: the commits the row reported are the commits git reports.
        expected = subprocess.run(["git", "log", "--oneline", "-n", "3"], cwd=str(ROOT),
                                  text=True, capture_output=True, check=True).stdout.strip().splitlines()
        steps = result.get("execution") or []
        rows = ((steps[0].get("result") or {}).get("rows") or []) if steps else []
        reported = [str(row.get("sha") or "") for row in rows]
        self.assertEqual(len(reported), len(expected), "the row did not report the commits git reports")
        for sha, expected_line in zip(reported, expected):
            self.assertTrue(expected_line.startswith(sha[:7]),
                            "%s is not one of git's last three commits" % sha)


if __name__ == "__main__":
    unittest.main()
