from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.h100_zero_learned_semantic_paraphrase_v1 import (
    SemanticRoleError,
    induce_semantic_roles,
)

PRE=Path(__file__).resolve().parents[1]/"governance"/"H100_ZERO_LEARNED_SEMANTIC_PARAPHRASE_PREEXPOSURE_V1.json"

class H100ZeroLearnedSemanticParaphraseTests(unittest.TestCase):
    def test_all_frozen_tasks_exact(self):
        doc=json.loads(PRE.read_text())
        self.assertEqual(len(doc["tasks"]),10)
        for task in doc["tasks"]:
            out=induce_semantic_roles(task["text"])
            self.assertEqual(out["status"],task["expected_status"],task["task_id"])
            self.assertEqual(out["inputs"],task["expected_inputs"],task["task_id"])
            self.assertEqual(out["target"],task["expected_target"],task["task_id"])
            self.assertEqual(out["persistent_learned_bytes"],0)
            self.assertEqual(out["external_frontier_model_calls"],0)
            self.assertEqual(out["external_learned_capability_calls"],0)

    def test_one_sided_role_cue_abstains(self):
        out=induce_semantic_roles("Inputs: a, b; values are listed.")
        self.assertEqual(out["status"],"ABSTAIN_DIRECTION_NOT_IDENTIFIED")

    def test_association_never_infers_direction(self):
        out=induce_semantic_roles("Variables x and y are perfectly associated.")
        self.assertEqual(out["status"],"ABSTAIN_DIRECTION_NOT_IDENTIFIED")

    def test_overlap_fails_closed(self):
        with self.assertRaisesRegex(SemanticRoleError,"INPUT_TARGET_OVERLAP"):
            induce_semantic_roles("Inputs: x, y; result: y.")

if __name__=="__main__":
    unittest.main(verbosity=2)
