"""A read cannot be the answer to a rewrite, and the row's own operation set decides.

Measured 2026-10-31 on `main` 4b1baa2, through ``live_brain_route_admission_v1.solve``:

    "Revert the last commit"              -> PASS, op=log          (V3 §3, row 34)
    "Reset the working tree to HEAD~1"    -> PASS, op=status
    "Stash the working tree changes"      -> PASS, op=status
    "Push the current branch to origin"   -> PASS, op=branch

Four sentences, four certified lies: the row's own ``limitations`` say *"Seven declared
operations only (log, status, diff, show, blame, branch, commit) ... any other operation is
refused by name"* and *"No push, rebase, merge, reset or history rewrite."*  The verb was never
read.  ``_GIT_OPERATION_GRAMMAR`` matches PHRASES, so "the working tree" bound ``status`` and
"the current branch" bound ``branch``, and the row that refuses an undeclared operation by name
was never asked -- the binder had already substituted a different one.

The binder now binds the sentence's own verb when that verb names a repository operation the
grammar does not implement.  Nothing else moves: an operation the row DOES implement keeps the
grammar's reading, so "Show the last three git commits" is still ``log`` (its verb is ``show``)
and "Commit the staged changes" is still ``commit``.

Four assertions, each an independent oracle:

  * the leading imperative is read, and only when it is a git subcommand;
  * the binding for a rewrite verb is that verb, not the noun phrase beside it;
  * a stated operation the row does not declare is refused BY NAME, by the adapter itself;
  * every sentence that worked before this rule binds exactly what it bound before.
"""
from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_selection_retrieval_v1 as selection  # noqa: E402
from canonical.runtime import declared_input_derivation_v1 as derivation  # noqa: E402
from canonical.runtime.bound_capabilities import git_repository_operate as git_operate  # noqa: E402

GIT_ROW = "git.repository.operate.v1"
REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"


def _entry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"][GIT_ROW]


class TheVerbIsTheOperation(unittest.TestCase):
    def test_the_leading_imperative_is_read_and_only_when_it_is_a_git_operation(self) -> None:
        cases = {
            "Reset the working tree to HEAD~1": "reset",
            "Please reset the working tree": "reset",
            "Could you push the current branch to origin": "push",
            "Revert the last commit": "revert",
            "Show the last three git commits": "show",
            "Commit the transaction to the database": "commit",
        }
        for goal, verb in cases.items():
            self.assertEqual(derivation.stated_git_operation(goal), verb, goal)
        # A question, a lookup, and a path do not state an operation at all.
        for goal in ("Which commit broke the tests",
                     "Find every caller of build_plan in pkg/x.py",
                     "List the branches",
                     "Explain why the push failed",
                     "pkg/x.py is broken"):
            self.assertIsNone(derivation.stated_git_operation(goal), goal)

    def test_a_rewrite_verb_binds_itself_not_the_noun_phrase_beside_it(self) -> None:
        entry = _entry()
        for goal, op in (("Reset the working tree to HEAD~1", "reset"),
                         ("Stash the working tree changes", "stash"),
                         ("Push the current branch to origin", "push"),
                         ("Revert the last commit", "revert")):
            bound = derivation.derive(goal, entry, ROOT).get("op") or {}
            self.assertEqual(bound.get("value"), op, goal)

    def test_every_operation_that_worked_before_binds_exactly_what_it_bound_before(self) -> None:
        entry = _entry()
        for goal, op in (("Show the last three git commits", "log"),
                         ("List the branches", "branch"),
                         ("Show the status of the working tree", "status"),
                         ("What changed in the last 5 commits", "log"),
                         ("Commit the staged changes", "commit")):
            bound = derivation.derive(goal, entry, ROOT).get("op") or {}
            self.assertEqual(bound.get("value"), op, goal)
        # No repository context: still no operation at all.
        self.assertNotIn("op", derivation.derive("Commit the transaction to the database",
                                                 entry, ROOT))

    def test_the_admission_layer_binds_the_stated_operation(self) -> None:
        admitted = selection.admit("Reset the working tree to HEAD~1", GIT_ROW, _entry(), ROOT)
        self.assertTrue(admitted.get("admitted"), admitted)
        self.assertEqual((admitted.get("inputs") or {}).get("op"), "reset")


class TheRowRefusesItByName(unittest.TestCase):
    def test_an_operation_the_adapter_does_not_declare_is_refused_with_its_name(self) -> None:
        for op in ("reset", "stash", "push", "revert"):
            with self.assertRaises(git_operate.GitOperateError) as caught:
                git_operate.run({"op": op, "repo_root": ".", "limit": 3}, ROOT)
            message = str(caught.exception)
            self.assertIn("OP_NOT_DECLARED:" + op, message)
            self.assertIn("declared=log,status,diff,show,blame,branch,commit", message)


if __name__ == "__main__":
    unittest.main()
