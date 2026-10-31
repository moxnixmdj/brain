"""A question about the repository is answered by the repository, not refused and not "no effect".

Measured 2026-10-30, wiring the git family into the prose table (the acceptance layer had been able
to verify `git status/diff/log/show/blame` by re-running them all along; nothing could state one):

    "Show me the recent commits."
        route  shell.command.run
        bind   output_path UNBOUND          -> OPEN__COMPOSER_SLOT_UNBOUND, no command ran
    "What changed since the last commit?"
        run    git status --porcelain       (correct, verified)
        then   FAIL_CLOSED__NO_OBSERVED_EFFECT
               because the noun "commit" matched the change-verb table, so the gate demanded that
               something on disk move -- for a sentence that asks what moved

Three rules, each read off a measured failure, are pinned here:

  1. A READ COMMAND'S ANSWER IS ITS STDOUT, and it lands in the machine's own scratch.  A path
     inside the command's own argv is an OPERAND: `git -C <dir> status` bound `<dir>` as the
     output and then reported NO_OBSERVED_EFFECT over a command that ran correctly.
  2. A QUESTION IS NOT A PROMISE.  An interrogative or a read-only opener never promises a change.
  3. A CAPTURE IS A SUFFIX.  The adapter keeps the last 12 000 characters, so comparing that
     suffix against a full re-run failed every command whose output is larger than the cap -- and
     the command had reproduced exactly.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import composer_route_v1 as composer  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

REPO = "canonical/astra_runtime/tmp/test_repo_question"


def _make_repo() -> None:
    """One commit and one uncommitted change: a repository with something to report."""
    import shutil
    import subprocess
    base = ROOT / REPO
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    (base / "a.txt").write_text("hello\n", encoding="utf-8")
    env = {"GIT_AUTHOR_NAME": "p", "GIT_AUTHOR_EMAIL": "p@x",
           "GIT_COMMITTER_NAME": "p", "GIT_COMMITTER_EMAIL": "p@x",
           "PATH": "/usr/bin:/bin"}
    for argv in (("init", "-q", "-b", "main"), ("add", "-A"), ("commit", "-qm", "init")):
        subprocess.run(("git", "-C", str(base)) + argv, check=False, capture_output=True, env=env)
    (base / "a.txt").write_text("hello\nbye\n", encoding="utf-8")


class TheRepositoryAnswersQuestionsAboutItself(unittest.TestCase):

    def setUp(self):
        _make_repo()

    def test_a_git_question_is_translated_into_the_command_that_answers_it(self):
        self.assertEqual(composer.extract_argv("What changed since the last commit?"),
                         ["git", "status", "--porcelain"])
        self.assertEqual(composer.extract_argv("Show me the recent commits."),
                         ["git", "log", "--oneline", "-n", "20"])

    def test_a_git_write_with_no_stateable_promise_states_no_command(self):
        for goal in ("Revert the last commit.",
                     "Find the commit that broke the build using git bisect.",
                     "Push the branch to origin."):
            self.assertIsNone(composer.extract_argv(goal), goal)

    def test_a_read_commands_operand_is_not_its_output(self):
        goal = "What changed in %s since the last commit?" % REPO
        args = composer.bind({"argv": "ARGV", "output_path": "PATH_OUTPUT"}, goal)
        self.assertEqual(args.get("argv"),
                         ["git", "-C", REPO, "status", "--porcelain"])
        self.assertNotEqual(args.get("output_path"), REPO)
        self.assertTrue(str(args.get("output_path") or "").startswith(
            "canonical/astra_runtime/tmp/"), args.get("output_path"))
        self.assertEqual(args.get("write_stdout_to_output"), "true")

    def test_a_directory_that_is_not_a_repository_is_refused_not_answered_elsewhere(self):
        """`git status` inside a plain directory reports the ENCLOSING repository."""
        self.assertIsNone(composer.extract_argv(
            "What changed in canonical/runtime since the last commit?"))

    def test_a_mutating_command_keeps_its_operand_as_the_output(self):
        args = composer.bind({"argv": "ARGV", "output_path": "PATH_OUTPUT"},
                             "Delete canonical/astra_runtime/tmp/gone.txt.")
        self.assertEqual(args.get("argv"), ["rm", "canonical/astra_runtime/tmp/gone.txt"])
        self.assertEqual(args.get("output_path"), "canonical/astra_runtime/tmp/gone.txt")
        self.assertNotIn("write_stdout_to_output", args)

    def test_a_question_about_changes_promises_no_change(self):
        for goal in ("What changed since the last commit?",
                     "Which files changed in the last commit?",
                     "Show me the diff of the working tree.",
                     "Find every caller of the function add in pkg."):
            self.assertFalse(door._sentence_promises_a_change(goal), goal)
        for goal in ("Repair the failing test in pkg/calc.py.",
                     "Rename the symbol mul to multiply in pkg/calc.py.",
                     "Write the text 'hello' to the file out.txt."):
            self.assertTrue(door._sentence_promises_a_change(goal), goal)

    def test_the_three_questions_are_answered_and_certified(self):
        for goal in ("Show me the recent commits.",
                     "What changed since the last commit?",
                     "What is the diff of the working tree?"):
            result = door.solve({"task_id": "repo_question", "goal": goal})
            self.assertIs(result.get("pass"), True,
                          "%r was not answered: %s / %s"
                          % (goal, result.get("status"), result.get("unverified_reason")))
            # and the answer is the command's own output, in the machine's scratch
            steps = ((result.get("composer_execution") or {}).get("steps") or [])
            if steps:
                out = str((steps[0].get("args") or {}).get("output_path") or "")
                self.assertTrue(out.startswith("canonical/astra_runtime/tmp/"), out)


if __name__ == "__main__":
    unittest.main()
