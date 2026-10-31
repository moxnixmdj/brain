# PROJECT_BRAIN
"""Pins for git.repository.operate.v1 — the git object model as typed operations.

Measured 2026-10-29 on c79a8f5: the registry had **zero** capabilities whose id
contained ``git``, ``commit``, ``branch``, ``blame``, ``bisect`` or ``merge``
(``grep -c`` over the 125 verified ids).  "Show the last three git commits" was
answered PASS by an inventory row keyed on a FILENAME that happens to contain the
word "three" (see ``live_brain_route_admission_v1.inventory_source_path``); no
commit was read.

Three laws are pinned here, each with an oracle that is not the adapter:

  * every operation's reported rows agree with the ``git`` CLI run directly by
    this test on the same repository;
  * the adapter is a typed operation set, not a shell: an operation it does not
    declare, a target that is an option, and a path outside the root all refuse;
  * ``commit`` records exactly what was STAGED.  An untracked file in the working
    tree must still be untracked afterwards — the operation may not absorb work
    nobody asked to record.

Run: python -m pytest canonical/tests/test_git_repository_operate_v1.py -q
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.bound_capabilities import git_repository_operate as git_op

GIT_ENV = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
           "LC_ALL": "C", "TZ": "UTC"}


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-c", "user.name=Fixture", "-c",
                           "user.email=fixture@example.invalid", *args],
                          cwd=cwd, capture_output=True, text=True, env=GIT_ENV,
                          timeout=120)
    if proc.returncode != 0:
        raise AssertionError("fixture git failed: " + " ".join(args) + "\n" + proc.stderr)
    return proc.stdout


class GitRepositoryOperateTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gitop_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        # The adapter confines every path to the root it is called with, so the
        # fixture repository IS the root here.
        self.repo = self.tmp
        _git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "calc.py").write_text("def add(a, b):\n    return a - b\n")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "initial commit")
        (self.repo / "calc.py").write_text("def add(a, b):\n    return a + b\n")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "fix add")
        (self.repo / "notes.txt").write_text("unstaged work\n")

    def _run(self, **kw):
        args = {"output_path": "_out/report.json", "repo_root": ".", **kw}
        return git_op.run(args, self.repo)

    # ------------------------------------------------------------ readers
    def test_log_agrees_with_the_git_cli(self):
        art = self._run(op="log", limit=5)
        expected = [line.split("\t") for line in
                    _git(self.repo, "log", "-n", "5", "--format=%H\t%s").splitlines()]
        self.assertEqual([(r["sha"], r["subject"]) for r in art["rows"]],
                         [(sha, subject) for sha, subject in expected])
        self.assertEqual(art["observed_effect"]["commit_count"], len(expected))

    def test_a_stated_count_is_the_count(self):
        art = self._run(op="log", limit=1)
        self.assertEqual(art["row_count"], 1)
        self.assertEqual(art["rows"][0]["sha"], _git(self.repo, "rev-parse", "HEAD").strip())

    def test_status_agrees_with_the_git_cli(self):
        art = self._run(op="status")
        porcelain = [e for e in _git(self.repo, "status", "--porcelain=v1",
                                     "--untracked-files=all", "-z").split("\0") if e]
        # the adapter's own report is a file in this repository, so it is the one
        # path the two views can legitimately differ on
        expected = [e[3:] for e in porcelain if not e[3:].startswith("_out/")]
        self.assertEqual([r["path"] for r in art["rows"]], expected)
        self.assertEqual(art["observed_effect"]["branch"], "main")

    def test_diff_agrees_with_the_git_cli(self):
        (self.repo / "calc.py").write_text("def add(a, b):\n    return a + b\n\nX = 1\n")
        art = self._run(op="diff", target="calc.py")
        numstat = _git(self.repo, "diff", "--numstat", "HEAD", "--", "calc.py").split("\t")
        self.assertEqual(art["rows"], [{"path": "calc.py", "added": int(numstat[0]),
                                        "removed": int(numstat[1])}])
        self.assertEqual(art["observed_effect"]["patch_bytes"] > 0, True)

    # ---------------------------------------------------- an untracked target
    # "Show the diff of <file>" answers a question about a file that git may not
    # know yet.  ``git diff HEAD -- <untracked>`` is EMPTY by design, and an empty
    # patch returned as the answer is a PASS over nothing.  Measured 2026-10-31 on
    # fabf28c: the request was served with ``row_count: 0`` and the empty-string
    # digest, and the 54-case capability matrix scored ``git_diff`` FALSE -- the
    # only false PASS in the matrix.  The difference between nothing and a new file
    # is a fact, and git states it with ``--no-index``.
    def test_an_untracked_target_still_has_a_diff(self):
        (self.repo / "fresh.py").write_text("def mul(a, b):\n    return a * b\n")
        art = self._run(op="diff", target="fresh.py")
        self.assertFalse(art["observed_effect"]["tracked"])
        self.assertEqual(art["row_count"], 1)
        self.assertGreater(art["observed_effect"]["patch_bytes"], 0)
        self.assertIn("@@", art["observed_effect"]["patch"])
        self.assertIn("new file mode", art["observed_effect"]["patch"])
        # the oracle is the CLI run by this test, not the adapter: git's own
        # --no-index numstat must agree on how many lines the file adds.
        proc = subprocess.run(["git", "diff", "--no-index", "--numstat", "--",
                               "/dev/null", "fresh.py"],
                              cwd=self.repo, capture_output=True, text=True,
                              env=GIT_ENV, timeout=120)
        self.assertEqual(art["rows"][0]["added"], int(proc.stdout.split("\t")[0]))

    def test_an_unchanged_tracked_target_is_an_honest_empty_diff(self):
        """The fix may not turn "nothing changed" into an invented patch."""
        art = self._run(op="diff", target="calc.py")
        self.assertTrue(art["observed_effect"]["tracked"])
        self.assertEqual(art["row_count"], 0)
        self.assertEqual(art["observed_effect"]["patch_bytes"], 0)
        self.assertNotIn("@@", art["observed_effect"]["patch"])

    def test_branch_agrees_with_the_git_cli(self):
        _git(self.repo, "branch", "feature")
        art = self._run(op="branch")
        names = sorted(line.split("\t")[0] for line in
                       _git(self.repo, "for-each-ref", "--format=%(refname:short)%09%(objectname)",
                            "refs/heads").splitlines())
        self.assertEqual(sorted(r["name"] for r in art["rows"]), names)
        self.assertEqual(art["observed_effect"]["current"], "main")

    def test_blame_agrees_with_the_git_cli(self):
        art = self._run(op="blame", target="calc.py", limit=50)
        self.assertEqual(art["row_count"], 2)
        self.assertEqual({r["sha"] for r in art["rows"]},
                         {_git(self.repo, "rev-parse", "HEAD").strip(),
                          _git(self.repo, "rev-parse", "HEAD~1").strip()})
        self.assertEqual(art["observed_effect"]["unreachable"], [])

    def test_show_names_the_object_the_cli_names(self):
        art = self._run(op="show")
        self.assertEqual(art["rows"][0]["sha"], _git(self.repo, "rev-parse", "HEAD").strip())
        self.assertEqual(art["observed_effect"]["object_type"], "commit")

    # ------------------------------------------------------------- write
    def test_commit_records_only_what_was_staged(self):
        (self.repo / "calc.py").write_text("def add(a, b):\n    return a + b\n# staged\n")
        _git(self.repo, "add", "calc.py")
        (self.repo / "untracked.txt").write_text("not in the commit\n")
        before = _git(self.repo, "rev-parse", "HEAD").strip()
        art = self._run(op="commit", message="record calc")
        after = _git(self.repo, "rev-parse", "HEAD").strip()
        self.assertEqual(art["observed_effect"]["commit_sha"], after)
        self.assertEqual(art["observed_effect"]["parent_sha"], before)
        self.assertNotEqual(after, before)
        files = _git(self.repo, "show", "--name-only", "--format=", "HEAD").split()
        self.assertEqual(files, ["calc.py"])
        self.assertIn("?? untracked.txt", _git(self.repo, "status", "--porcelain"))
        self.assertEqual(art["observed_effect"]["subject"], "record calc")

    def test_a_commit_with_nothing_staged_refuses(self):
        with self.assertRaises(git_op.GitOperateError):
            self._run(op="commit", message="nothing to record")

    # ---------------------------------------------------------- refusals
    def test_an_undeclared_operation_refuses_by_name(self):
        with self.assertRaises(git_op.GitOperateError) as cm:
            self._run(op="push --force")
        self.assertIn("OP_NOT_DECLARED", str(cm.exception))
        self.assertIn("log,status,diff,show,blame,branch,commit", str(cm.exception))

    def test_a_target_may_not_be_an_option(self):
        with self.assertRaises(git_op.GitOperateError) as cm:
            self._run(op="blame", target="--reverse")
        self.assertIn("TARGET_MAY_NOT_BE_AN_OPTION", str(cm.exception))

    def test_a_target_outside_the_root_refuses(self):
        with self.assertRaises(git_op.GitOperateError) as cm:
            self._run(op="blame", target="../../etc/passwd")
        self.assertIn("TARGET_OUTSIDE_REPOSITORY", str(cm.exception))

    def test_an_output_outside_the_root_refuses(self):
        with self.assertRaises(git_op.GitOperateError) as cm:
            git_op.run({"op": "log", "output_path": "../escape.json"}, self.repo)
        self.assertIn("OUTPUT_PATH_OUTSIDE_REPOSITORY", str(cm.exception))

    def test_a_directory_that_is_not_a_repository_refuses(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        with self.assertRaises(git_op.GitOperateError) as cm:
            git_op.run({"op": "log", "repo_root": "plain",
                        "output_path": "_out/x.json"}, self.tmp)
        self.assertIn("NOT_A_GIT_REPOSITORY", str(cm.exception))

    # ------------------------------------------------------ determinism
    def test_two_runs_write_byte_identical_artifacts(self):
        first = self._run(op="log", limit=5)
        stored = (self.repo / first["output_path"]).read_bytes()
        second = self._run(op="log", limit=5)
        self.assertEqual(stored, (self.repo / second["output_path"]).read_bytes())
        self.assertEqual(first["output_sha256"], second["output_sha256"])

    def test_the_artifact_is_the_report(self):
        art = self._run(op="status")
        body = json.loads((self.repo / art["output_path"]).read_text())
        self.assertEqual(body["schema"], git_op.SCHEMA)
        self.assertEqual(body["row_count"], art["row_count"])
        self.assertTrue(art["output_verified"])


if __name__ == "__main__":
    unittest.main()
