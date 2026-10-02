from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.objective_route_promotion_transition import validate_promotion_transition


SPECS = (
    (
        "canonical/governance/BROWSER_T2_OBJECTIVE_TERMINAL_BINDING_V1.json",
        "BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001",
        "FROZEN_PREWAVE_BINDING__SELECTION_KERNEL_REBOUND__INDEPENDENT_VERIFICATION_PENDING__ZERO_TERMINAL_RESULTS",
        "FROZEN_PREWAVE_BINDING__INDEPENDENT_PUBLIC_RUNNER_PASS__ZERO_TERMINAL_RESULTS",
    ),
    (
        "canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json",
        "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001",
        "FROZEN_PREWAVE_BINDING__SELECTION_KERNEL_REBOUND__TRANSITIVE_DEPENDENCY_CONE_HARDENED__INDEPENDENT_VERIFICATION_PENDING__ZERO_TERMINAL_RESULTS",
        "FROZEN_PREWAVE_BINDING__INDEPENDENT_PUBLIC_RUNNER_PASS__ZERO_TERMINAL_RESULTS",
    ),
    (
        "canonical/governance/RESEARCH_T3_OBJECTIVE_TERMINAL_BINDING_V1.json",
        "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001",
        "FROZEN_PREWAVE_BINDING__SELECTION_KERNEL_REBOUND__INDEPENDENT_VERIFICATION_PENDING__ZERO_TERMINAL_RESULTS",
        "FROZEN_PREWAVE_BINDING__SELECTION_KERNEL_REBOUND__INDEPENDENT_PASS__PREWAVE_ADMISSIBLE__ZERO_TERMINAL_RESULTS",
    ),
)


class ObjectiveRoutePromotionTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[2]

    def _binding(self, path: str):
        return json.loads((self.root / path).read_text(encoding="utf-8"))

    def test_all_live_promotions_reconstruct_exact_receipt_bound_bases(self):
        for path, behavior, pre_status, promoted_status in SPECS:
            with self.subTest(behavior=behavior):
                errors = validate_promotion_transition(
                    self.root,
                    self._binding(path),
                    binding_path=path,
                    behavior_id=behavior,
                    prepromotion_status=pre_status,
                    promoted_status=promoted_status,
                )
                self.assertEqual(errors, [])

    def test_nonpromotion_mutation_breaks_receipt_bound_base_hash(self):
        path, behavior, pre_status, promoted_status = SPECS[0]
        binding = copy.deepcopy(self._binding(path))
        binding["proof_mode"] = binding["proof_mode"] + "__MUTATED"
        errors = validate_promotion_transition(
            self.root,
            binding,
            binding_path=path,
            behavior_id=behavior,
            prepromotion_status=pre_status,
            promoted_status=promoted_status,
        )
        self.assertTrue(
            any(x.startswith("PROMOTION_TRANSITION_BASE_SHA_MISMATCH:") for x in errors),
            errors,
        )

    def test_promotion_state_pair_must_match(self):
        path, behavior, pre_status, promoted_status = SPECS[1]
        binding = copy.deepcopy(self._binding(path))
        binding["prewave_admissible"] = False
        errors = validate_promotion_transition(
            self.root,
            binding,
            binding_path=path,
            behavior_id=behavior,
            prepromotion_status=pre_status,
            promoted_status=promoted_status,
        )
        self.assertIn("PREWAVE_ADMISSIBILITY_VERIFICATION_STATE_MISMATCH", errors)


if __name__ == "__main__":
    unittest.main()
