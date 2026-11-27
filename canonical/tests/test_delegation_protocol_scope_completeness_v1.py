from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.delegation_protocol_scope_completeness_verifier_v1 import (
    ROOT, execute, verify,
)

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class DelegationProtocolScopeCompletenessV1Tests(unittest.TestCase):
    def setUp(self):
        self.relation=load("canonical/governance/DELEGATION_SCOPE_EQUIVALENCE_RELATION_V2.json")
        self.registry=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
        self.protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
        self.gate=load("canonical/governance/TASK_TO_DELEGATION_SCOPE_EQUIVALENT_PROOF_GATE_V2_INPUT.json")
        self.candidate=(ROOT/"canonical/runtime/delegation_whole_scope_candidate_v2.py").read_text()
        self.oracle=(ROOT/"canonical/runtime/delegation_whole_scope_proof_v2.py").read_text()
        self.structural=(ROOT/"canonical/runtime/delegation_structural_variety_proof_v3.py").read_text()

    def run_mutated(self, *, relation=None, registry=None, protocols=None, gate=None, candidate=None):
        return verify(
            relation or self.relation,
            registry or self.registry,
            protocols or self.protocols,
            gate or self.gate,
            candidate_source=self.candidate if candidate is None else candidate,
            oracle_source=self.oracle,
            structural_source=self.structural,
            enforce_exact_blobs=False,
        )

    def test_live_exact_cone_passes_zero_credit(self):
        out=execute()
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertTrue(out["scope_complete"])
        self.assertEqual(out["basis"],"UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertFalse(out["finite_sample_used_as_exhaustive_proof"])
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_second_family_contract_fails_closed(self):
        reg=copy.deepcopy(self.registry)
        reg["family_to_residual_contracts"]["SUBAGENT_DELEGATION_AND_COORDINATION"].append(
            "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
        )
        out=self.run_mutated(registry=reg)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("FAMILY_NOT_EXACTLY_ONE_DELEGATION_CONTRACT",out["errors"])

    def test_protocol_dimension_drift_fails_closed(self):
        p=copy.deepcopy(self.protocols)
        row=next(x for x in p["protocols"] if x["family"]=="SUBAGENT_DELEGATION_AND_COORDINATION")
        row["task_dimensions"].append("implicit hidden semantics")
        out=self.run_mutated(protocols=p)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("PROTOCOL_DIMENSIONS_CHANGED_OR_UNCOVERED",out["errors"])

    def test_inference_leak_fails_closed(self):
        g=copy.deepcopy(self.gate)
        g["candidate_visible_derived_or_oracle_ids"]=["MINIMUM_REQUIRED_TASK_SET"]
        out=self.run_mutated(gate=g)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("SCOPE_EQUIVALENT_GATE_NOT_ADMISSIBLE",out["errors"])

    def test_static_task_cutoff_fails_closed(self):
        out=self.run_mutated(candidate=self.candidate+"\nMAX_TASKS=20\n")
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertTrue(any(x.startswith("CANDIDATE_STATIC_OR_TOPOLOGY_CUTOFF") for x in out["errors"]))

    def test_unresolved_scope_dimension_fails_closed(self):
        r=copy.deepcopy(self.relation)
        r["universal_scope_argument"]["unresolved_required_dimensions"]=["UNKNOWN_X"]
        out=self.run_mutated(relation=r)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("UNRESOLVED_REQUIRED_DIMENSIONS",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
