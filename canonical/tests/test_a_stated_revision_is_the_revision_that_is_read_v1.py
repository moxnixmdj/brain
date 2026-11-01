"""A sentence that names a revision must be answered about THAT revision.

Measured 2026-11-01 on ``05762527``: a two-commit repository in which ``git diff HEAD~1``
carries exactly one hunk (``-A = 1`` / ``+A = 2``) was asked

    Show me the diff of <pkg>/f.py against HEAD~1.

The door answered ``git diff HEAD`` -- the working tree against the current commit -- and in
a clean tree that is the EMPTY patch.  It reported ``rows: []``, ``output_verified: True`` and
``PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED``.  A false pass of the
worst class: a verified claim over an effect that was never observed.  The row's contract had
``op/target/repo_root/limit/message`` and NO slot for a revision, so the sentence's own object
could not reach the adapter even in principle.

Three laws are pinned here:

1. the slot exists and is declared (``rev`` in the registry row);
2. the sentence's revision is what binds it, and a sentence that names none says so;
3. the adapter diffs the revision it was given, and the empty answer belongs to ``HEAD``
   while the hunk belongs to ``HEAD~1`` -- the two are distinguishable, which is what makes
   the first one an answer instead of a false pass.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import unittest

from canonical.runtime import declared_input_derivation_v1 as derivation
from canonical.runtime.bound_capabilities import git_repository_operate as git_op

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORK = ROOT / "canonical/astra_runtime/tmp/test_stated_revision"
ROW = "git.repository.operate.v1"

_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}


def _registry() -> dict:
    path = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    return json.loads(path.read_text(encoding="utf-8"))["capabilities"]


def _git(cwd: pathlib.Path, *argv: str) -> str:
    env = {"HOME": str(cwd), "PATH": "/usr/local/bin:/usr/bin:/bin", **_ENV}
    proc = subprocess.run(("git", *argv), cwd=str(cwd), capture_output=True, text=True,
                          env=env, timeout=120)
    return proc.stdout


def _two_commits() -> pathlib.Path:
    if WORK.exists():
        shutil.rmtree(WORK)
    pkg = WORK / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "f.py").write_text("A = 1\n", encoding="utf-8")
    _git(WORK, "init", "-q")
    _git(WORK, "add", "-A")
    _git(WORK, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "baseline")
    (pkg / "f.py").write_text("A = 2\n", encoding="utf-8")
    _git(WORK, "add", "-A")
    _git(WORK, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "change")
    return WORK


def _diff(root: pathlib.Path, **extra) -> dict:
    args = {"op": "diff", "target": "pkg/f.py",
            "output_path": "report/diff.json", **extra}
    return git_op.run(args, root)


class TheRevisionSlotIsDeclared(unittest.TestCase):

    def test_the_row_declares_a_slot_for_the_revision(self):
        entry = _registry()[ROW]
        self.assertIn("rev", entry["action_template"]["args"])
        self.assertEqual(entry["action_template"]["args"]["rev"], "${input.rev}")


class TheSentenceDecidesWhichRevision(unittest.TestCase):

    def _bind(self, goal: str) -> dict:
        return derivation.derive(goal, _registry()[ROW], ROOT)

    def test_a_stated_revision_is_bound_verbatim(self):
        bound = self._bind("Show me the diff of pkg/calc.py against HEAD~1.")
        self.assertEqual(bound["rev"]["value"], "HEAD~1")
        self.assertEqual(bound["rev"]["rule"], "REVISION_FROM_STATED_SENTENCE")

    def test_a_previous_commit_phrase_is_the_parent_revision(self):
        bound = self._bind("What changed in pkg/calc.py compared to the previous commit?")
        self.assertEqual(bound["rev"]["value"], "HEAD~1")

    def test_a_sentence_that_names_no_revision_says_so(self):
        """Silence must not be read as ``HEAD~1``, and must not be read as silence either.

        The slot is bound to the current commit WITH A RULE THAT NAMES IT, so the receipt
        states which trees were compared even for the default case.
        """
        bound = self._bind("Show the diff of pkg/calc.py.")
        self.assertEqual(bound["rev"]["value"], "HEAD")
        self.assertEqual(bound["rev"]["rule"], "REVISION_NOT_STATED_CURRENT_COMMIT")


class TheAdapterDiffsTheRevisionItWasGiven(unittest.TestCase):

    def setUp(self):
        self.root = _two_commits()

    def test_the_stated_parent_revision_carries_the_hunk(self):
        result = _diff(self.root, rev="HEAD~1")
        patch = result["observed_effect"]["patch"]
        self.assertEqual(result["row_count"], 1)
        self.assertIn("-A = 1", patch)
        self.assertIn("+A = 2", patch)
        self.assertEqual(result["observed_effect"]["rev"], "HEAD~1")

    def test_the_current_commit_has_no_difference_and_says_which_one_it_is(self):
        result = _diff(self.root, rev="HEAD")
        self.assertEqual(result["row_count"], 0)
        self.assertEqual(result["observed_effect"]["patch"], "")
        # The empty answer is an ANSWER: it names the revision it is empty about.
        self.assertEqual(result["observed_effect"]["rev"], "HEAD")
        self.assertTrue(result["observed_effect"]["rev_sha"])

    def test_a_revision_that_does_not_exist_is_refused_not_read_as_empty(self):
        with self.assertRaises(RuntimeError) as raised:
            _diff(self.root, rev="HEAD~99")
        self.assertIn("STATED_REVISION_NOT_FOUND", str(raised.exception))

    def test_an_option_is_never_read_as_a_revision(self):
        with self.assertRaises(RuntimeError) as raised:
            _diff(self.root, rev="--output=/tmp/pwn")
        self.assertIn("REV_MAY_NOT_BE_AN_OPTION", str(raised.exception))


if __name__ == "__main__":
    unittest.main()


class ACommitRecordsWhatTheSentenceNamed(unittest.TestCase):
    """A commit is the sentence's, not the checkout's.

    Two failures measured 2026-11-01, one line apart:

    * "Commit the changes in <pkg> with a clear message" was refused
      ``R13_DECLARED_INPUT_UNBINDABLE:message`` -- the sentence delegates the wording and the
      contract could not say so.  The message now comes from the staged diff, so it describes
      the commit instead of guessing at the sentence.
    * the same commit ran ``git add -A`` across the WHOLE repository, recording every unrelated
      edit in the checkout while the receipt named one package.  Staging is now pinned to the
      stated subtree, and a staged path outside it is refused rather than committed.
    """

    def setUp(self):
        self.root = _two_commits()
        # ...plus work in progress, which is what a commit records.
        pending = self.root / "pkg/f.py"
        pending.write_text(pending.read_text(encoding="utf-8") + "B = 3\n", encoding="utf-8")

    def _commit(self, **extra):
        args = {"op": "commit", "output_path": "report/commit.json",
                "staged": False, "rev": "HEAD", "target": "pkg", **extra}
        return git_op.run(args, self.root)

    def test_a_delegated_message_describes_what_the_commit_records(self):
        result = self._commit(message="", message_source="DELEGATED_STAGED_DIFF")
        subject = result["observed_effect"]["subject"]
        self.assertTrue(subject.startswith("Update pkg/f.py"), subject)
        self.assertEqual(result["observed_effect"]["files_committed"], 1)

    def test_a_sweep_is_pinned_to_the_stated_subtree(self):
        (self.root / "outside.txt").write_text("not this package\n", encoding="utf-8")
        result = self._commit(message="in scope")
        staged = subprocess.run(("git", "show", "--name-only", "--format=", "HEAD"),
                                cwd=str(self.root), capture_output=True, text=True,
                                env={"HOME": str(self.root), "PATH": "/usr/bin:/bin", **_ENV},
                                timeout=120).stdout.split()
        self.assertEqual(staged, ["pkg/f.py"])
        self.assertEqual(result["observed_effect"]["target"], "pkg")
        # ...and the file nobody named is still uncommitted.
        self.assertTrue((self.root / "outside.txt").is_file())

    def test_staging_outside_the_stated_target_is_refused(self):
        (self.root / "outside.txt").write_text("not this package\n", encoding="utf-8")
        _git(self.root, "add", "outside.txt")
        with self.assertRaises(RuntimeError) as raised:
            self._commit(message="in scope")
        self.assertIn("STAGED_OUTSIDE_STATED_TARGET", str(raised.exception))
