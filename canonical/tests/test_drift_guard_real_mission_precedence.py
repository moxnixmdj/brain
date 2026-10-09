from __future__ import annotations

import unittest

from canonical.runtime.enforce_goal_hierarchy import terminal_objective_currentness_errors


REAL = "BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE"
CHECKPOINT = "PERMANENTLY_INTERNALIZE_CONFIGURE_VERIFY_AND_OWN_ALL_USEFUL_OPUS_5_5_CAPABILITIES_AT_EQUAL_OR_BETTER_LEVEL__KNOWLEDGE_EXTERNAL_JIT_ONLY"


class TestDriftGuardRealMissionPrecedence(unittest.TestCase):
    def mission(self, *, role="FIRST_FRONTIER_CHECKPOINT_NOT_TERMINAL_OBJECTIVE"):
        return {"real_objective": REAL, "opus_5_5_role": role}

    def pointer(self):
        return {"mission_lock": {"terminal_objective": CHECKPOINT}}

    def test_real_mission_intent_with_legacy_checkpoint_hierarchy_passes(self):
        errors = terminal_objective_currentness_errors(
            self.mission(),
            self.pointer(),
            {"terminal_objective": CHECKPOINT},
            {"terminal_objective": REAL},
        )
        self.assertEqual(errors, [])

    def test_real_mission_hierarchy_and_intent_pass(self):
        errors = terminal_objective_currentness_errors(
            self.mission(),
            self.pointer(),
            {"terminal_objective": REAL},
            {"terminal_objective": REAL},
        )
        self.assertEqual(errors, [])

    def test_legacy_checkpoint_cannot_remain_intent_terminal_objective(self):
        errors = terminal_objective_currentness_errors(
            self.mission(),
            self.pointer(),
            {"terminal_objective": CHECKPOINT},
            {"terminal_objective": CHECKPOINT},
        )
        self.assertIn("INTENT_REAL_MISSION_OBJECTIVE_MISMATCH", errors)

    def test_legacy_hierarchy_requires_explicit_checkpoint_role(self):
        errors = terminal_objective_currentness_errors(
            self.mission(role=""),
            self.pointer(),
            {"terminal_objective": CHECKPOINT},
            {"terminal_objective": REAL},
        )
        self.assertIn("HIERARCHY_OBJECTIVE_NOT_REAL_MISSION_OR_DECLARED_CHECKPOINT", errors)

    def test_arbitrary_hierarchy_objective_fails(self):
        errors = terminal_objective_currentness_errors(
            self.mission(),
            self.pointer(),
            {"terminal_objective": "OTHER"},
            {"terminal_objective": REAL},
        )
        self.assertIn("HIERARCHY_OBJECTIVE_NOT_REAL_MISSION_OR_DECLARED_CHECKPOINT", errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
