#!/usr/bin/env python3
"""Executed proof for the git object-model lane (`git_object_model_v1`).

Each test builds a real repository in a temporary directory and asks the adapter a
question whose answer is known independently -- the shas come from `git rev-parse` read
by the test, not from the artifact -- so a pass means the lane observed the repository
rather than reporting itself.

The red paths are the point of the file: a landing whose suite fails must leave no
branch and no modified file, and a bisect must hand the repository back at the commit it
was given.  Those are the two ways a "change" capability destroys work, so both are
asserted by re-reading the repository after the refusal.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "canonical" / "runtime" / "bound_capabilities" / "git_object_model_v1.py"

GIT = shutil.which("git")
TEST_ARGV_OK = [sys.executable, "-c",
                "import sys;sys.path.insert(0,'.');import calc;"
                "sys.exit(0 if calc.add(2,3)==5 else 1)"]
TEST_ARGV_RED = [sys.executable, "-c", "import sys;sys.exit(1)"]

FIX_DIFF = (
    "diff --git a/calc.py b/calc.py\n"
    "--- a/calc.py\n"
    "+++ b/calc.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def add(a,b):\n"
    "-    return a * b\n"
    "+    return a + b\n"
)


def _load():
    spec = importlib.util.spec_from_file_location("git_object_model_v1_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(repo: pathlib.Path, *argv: str) -> str:
    """Run git inside the fixture.  `cwd=` is always explicit: these tests never touch
    the repository under test, only their own temporary one."""
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@localhost",
        "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@localhost",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
    })
    proc = subprocess.run(["git", *argv], cwd=str(repo), text=True, capture_output=True,
                          env=env, check=False)
    if proc.returncode != 0:
        raise AssertionError("fixture git %s failed: %s" % (argv, proc.stderr))
    return proc.stdout


def _make_repo(root: pathlib.Path) -> tuple[pathlib.Path, list[str]]:
    """Three commits: add is correct, then wrong, then differently wrong.

    The bug therefore enters at the SECOND commit, which is what bisect must find --
    a first-bad answer of the first or last commit would be wrong and the test says so.
    """
    repo = root / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Fixture")
    _git(repo, "config", "user.email", "fixture@localhost")
    (repo / "test_calc.py").write_text(
        "import unittest\nfrom calc import add\n\n\n"
        "class T(unittest.TestCase):\n"
        "    def test_add(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n", encoding="utf-8")
    shas: list[str] = []
    for body in ("    return a + b\n", "    return a - b\n", "    return a * b\n"):
        (repo / "calc.py").write_text("def add(a,b):\n" + body, encoding="utf-8")
        _git(repo, "add", "calc.py", "test_calc.py")
        _git(repo, "commit", "-q", "-m", "add" + body.strip()[-5:])
        shas.append(_git(repo, "rev-parse", "HEAD").strip())
    return repo, shas


@unittest.skipUnless(GIT, "git is not on PATH; the lane is installable but untestable here")
class GitObjectModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load()

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="brain_git_lane_")
        self.root = pathlib.Path(self._tmp).resolve()
        self.repo, self.shas = _make_repo(self.root)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    # ------------------------------------------------------------------ inspect

    def test_inspect_observes_the_repository_it_was_given(self):
        result = self.module.run_inspect({
            "repo_path": "repo",
            "queries": [{"kind": "log", "max_count": 3}, {"kind": "status"},
                        {"kind": "branch"}, {"kind": "ls_files"}],
            "output_path": "out/inspect.json",
        }, self.root)
        self.assertTrue(result["output_verified"])
        self.assertEqual(result["head"], self.shas[-1])
        artifact = json.loads((self.root / "out/inspect.json").read_text(encoding="utf-8"))
        logged = [entry["sha"] for entry in artifact["results"][0]["entries"]]
        self.assertEqual(logged, list(reversed(self.shas)))
        self.assertEqual(artifact["failed_query_count"], 0)
        self.assertEqual(artifact["model_dependency_count"], 0)

    def test_inspect_refuses_an_artifact_outside_the_caller_root(self):
        with self.assertRaises(self.module.GitCapabilityError) as caught:
            self.module.run_inspect({"repo_path": "repo", "queries": [{"kind": "status"}],
                                     "output_path": "../escaped.json"}, self.root)
        self.assertIn("OUTPUT_PATH_OUTSIDE_REPOSITORY", str(caught.exception))
        self.assertFalse((self.root.parent / "escaped.json").exists())

    def test_inspect_refuses_a_directory_that_is_not_a_repository(self):
        (self.root / "plain").mkdir()
        with self.assertRaises(self.module.GitCapabilityError) as caught:
            self.module.run_inspect({"repo_path": "plain", "queries": [{"kind": "status"}],
                                     "output_path": "out/x.json"}, self.root)
        self.assertIn("NOT_A_GIT_WORK_TREE", str(caught.exception))

    # ------------------------------------------------------------------- bisect

    def test_bisect_finds_the_commit_that_broke_the_suite_and_restores_head(self):
        result = self.module.run_bisect({
            "repo_path": "repo", "good": self.shas[0], "bad": self.shas[2],
            "test_argv": TEST_ARGV_OK, "output_path": "out/bisect.json",
        }, self.root)
        self.assertTrue(result["output_verified"])
        self.assertEqual(result["first_bad_commit"], self.shas[1])
        self.assertTrue(result["restored"])
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").strip(), self.shas[-1])
        self.assertEqual(_git(self.repo, "status", "--porcelain", "--untracked-files=no"), "")

    def test_bisect_refuses_a_dirty_tree_and_leaves_it_untouched(self):
        (self.repo / "calc.py").write_text("def add(a,b):\n    return 0\n", encoding="utf-8")
        with self.assertRaises(self.module.GitCapabilityError) as caught:
            self.module.run_bisect({"repo_path": "repo", "good": self.shas[0],
                                    "bad": self.shas[2], "test_argv": TEST_ARGV_OK,
                                    "output_path": "out/bisect.json"}, self.root)
        self.assertIn("DIRTY_WORKTREE", str(caught.exception))
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").strip(), self.shas[-1])
        self.assertIn("return 0", (self.repo / "calc.py").read_text(encoding="utf-8"))

    def test_a_test_command_that_is_not_python_is_refused(self):
        with self.assertRaises(self.module.GitCapabilityError) as caught:
            self.module.run_bisect({"repo_path": "repo", "good": self.shas[0],
                                    "bad": self.shas[2], "test_argv": ["sh", "-c", "exit 0"],
                                    "output_path": "out/bisect.json"}, self.root)
        self.assertIn("TEST_ARGV_EXECUTABLE_NOT_PYTHON", str(caught.exception))

    # --------------------------------------------------------------------- land

    def test_land_commits_on_a_branch_and_does_not_move_the_callers_head(self):
        diff = self.repo / "fix.diff"
        diff.write_text(FIX_DIFF, encoding="utf-8")
        result = self.module.run_land({
            "repo_path": "repo", "branch_name": "brain/fix-add", "message": "fix add",
            "diff_path": "repo/fix.diff", "test_argv": TEST_ARGV_OK,
            "output_path": "out/land.json",
        }, self.root)
        self.assertTrue(result["output_verified"])
        self.assertTrue(result["diff_applied"])
        self.assertTrue(result["tests_passed"])
        self.assertTrue(result["head_restored"])
        self.assertEqual(result["changed_paths"], ["calc.py"])
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").strip(), self.shas[-1])
        self.assertEqual(_git(self.repo, "rev-parse", "brain/fix-add").strip(),
                         result["commit_sha"])
        self.assertEqual(_git(self.repo, "show", "brain/fix-add:calc.py").strip().splitlines()[-1],
                         "    return a + b")

    def test_land_red_undoes_branch_diff_and_tree(self):
        (self.repo / "fix.diff").write_text(FIX_DIFF, encoding="utf-8")
        with self.assertRaises(self.module.GitCapabilityError) as caught:
            self.module.run_land({
                "repo_path": "repo", "branch_name": "brain/red", "message": "red",
                "diff_path": "repo/fix.diff", "test_argv": TEST_ARGV_RED,
                "output_path": "out/land.json",
            }, self.root)
        self.assertIn("TESTS_RED_BEFORE_COMMIT", str(caught.exception))
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").strip(), self.shas[-1])
        self.assertEqual(_git(self.repo, "status", "--porcelain", "--untracked-files=no"), "")
        branches = _git(self.repo, "branch", "--format=%(refname:short)").split()
        self.assertNotIn("brain/red", branches)
        self.assertIn("main", branches)

    def test_land_refuses_a_diff_that_does_not_apply(self):
        (self.repo / "wrong.diff").write_text(
            FIX_DIFF.replace("return a * b", "return a / b"), encoding="utf-8")
        with self.assertRaises(self.module.GitCapabilityError) as caught:
            self.module.run_land({
                "repo_path": "repo", "branch_name": "brain/nope", "message": "nope",
                "diff_path": "repo/wrong.diff", "test_argv": TEST_ARGV_OK,
                "output_path": "out/land.json",
            }, self.root)
        self.assertIn("DIFF_DOES_NOT_APPLY", str(caught.exception))
        self.assertEqual(_git(self.repo, "status", "--porcelain", "--untracked-files=no"), "")
        self.assertNotIn("brain/nope",
                         _git(self.repo, "branch", "--format=%(refname:short)").split())


    # --------------------------------------------------------------- derivation

    def test_a_sentence_is_turned_into_queries_deterministically(self):
        log = self.module.derive_queries("show me the last three commits", self.repo)
        self.assertEqual([q["kind"] for q in log], ["log"])
        self.assertEqual(log[0]["max_count"], 3)
        changed = self.module.derive_queries("what changed in the working tree", self.repo)
        self.assertEqual([q["kind"] for q in changed], ["status", "diff"])
        tracked = self.module.derive_queries("list the tracked files", self.repo)
        self.assertEqual([q["kind"] for q in tracked], ["ls_files"])

    def test_a_sentence_about_nothing_the_lane_reads_refuses(self):
        with self.assertRaises(self.module.GitCapabilityError) as caught:
            self.module.run_inspect({"repo_path": "repo", "goal": "make me a sandwich",
                                     "output_path": "out/i.json"}, self.root)
        self.assertIn("QUERY_KIND_UNDERIVED", str(caught.exception))

    def test_a_read_request_may_not_be_answered_for_a_write_sentence(self):
        for sentence in ("commit the staged changes with the message fix add",
                         "create a branch and commit the fix"):
            with self.assertRaises(self.module.GitCapabilityError) as caught:
                self.module.run_inspect({"repo_path": "repo", "goal": sentence,
                                         "output_path": "out/i.json"}, self.root)
            self.assertIn("READ_CAPABILITY_REFUSES_WRITE_REQUEST", str(caught.exception))

    def test_inspect_writes_its_own_artifact_when_the_sentence_names_none(self):
        result = self.module.run_inspect({"repo_path": "repo",
                                          "goal": "show git status"}, self.root)
        self.assertTrue(result["output_verified"])
        self.assertIn("canonical/astra_runtime/tmp/git_lane/inspect_", result["output_path"])
        self.assertTrue(pathlib.Path(result["output_path"]).is_file())

    def test_bisect_infers_the_range_and_the_suites_from_the_sentence(self):
        result = self.module.run_bisect({"repo_path": "repo",
                                         "goal": "which commit broke the test suite"},
                                        self.root)
        self.assertTrue(result["output_verified"])
        self.assertEqual(result["first_bad_commit"], self.shas[1])
        artifact = json.loads(pathlib.Path(result["output_path"]).read_text(encoding="utf-8"))
        self.assertTrue(artifact["good_inferred_as_root_commit"])
        self.assertEqual(artifact["test_argv_derivation"], "repository_suites")
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").strip(), self.shas[-1])

    def test_bisect_refuses_a_write_sentence(self):
        with self.assertRaises(self.module.GitCapabilityError) as caught:
            self.module.run_bisect({"repo_path": "repo",
                                    "goal": "commit the staged changes"}, self.root)
        self.assertIn("BISECT_REFUSES_WRITE_REQUEST", str(caught.exception))

    def test_bisect_refuses_a_range_it_cannot_finish_in_max_steps(self):
        with self.assertRaises(self.module.GitCapabilityError) as caught:
            self.module.run_bisect({"repo_path": "repo", "good": self.shas[0],
                                    "bad": self.shas[2], "test_argv": TEST_ARGV_OK,
                                    "max_steps": 1, "output_path": "out/b.json"}, self.root)
        self.assertIn("BISECT_RANGE_EXCEEDS_MAX_STEPS", str(caught.exception))
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").strip(), self.shas[-1])


    # ------------------------------------------------- reachability through the door

    def test_the_lane_is_reachable_through_the_live_dispatch_door(self):
        """A capability the door cannot invoke is not a capability.

        `run_adapter_locally` hands the adapter the repository root it belongs to, so this
        test reads *this* repository -- read-only, one rev-parse -- and writes its artifact
        under the repository's gitignored scratch directory, which it removes afterwards.
        """
        import tempfile

        from canonical.runtime import live_brain_route_admission_v1 as admission
        scratch = pathlib.Path(tempfile.mkdtemp(prefix="brain_git_door_",
                                                 dir=str(REPO_ROOT / "canonical" / "astra_runtime" / "tmp")))
        self.addCleanup(shutil.rmtree, scratch, True)
        out_rel = str(scratch.relative_to(REPO_ROOT) / "door.json")
        expected = _git(REPO_ROOT, "rev-parse", "HEAD").strip()
        entry = {
            "capability_id": "git.repository.inspect.v1",
            "adapter_module": "git_object_model_v1",
            "entrypoint": "run_inspect",
            "source": {"adapter_path": str(MODULE_PATH), "type": "system_tool", "module": "git"},
            "incremental_spend_usd": 0,
        }
        action = {
            "type": "invoke_capability",
            "args": {"capability_id": "git.repository.inspect.v1", "repo_path": ".",
                     "queries": [{"kind": "rev_parse", "rev": "HEAD"}],
                     "output_path": out_rel},
            "expect": {"field": "output_verified", "type": "field_equals", "value": True},
        }
        with contextlib.redirect_stdout(io.StringIO()):
            result = admission.run_adapter_locally(entry, action)
        self.assertTrue(result["output_verified"])
        self.assertEqual(result["head"], expected)


    def test_a_goal_sentence_compiles_to_this_lane_and_runs_through_the_door(self):
        """The whole path a user request travels: sentence -> compiler -> door -> git.

        This is the measurement the lane exists for.  On 87cecd5 ten ordinary
        software-engineering sentences reached zero capabilities; "show me the last three
        commits" now names this capability and the artifact it produces carries the three
        commits that are really in HEAD's history.
        """
        import tempfile

        from canonical.runtime import goal_compiler
        from canonical.runtime import live_brain_route_admission_v1 as admission

        caps = json.loads((REPO_ROOT / "canonical" / "runtime" /
                           "BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))["capabilities"]
        compiled = goal_compiler.compile_goal("show me the last three commits", caps, REPO_ROOT)
        self.assertEqual(compiled["selected_capability"], "git.repository.inspect.v1")
        row = caps["git.repository.inspect.v1"]
        scratch = pathlib.Path(tempfile.mkdtemp(prefix="brain_git_goal_",
                                                 dir=str(REPO_ROOT / "canonical" / "astra_runtime" / "tmp")))
        self.addCleanup(shutil.rmtree, scratch, True)
        entry = {"capability_id": compiled["selected_capability"],
                 "adapter_module": row["adapter_module"], "entrypoint": row["entrypoint"],
                 "source": row["source"], "incremental_spend_usd": 0}
        action = {"type": "invoke_capability",
                  "args": {"capability_id": compiled["selected_capability"],
                           "goal": compiled["inputs"]["goal"],
                           "output_path": str(scratch.relative_to(REPO_ROOT) / "goal.json")},
                  "expect": {"field": "output_verified", "type": "field_equals", "value": True}}
        with contextlib.redirect_stdout(io.StringIO()):
            result = admission.run_adapter_locally(entry, action)
        self.assertTrue(result["output_verified"])
        artifact = json.loads((scratch / "goal.json").read_text(encoding="utf-8"))
        expected = _git(REPO_ROOT, "log", "-n", "3", "--format=%H").split()
        self.assertEqual([e["sha"] for e in artifact["results"][0]["entries"]], expected)


if __name__ == "__main__":
    unittest.main()
