from __future__ import annotations

import unittest

from canonical.runtime import assurance_closure_compiler_v1 as c


def evidence(node_id: str = "e"):
    return {
        "id": node_id,
        "type": "EVIDENCE",
        "status": "SUPPORTED",
        "authoritative_leaf": True,
    }


def closed_graph():
    return {
        "schema": c.GRAPH_SCHEMA,
        "root_ids": ["root"],
        "nodes": [
            {
                "id": "root",
                "type": "CLAIM",
                "status": "SUPPORTED",
                "depends_on": ["e"],
                "defeated_by": [],
            },
            evidence(),
        ],
    }


class AssuranceClosureCompilerV1Tests(unittest.TestCase):
    def test_generic_graph_cannot_self_certify_execution_or_adversary(self):
        out = c.evaluate(closed_graph())
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "OPEN__EXECUTION_CLOSURE_REQUIRED")
        self.assertTrue(out["closure_gates"]["representation_closure"])
        self.assertTrue(out["closure_gates"]["proof_closure"])
        self.assertFalse(out["closure_gates"]["execution_closure"])
        self.assertFalse(out["closure_gates"]["adversarial_closure"])
        self.assertFalse(out["terminal_authority"])

    def test_open_obligation_is_residual_not_new_primitive(self):
        g = closed_graph()
        g["nodes"] = [
            {
                "id": "root", "type": "CLAIM", "status": "SUPPORTED",
                "depends_on": ["o"], "defeated_by": [],
            },
            {"id": "o", "type": "OBLIGATION", "status": "OPEN"},
        ]
        out = c.evaluate(g)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__ASSURANCE_RESIDUAL")
        self.assertEqual(out["open_residual_ids"], ["o"])
        self.assertTrue(out["existing_kernel_expressive"])
        self.assertFalse(out["new_primitive_required"])

    def test_supported_defeater_counterproves_root(self):
        g = closed_graph()
        g["nodes"].append({
            "id": "d", "type": "DEFEATER", "status": "SUPPORTED",
            "depends_on": ["de"], "defeated_by": [],
        })
        g["nodes"].append(evidence("de"))
        g["nodes"][0]["defeated_by"] = ["d"]
        out = c.evaluate(g)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "COUNTERPROVED")
        self.assertEqual(out["active_defeater_ids"], ["d"])

    def test_supported_defeater_dominates_earlier_unresolved_defeater_regardless_of_order(self):
        for order in (["open_d", "active_d"], ["active_d", "open_d"]):
            g = closed_graph()
            g["nodes"].extend([
                {"id": "open_d", "type": "DEFEATER", "status": "OPEN"},
                {
                    "id": "active_d",
                    "type": "DEFEATER",
                    "status": "SUPPORTED",
                    "depends_on": ["de"],
                    "defeated_by": [],
                },
                evidence("de"),
            ])
            g["nodes"][0]["defeated_by"] = order
            out = c.evaluate(g)
            self.assertEqual(out["status"], "COUNTERPROVED", (order, out))
            self.assertEqual(out["active_defeater_ids"], ["active_d"], (order, out))
            self.assertFalse(out["pass"], (order, out))

    def test_unresolved_defeater_keeps_root_open(self):
        g = closed_graph()
        g["nodes"].append({"id": "d", "type": "DEFEATER", "status": "OPEN"})
        g["nodes"][0]["defeated_by"] = ["d"]
        out = c.evaluate(g)
        self.assertEqual(out["status"], "OPEN__ASSURANCE_RESIDUAL")
        self.assertEqual(out["unresolved_defeater_ids"], ["d"])

    def test_unsupported_primitive_is_only_new_primitive_trigger(self):
        g = closed_graph()
        g["nodes"].append({
            "id": "alien", "type": "UNMODELED_MAGIC", "status": "OPEN"
        })
        g["nodes"][0]["depends_on"] = ["alien"]
        out = c.evaluate(g)
        self.assertEqual(out["status"], "OPEN__NEW_PRIMITIVE_REPRESENTATION_REQUIRED")
        self.assertTrue(out["new_primitive_required"])
        self.assertEqual(out["unsupported_primitive_types"], ["UNMODELED_MAGIC"])

    def test_dangling_reference_fails_closed(self):
        g = closed_graph()
        g["nodes"][0]["depends_on"] = ["missing"]
        out = c.evaluate(g)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "DANGLING_NODE_REFERENCE")

    def test_dependency_cycle_fails_closed(self):
        g = {
            "schema": c.GRAPH_SCHEMA,
            "root_ids": ["a"],
            "nodes": [
                {"id": "a", "type": "CLAIM", "status": "SUPPORTED",
                 "depends_on": ["b"], "defeated_by": []},
                {"id": "b", "type": "DEPENDENCY", "status": "SUPPORTED",
                 "depends_on": ["a"], "defeated_by": []},
            ],
        }
        out = c.evaluate(g)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "UNSUPPORTED_DEPENDENCY_CYCLE")

    def test_stale_evidence_reopens_proof(self):
        g = closed_graph()
        g["nodes"][1]["status"] = "STALE"
        out = c.evaluate(g)
        self.assertEqual(out["status"], "OPEN__ASSURANCE_RESIDUAL")
        self.assertEqual(out["stale_ids"], ["e"])

    def test_pass_controller_result_still_requires_adversarial_closure(self):
        result = {
            "schema": "X",
            "status": "PASS__GOAL",
            "pass": True,
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "terminal_authority": False,
        }
        out = c.evaluate_controller_result(result)
        self.assertFalse(out["pass"])
        self.assertTrue(out["closure_gates"]["proof_closure"])
        self.assertTrue(out["closure_gates"]["execution_closure"])
        self.assertFalse(out["closure_gates"]["adversarial_closure"])
        self.assertEqual(out["status"], "OPEN__ADVERSARIAL_CLOSURE_REQUIRED")

    def test_open_controller_result_becomes_existing_kernel_obligation(self):
        result = {
            "schema": "X",
            "status": "OPEN__THING",
            "pass": False,
            "next_required_edge": "AUTHENTICATED_THING",
            "semantic_acceptance_complete": False,
            "actual_goal_satisfaction_verified": False,
        }
        graph = c.compile_controller_result(result)
        out = c.evaluate(graph)
        self.assertEqual(out["status"], "OPEN__ASSURANCE_RESIDUAL")
        self.assertIn("obligation:next-edge", out["open_residual_ids"])
        self.assertFalse(out["new_primitive_required"])
        self.assertEqual(
            graph["nodes"][1]["required_edge"],
            "AUTHENTICATED_THING",
        )


if __name__ == "__main__":
    unittest.main()
