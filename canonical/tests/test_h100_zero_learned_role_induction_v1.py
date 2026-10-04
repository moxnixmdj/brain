from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.h100_zero_learned_role_induction_v1 import (
    RoleInductionError,
    induce_roles,
)

PRE = Path(__file__).resolve().parents[1] / "governance" / "H100_ZERO_LEARNED_ROLE_INDUCTION_PREEXPOSURE_V1.json"


class H100ZeroLearnedRoleInductionTests(unittest.TestCase):
    def test_all_frozen_tasks_match_exact_expected_roles_or_abstention(self):
        doc = json.loads(PRE.read_text())
        self.assertEqual(len(doc["tasks"]), 6)
        for task in doc["tasks"]:
            out = induce_roles(task["payload"], format_hint=task["format"])
            self.assertEqual(out["status"], task["expected_status"], task["task_id"])
            self.assertEqual(out["inputs"], task["expected_inputs"], task["task_id"])
            self.assertEqual(out["target"], task["expected_target"], task["task_id"])
            self.assertEqual(out["persistent_learned_bytes"], 0)
            self.assertEqual(out["external_frontier_model_calls"], 0)
            self.assertEqual(out["external_learned_capability_calls"], 0)

    def test_perfect_observational_predictability_does_not_create_direction(self):
        out = induce_roles(
            [{"a":1.0,"b":2.0},{"a":2.0,"b":4.0},{"a":3.0,"b":6.0}],
            format_hint="UNLABELED_TABLE",
        )
        self.assertEqual(out["status"], "ABSTAIN_DIRECTION_NOT_IDENTIFIED")
        self.assertEqual(out["inputs"], [])
        self.assertIsNone(out["target"])

    def test_multiple_result_fields_fail_closed(self):
        with self.assertRaisesRegex(RoleInductionError, "TARGET_NOT_UNIQUE"):
            induce_roles(
                [{"arguments":{"x":1.0},"result":{"y":2.0,"z":3.0}}],
                format_hint="TOOL_TRACE",
            )

    def test_schema_drift_fails_closed(self):
        with self.assertRaisesRegex(RoleInductionError, "TOOL_ROLE_SCHEMA_DRIFT"):
            induce_roles(
                [
                    {"arguments":{"x":1.0},"result":{"y":2.0}},
                    {"arguments":{"x":2.0,"q":3.0},"result":{"y":4.0}},
                ],
                format_hint="TOOL_TRACE",
            )

    def test_no_lexical_guess_without_declared_structural_cue(self):
        with self.assertRaisesRegex(RoleInductionError, "UNSUPPORTED_OR_MISSING_FORMAT_HINT"):
            induce_roles([{"input_guess":1.0,"target_guess":2.0}], format_hint="MYSTERY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
