"""A benchmark harness must be shown to discriminate, or it is a script that prints green.

The thing this file pins down is narrow and worth stating plainly. Fetching a task definition
and replaying its gold patch proves nothing about this system -- it grades the benchmark's own
answer sheet. What it *does* prove is that the harness can tell a broken tree from a fixed one.
If both states came back RESOLVED, every future measurement through this harness would be
worthless and would look fine.

Measured 2026-11-24 (§A152), on
`instance_ansible__ansible-0ea40e09...-v30a923fb...`:

    pre-fix  (published test patch only)  1 failed, 15 passed   RESOLVED = False
    post-fix (+ published gold patch)     16 passed             RESOLVED = True

Three defects were found while building it, and each is asserted below because each one made
the harness *silently agree with itself*:

1. The sha in the instance name is the **fix commit**, not the base. A tree at that sha already
   contains the fix, so the test patch does not apply and a "baseline" passes. The base is the
   fix commit's parent, and it is asked for rather than derived.
2. `raw.githubusercontent.com` is unreachable here (HTTP 000). urllib raises a TLS EOF, curl
   returns nothing. Every file is read through `api.github.com`, which is reachable and serves
   the same bytes base64-encoded.
3. `pytest -q` prints no per-test line, and `-v` lines are only readable if the repo's import
   roots are on `PYTHONPATH`. Without them every test is `null` -- not failed, not passed,
   simply never run -- and a parser that treats "not seen" as "failed" reports a total failure
   that did not happen.

The harness is offline by default in this test: no network, no 24 MB download. It exercises the
parts that decide an answer from data already on disk, and the one networked claim (that the
base is the fix's parent) is asserted against the recorded measurement, not re-fetched.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import textwrap
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import swepro_instance_harness_v1 as H  # noqa: E402

INSTANCE = ("instance_ansible__ansible-0ea40e09d1b35bcb69ff4d9cecf3d0defa4b36e8"
            "-v30a923fb5c164d6cd18280c02422f75e611e8fb2")


class TheInstanceNameDoesNotCarryTheBase(unittest.TestCase):
    def test_the_leading_sha_is_split_out_with_its_repo(self) -> None:
        slug, sha = H._sha_from_instance(INSTANCE)
        self.assertEqual(slug, "ansible/ansible")
        self.assertEqual(sha, "0ea40e09d1b35bcb69ff4d9cecf3d0defa4b36e8")

    def test_an_unparseable_id_is_refused_rather_than_guessed(self) -> None:
        """A wrong base commit produces a run that looks correct and is not."""
        with self.assertRaises(ValueError):
            H._sha_from_instance("instance_broken")

    def test_the_base_is_the_parent_of_the_fix_not_the_fix(self) -> None:
        """The recorded measurement, asserted so a future edit cannot quietly invert it.

        `0ea40e09` is 'vars: handle exception in combine_vars (#81700)'. Its parent
        `f7234968` is the tree where the published test patch applies and the published
        failure reproduces. If `resolve_base_commit` ever returns the fix sha, the harness
        would report a baseline that already contains the repair.
        """
        self.assertNotEqual(
            H.resolve_base_commit.__doc__.count("NOT the sha in the instance name"), 0,
            "the docstring must say which sha is the base, or the next reader repeats the defect",
        )
        # It must ask the API for parents, never slice the instance id.
        source = pathlib.Path(H.__file__).read_text(encoding="utf-8")
        body = source.split("def resolve_base_commit", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("parents", body)
        self.assertNotIn("instance_id", body)


class TheGraderCountsWhatActuallyRan(unittest.TestCase):
    """`-q` output has no per-test lines; a silent parser grades everything unmet."""

    def setUp(self) -> None:
        self.room = pathlib.Path(tempfile.mkdtemp(prefix="grade_room_", dir=REPO / "canonical" / "astra_runtime" / "tmp"))
        (self.room / "test_sample.py").write_text(textwrap.dedent("""
            def test_passes():
                assert True

            def test_fails():
                assert False
        """), encoding="utf-8")

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.room, ignore_errors=True)

    def test_a_passing_and_a_failing_test_are_told_apart(self) -> None:
        rep = H.grade(self.room, ["test_sample.py::test_passes"],
                      ["test_sample.py::test_fails"])
        self.assertTrue(rep["f2p_passed"])
        self.assertFalse(rep["p2p_passed"])
        self.assertFalse(rep["resolved"])
        self.assertEqual(rep["unseen"], [], "both tests ran; nothing may be 'unseen'")

    def test_a_test_that_never_ran_is_not_reported_as_passing(self) -> None:
        """The `-q` defect: no per-test line means the id is absent, not that it passed."""
        rep = H.grade(self.room, ["test_sample.py::test_does_not_exist"], [])
        self.assertFalse(rep["f2p_passed"])
        self.assertFalse(rep["resolved"])
        self.assertEqual(rep["unseen"], ["test_does_not_exist"],
                         "a test that was never collected must be named as unseen, not silently failed")

    def test_an_import_failure_is_visible_and_not_counted_as_a_pass(self) -> None:
        (self.room / "test_broken.py").write_text(
            "import definitely_not_a_real_module_xyz\n\n\ndef test_x():\n    pass\n", encoding="utf-8")
        rep = H.grade(self.room, ["test_broken.py::test_x"], [])
        self.assertFalse(rep["f2p_passed"])
        self.assertTrue(rep["import_error"], rep)


class TheHarnessCannotGradeItsOwnAnswerSheet(unittest.TestCase):
    def test_the_module_says_out_loud_that_it_is_not_a_solver(self) -> None:
        """§6 asks for the agent's patch. Replaying the gold patch grades the answer sheet."""
        doc = (H.__doc__ or "").lower()
        self.assertIn("does **not** solve", doc)
        self.assertIn("answer sheet", doc)

    def test_the_offline_network_claim_is_recorded_not_hidden(self) -> None:
        source = pathlib.Path(H.__file__).read_text(encoding="utf-8")
        self.assertIn("raw.githubusercontent.com", source)
        self.assertIn("api.github.com", source)


if __name__ == "__main__":
    unittest.main()
