from __future__ import annotations
import inspect
import json
import unittest
from pathlib import Path

from canonical.runtime import scope_equivalent_proof_gate_v2 as gate
from canonical.runtime import delegation_whole_scope_candidate_v2 as candidate
from canonical.runtime import delegation_whole_scope_proof_v2 as proof_v2
from canonical.runtime import delegation_structural_variety_proof_v3 as proof_v3

ROOT=Path(__file__).resolve().parents[2]
INPUT=ROOT/"canonical/governance/TASK_TO_DELEGATION_SCOPE_EQUIVALENT_PROOF_GATE_V2_INPUT.json"
RELATION=ROOT/"canonical/governance/TASK_TO_DELEGATION_SCOPE_RELATION_V1.json"
REGISTRY=ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"

class DelegationScopeGateV2Tests(unittest.TestCase):
    def setUp(self):
        self.input=json.loads(INPUT.read_text(encoding="utf-8"))
        self.relation=json.loads(RELATION.read_text(encoding="utf-8"))
        registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.contract=next(x for x in registry["active_contracted_residuals"] if x["behavior_id"]=="TASK_TO_DELEGATION_GRAPH_001")

    def test_current_input_is_admissible(self):
        out=gate.evaluate(self.input)
        self.assertTrue(out["admissible"],out)
        self.assertEqual(out["leaked_inference_ids"],[])

    def test_relation_matches_frozen_contract_boundary(self):
        text=" ".join([
            self.contract["inputs"],self.contract["required_output_or_action"],
            self.contract["success_condition"],self.contract["failure_condition"],
            self.contract["verification_route"],
        ]).lower()
        for phrase in ("resource constraints","evidence ownership","live receipts","conflicting writes","fanin","single-worker","naive fanout"):
            self.assertIn(phrase,text)
        self.assertEqual(self.relation["behavior_id"],self.contract["behavior_id"])
        self.assertFalse(self.relation["target_weakened"])
        self.assertEqual(self.relation["unresolved_required_dimensions"],[])

    def test_candidate_and_oracles_are_topology_generic_at_interface(self):
        csrc=inspect.getsource(candidate)
        self.assertNotIn("PARSE_",csrc)
        self.assertNotIn("REASON_",csrc)
        self.assertNotIn("TOO_MANY_STEPS",csrc)
        self.assertIn('task.get("steps"',csrc)
        self.assertIn('task.get("workers"',csrc)
        osrc=inspect.getsource(proof_v2)
        self.assertIn('task["steps"]',osrc)
        self.assertIn('task["workers"]',osrc)
        self.assertEqual(set(proof_v3.CLASSES),{"CHAIN","FORK_JOIN","FANOUT_JOIN","DUAL_ROOT_FANIN","ALTERNATIVE_PLAN"})

    def test_load_bearing_leak_fails_closed(self):
        bad=dict(self.input)
        bad["candidate_visible_derived_or_oracle_ids"]=["MINIMUM_REQUIRED_TASK_SET"]
        out=gate.evaluate(bad)
        self.assertFalse(out["admissible"])
        self.assertTrue(any(x.startswith("LOAD_BEARING_INFERENCE_LEAKED") for x in out["errors"]))

    def test_unresolved_dimension_fails_closed(self):
        bad=dict(self.input)
        bad["unresolved_required_dimensions"]=["UNPROVEN_X"]
        self.assertFalse(gate.evaluate(bad)["admissible"])

if __name__=="__main__":
    unittest.main(verbosity=2)
