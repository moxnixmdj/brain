"""`git` belongs in neither table, so every git sentence was refused after doing the work.

Measured 2026-10-29 on this repository::

    Run the shell command "git diff -- canonical/runtime/declared_input_derivation_v1.py"
      execute_chain   PASS__COMPOSER_CHAIN_EXECUTED       real stdout, argv exactly as stated
      the door        FAIL_CLOSED__COMPOSED_CHAIN_NOT_VERIFIED

Nothing was wrong with the run.  The inspector's only question was
``program in _READ_ONLY_COMMANDS``, and `git` cannot be placed in that frozenset OR in
``_MUTATING_POSTCONDITIONS``: `blame`/`log`/`show`/`diff` are re-runnable readers, `commit`/
`checkout`/`reset` rewrite the repository.  A program name is not a behaviour.

The fix is the mechanism this file already uses one level up — ``_SIDE_EFFECTING_FLAGS_BY_PROGRAM``
keys a program's *flags* rather than its name — so ``_READ_ONLY_SUBCOMMANDS`` keys its
*subcommands*.  Everything not listed stays unverifiable, which is why `git commit` still refuses.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import raw_goal_trace_acceptance_v1 as accept  # noqa: E402

GIT = shutil.which("git")


@unittest.skipUnless(GIT, "git is not installed")
class TheSubcommandDecidesWhetherTheCommandCanBeReRun(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="git-subcommand-")
        self.repo = pathlib.Path(self.temp.name)
        (self.repo / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        for argv in (["init", "-q"], ["add", "calc.py"], ["-c", "user.name=t", "-c",
                                                           "user.email=t@example.com",
                                                           "commit", "-qm", "first"]):
            subprocess.run(["git", *argv], cwd=self.repo, check=True, capture_output=True)

    def tearDown(self):
        self.temp.cleanup()

    def _inspect(self, argv, root=None):
        claim = subprocess.run(argv, cwd=self.repo, capture_output=True)
        result = {"stdout": claim.stdout.decode("utf-8", "replace"),
                  "stderr": claim.stderr.decode("utf-8", "replace"),
                  "returncode": claim.returncode}
        return accept._inspect_shell_command_run({"argv": argv}, result, root or self.repo)

    def test_a_reading_git_subcommand_is_re_run_and_compared(self):
        for argv in (["git", "log", "-1", "--oneline", "--", "calc.py"],
                     ["git", "status", "--porcelain"],
                     ["git", "rev-parse", "HEAD"],
                     ["git", "diff", "--", "calc.py"]):
            ok, reason, evidence = self._inspect(argv)
            self.assertTrue(ok, (argv, reason))
            self.assertTrue(evidence.get("command_re_run"), (argv, evidence))

    def test_a_writing_git_subcommand_stays_unverifiable(self):
        for argv in (["git", "commit", "-m", "second"],
                     ["git", "checkout", "--", "calc.py"],
                     ["git", "reset", "--hard"],
                     ["git", "clean", "-fdx"]):
            ok, reason, _evidence = self._inspect(argv)
            self.assertFalse(ok, argv)
            self.assertEqual(reason, "COMMAND_NOT_RE_RUNNABLE_WITHOUT_SIDE_EFFECTS", (argv, reason))

    def test_a_flag_before_the_subcommand_is_not_a_subcommand(self):
        # `git --version` names no subcommand, so it is not re-runnable by this rule.
        ok, reason, _ = self._inspect(["git", "--version"])
        self.assertFalse(ok)
        self.assertEqual(reason, "COMMAND_NOT_RE_RUNNABLE_WITHOUT_SIDE_EFFECTS")

    def test_the_program_set_the_router_reads_now_names_git(self):
        from canonical.runtime import composer_route_v1 as route
        self.assertIn("git", route._known_programs())
        # and the strict table still does not: the behaviour is the subcommand's.
        self.assertNotIn("git", accept._READ_ONLY_COMMANDS)
        self.assertNotIn("git", accept._MUTATING_POSTCONDITIONS)


if __name__ == "__main__":
    unittest.main()
