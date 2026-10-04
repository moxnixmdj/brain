from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.h100_jit_lexical_role_v1 import (
    JITLexicalRoleError,
    induce_roles,
)

ROOT=Path(__file__).resolve().parents[1]
PRE=ROOT/"governance"/"H100_JIT_LEXICAL_ROLE_PREEXPOSURE_V1.json"
KNOW=ROOT/"governance"/"H100_JIT_LEXICAL_RAW_KNOWLEDGE_V1.json"


class H100JITLexicalRoleTests(unittest.TestCase):
    def test_all_preexposed_tasks_exact(self):
        pre=json.loads(PRE.read_text())
        knowledge=json.loads(KNOW.read_text())
        self.assertEqual(len(pre["tasks"]),5)
        for task in pre["tasks"]:
            out=induce_roles(task["clauses"],knowledge)
            self.assertEqual(out["status"],task["expected_status"],task["task_id"])
            self.assertEqual(out["inputs"],task["expected_inputs"],task["task_id"])
            self.assertEqual(out["target"],task["expected_target"],task["task_id"])
            self.assertEqual(out["persistent_learned_bytes"],0)
            self.assertEqual(out["external_frontier_model_calls"],0)
            self.assertEqual(out["external_learned_capability_calls"],0)

    def test_arbitrary_new_tokens_work_without_runtime_changes(self):
        knowledge={
            "anchors":{"input":"input","target":"output"},
            "edges":[
                ["never_seen_a","bridge_x"],["bridge_x","input"],
                ["never_seen_b","bridge_y"],["bridge_y","output"],
            ],
        }
        out=induce_roles([
            {"cue":"never_seen_b","fields":["z"]},
            {"cue":"never_seen_a","fields":["x","y"]},
        ],knowledge)
        self.assertEqual(out["status"],"ROLES_IDENTIFIED")
        self.assertEqual(out["inputs"],["x","y"])
        self.assertEqual(out["target"],"z")

    def test_order_does_not_assign_role(self):
        knowledge=json.loads(KNOW.read_text())
        out=induce_roles([
            {"cue":"cue_d","fields":["z"]},
            {"cue":"cue_a","fields":["x","y"]},
        ],knowledge)
        self.assertEqual(out["inputs"],["x","y"])
        self.assertEqual(out["target"],"z")

    def test_ambiguous_graph_abstains(self):
        knowledge=json.loads(KNOW.read_text())
        out=induce_roles([
            {"cue":"cue_ambiguous","fields":["x"]},
            {"cue":"cue_e","fields":["y"]},
        ],knowledge)
        self.assertEqual(out["status"],"ABSTAIN_LEXICAL_ROLE_AMBIGUOUS")

    def test_disconnected_cue_abstains(self):
        knowledge=json.loads(KNOW.read_text())
        out=induce_roles([
            {"cue":"not_in_graph","fields":["x"]},
            {"cue":"cue_d","fields":["y"]},
        ],knowledge)
        self.assertEqual(out["status"],"ABSTAIN_LEXICAL_ROLE_UNKNOWN")

    def test_target_cardinality_abstains(self):
        knowledge=json.loads(KNOW.read_text())
        out=induce_roles([
            {"cue":"cue_a","fields":["x"]},
            {"cue":"cue_d","fields":["y","z"]},
        ],knowledge)
        self.assertEqual(out["status"],"ABSTAIN_ROLE_CARDINALITY")

    def test_anchor_collision_rejected(self):
        with self.assertRaisesRegex(JITLexicalRoleError,"ROLE_ANCHORS_COLLIDE"):
            induce_roles(
                [{"cue":"a","fields":["x"]},{"cue":"b","fields":["y"]}],
                {"anchors":{"input":"same","target":"same"},"edges":[]},
            )

    def test_cycles_are_bounded_and_deterministic(self):
        knowledge={
            "anchors":{"input":"input","target":"output"},
            "edges":[["a","b"],["b","c"],["c","a"],["c","input"],["d","output"]],
        }
        out=induce_roles([
            {"cue":"a","fields":["x"]},
            {"cue":"d","fields":["y"]},
        ],knowledge)
        self.assertEqual(out["status"],"ROLES_IDENTIFIED")
        self.assertEqual(out["inputs"],["x"])
        self.assertEqual(out["target"],"y")


if __name__=="__main__":
    unittest.main(verbosity=2)
