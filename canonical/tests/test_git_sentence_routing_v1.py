# PROJECT_BRAIN
"""Two door laws, measured 2026-10-29 on c79a8f5.

1. **A repository FILE is not a capability.** ``load_verified_registry`` admits
   293 inventory rows, each keyed by the path of one of this repository's own
   Python files (``canonical/runtime/<module>.py.auto.v1``).  The lexical selector
   treats every token of that filename as evidence about the goal, so
   "Show the last three git commits" selected
   ``cursorbench_three_region_complement_nonidentifiability_v1.py.auto.v1`` on the
   single word ``three`` and returned
   ``PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED`` with
   ``semantic_acceptance_complete: true`` and ``independent_reinspection: true``.
   No commit was read: a set-theory verifier ran and its own stdout said
   ``"pass": true`` about set theory.  ``"three"`` alone did the same.  A sentence
   that NAMES the path still reaches it, because naming a file is a request about
   that file.

2. **A stated git operation reaches the git capability.** "Show the last three git
   commits" derived ``op=log`` from its own verb and ``limit=3`` from its own
   number, and the tree it read is the real one.

Run: python -m pytest canonical/tests/test_git_sentence_routing_v1.py -q
"""

from __future__ import annotations

import json
import unittest

from canonical.runtime import live_brain_route_admission_v1 as door

_INVENTORY_ID = ("canonical/runtime/cursorbench_three_region_complement_"
                 "nonidentifiability_v1.py.auto.v1")


def _compiled(cid: str) -> dict:
    return {"selected_capability": cid,
            "compiler_mode": "DETERMINISTIC_VERIFIED_CAPABILITY_MATCH"}


class InventoryRowIsNotACapability(unittest.TestCase):

    def test_a_common_word_does_not_route_to_a_repository_file(self):
        for goal in ("Show the last three git commits",
                     "three",
                     "Show the last seven git commits",
                     "three region complement nonidentifiability"):
            verdict = door.route_admission(goal, _compiled(_INVENTORY_ID),
                                           {_INVENTORY_ID: {}})
            self.assertFalse(verdict["admitted"], goal)
            self.assertEqual(verdict["rule"],
                             "INVENTORY_FILE_IS_NOT_A_CAPABILITY_UNLESS_THE_SENTENCE_NAMES_IT",
                             goal)

    def test_naming_the_file_still_reaches_it(self):
        goal = ("Show the last three git commits from "
                "canonical/runtime/cursorbench_three_region_complement_"
                "nonidentifiability_v1.py")
        verdict = door.route_admission(goal, _compiled(_INVENTORY_ID),
                                       {_INVENTORY_ID: {}})
        # admitted or refused for some OTHER honest reason, but never by this rule
        self.assertNotEqual(verdict.get("rule"),
                            "INVENTORY_FILE_IS_NOT_A_CAPABILITY_UNLESS_THE_SENTENCE_NAMES_IT")

    def test_a_real_capability_id_is_untouched_by_the_rule(self):
        self.assertIsNone(door.inventory_source_path("git.repository.operate.v1"))
        self.assertIsNone(door.inventory_source_path("python.refactor.rename_symbol.v1"))
        self.assertEqual(door.inventory_source_path(_INVENTORY_ID),
                         "canonical/runtime/cursorbench_three_region_complement_"
                         "nonidentifiability_v1.py")


class AStatedGitOperationReachesTheGitCapability(unittest.TestCase):

    def _plan(self, goal: str) -> dict:
        from canonical.runtime import swe_typed_plan_v1 as typed
        return typed.plan_report(goal, door.ROOT)

    def test_the_last_three_commits_binds_log_three(self):
        plan = self._plan("Show the last three git commits")
        self.assertEqual(plan["status"], "DECISIVE_TYPED_PLAN")
        self.assertEqual(plan["selected_capability"], "git.repository.operate.v1")
        self.assertEqual(plan["inputs"]["op"], "log")
        self.assertEqual(plan["inputs"]["limit"], 3)

    def test_the_stated_count_is_honoured_not_ignored(self):
        self.assertEqual(self._plan("Show the last seven git commits")["inputs"]["limit"], 7)
        self.assertEqual(self._plan("show the last 5 commits")["inputs"]["limit"], 5)

    def test_a_commit_imperative_binds_commit(self):
        plan = self._plan("Commit the staged changes with the message 'wip'")
        self.assertEqual(plan["selected_capability"], "git.repository.operate.v1")
        self.assertEqual(plan["inputs"]["op"], "commit")

    def test_a_software_engineering_sentence_never_binds_a_git_operation(self):
        """The family grammar must not capture the SWE corridor it sits beside."""
        from canonical.runtime import declared_input_derivation_v1 as derivation
        for goal in ("Repair the python source pkg/calc.py so that the unit test "
                     "pkg/test_calc.py passes, and save the repair report to a.json.",
                     "Find every caller of the function add in pkg/calc.py",
                     "Rename the parameter old_price to price in pkg/util.py",
                     "Write a unit test for the module pkg/calc.py"):
            self.assertEqual(derivation._GIT_OPERATION_GRAMMAR and
                             [n for n, p in derivation._GIT_OPERATION_GRAMMAR
                              if p.search(goal)], [], goal)


class AMetaphorIsNotARepositoryOperation(unittest.TestCase):
    """Measured 2026-10-29, both of these were false PASSes before the grammar
    was tightened: `op` was derived from a bare noun, so a sentence that merely
    contained the word committed or branched ran a git operation."""

    def _op(self, goal):
        from canonical.runtime import declared_input_derivation_v1 as derivation
        stated = [n for n, p in derivation._GIT_OPERATION_GRAMMAR if p.search(goal)]
        if stated == ["commit"] and not derivation._REPOSITORY_CONTEXT.search(goal):
            return []
        return stated

    def test_a_metaphorical_branch_binds_nothing(self):
        self.assertEqual(self._op("Branch out the new feature into three modules"), [])
        self.assertEqual(self._op("List the branches"), ["branch"])
        self.assertEqual(self._op("which branch am I on"), ["branch"])

    def test_a_database_transaction_is_not_a_commit(self):
        for goal in ("Commit the transaction to the database",
                     "Commit the purchase order",
                     "Commit to the plan"):
            self.assertEqual(self._op(goal), [], goal)
        for goal in ("Commit the staged changes",
                     "commit the changes to the repo",
                     "git commit the fix"):
            self.assertEqual(self._op(goal), ["commit"], goal)

    def test_a_metaphor_never_returns_pass(self):
        """The end-to-end verdict, not just the grammar."""
        for goal in ("Branch out the new feature into three modules",
                     "Commit the transaction to the database"):
            verdict = door.solve({"task_id": "metaphor", "goal": goal})
            self.assertFalse(verdict.get("pass"), goal)


class TheCapabilityIsReal(unittest.TestCase):
    """The repair of the false PASS must be a working capability, not a refusal."""

    def test_the_registry_row_declares_the_operation_contract(self):
        registry = json.loads((door.ROOT / "canonical/runtime/"
                               "BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
        entry = registry["capabilities"]["git.repository.operate.v1"]
        self.assertEqual(entry["status"], "VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(entry["incremental_spend_usd"], 0)
        self.assertEqual(sorted(entry["action_template"]["args"]),
                         ["capability_id", "limit", "op"])
        self.assertIn("git.history.read", entry["provides"])
        self.assertTrue(entry["source"]["adapter_path"].endswith("git_repository_operate.py"))

    def test_the_adapter_covers_every_declared_operation(self):
        from canonical.runtime.bound_capabilities import git_repository_operate as git_op
        self.assertEqual(tuple(git_op.OPS),
                         ("log", "status", "diff", "show", "blame", "branch", "commit"))
        self.assertEqual(set(git_op._READERS), set(git_op.OPS))


if __name__ == "__main__":
    unittest.main()
