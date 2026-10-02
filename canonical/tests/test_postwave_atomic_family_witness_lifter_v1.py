from __future__ import annotations
import copy,json,unittest
from pathlib import Path

from canonical.runtime.postwave_evidence_reconciler_v1 import evaluate as reconcile
from canonical.runtime.postwave_atomic_family_witness_lifter_v1 import evaluate as lift

ROOT=Path(__file__).resolve().parents[2]

def load(rel:str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class Tests(unittest.TestCase):
    def live_inputs(self):
        rec=reconcile(
            load("canonical/governance/POSTWAVE_EVIDENCE_RECONCILIATION_INPUT_V1.json"),
            load("canonical/verification/CURRENT_OBJECTIVE_BINDINGS_PUBLIC_RUNNER_VERIFICATION_20261002_V2.json"),
            load("canonical/governance/OPUS55_REOPENED_OBJECTIVE_ROUTE_RESIDUAL_V1.json"),
            load("canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json"),
            load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
        )
        return dict(
            family="SUBAGENT_DELEGATION_AND_COORDINATION",
            target_predicate="DELEGATION_TERMINAL_SUCCESS_NONINFERIOR",
            reconciliation=rec,
            registry=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
            evidence=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
            behavioral_registry=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),
            behavioral_reduction=load("canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json"),
            protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"),
        )

    def test_live_delegation_candidate_is_full_family_composite_ceiling(self):
        x=self.live_inputs()
        self.assertEqual(x["reconciliation"]["status"],"PASS")
        out=lift(**x)
        self.assertTrue(out["pass"],out)
        w=out["candidate_witness"]
        self.assertEqual(w["family"],"SUBAGENT_DELEGATION_AND_COORDINATION")
        self.assertEqual(w["source_target_predicate"],"DELEGATION_TERMINAL_SUCCESS_NONINFERIOR")
        self.assertEqual(w["source_case_count"],132)
        self.assertEqual(w["result"],{
            "direction":"higher",
            "brain_lower_bound":1.0,
            "theoretical_upper_bound":1.0,
        })
        self.assertEqual(w["atomic_basis"]["already_proved_predicates"],[
            "DELEGATION_SPEEDUP_NO_CORRECTNESS_TRADE",
            "DELEGATION_ZERO_CRITICAL_COORDINATION_VIOLATIONS",
        ])
        self.assertTrue(w["closes_entire_protocol"])
        self.assertFalse(w["verified"])
        self.assertFalse(w["independent"])
        self.assertFalse(out["promotion_authority"])

    def test_missing_other_atomic_proof_fails(self):
        x=self.live_inputs()
        x["evidence"]=copy.deepcopy(x["evidence"])
        x["evidence"]["claims"]=[
            c for c in x["evidence"]["claims"]
            if c.get("predicate_id")!="DELEGATION_SPEEDUP_NO_CORRECTNESS_TRADE"
        ]
        out=lift(**x)
        self.assertFalse(out["pass"])
        self.assertIn(
            "OTHER_FAMILY_PREDICATE_NOT_PROVED:DELEGATION_SPEEDUP_NO_CORRECTNESS_TRADE",
            out["errors"],
        )

    def test_nonindependent_other_atomic_fails(self):
        x=self.live_inputs()
        x["evidence"]=copy.deepcopy(x["evidence"])
        c=next(c for c in x["evidence"]["claims"] if c.get("predicate_id")=="DELEGATION_ZERO_CRITICAL_COORDINATION_VIOLATIONS")
        c["independent_or_objective"]=False
        out=lift(**x)
        self.assertFalse(out["pass"])
        self.assertIn(
            "OTHER_FAMILY_PREDICATE_NOT_INDEPENDENT:DELEGATION_ZERO_CRITICAL_COORDINATION_VIOLATIONS",
            out["errors"],
        )

    def test_family_mapping_must_be_exact_single_contract(self):
        x=self.live_inputs()
        x["behavioral_registry"]=copy.deepcopy(x["behavioral_registry"])
        x["behavioral_registry"]["family_to_residual_contracts"]["SUBAGENT_DELEGATION_AND_COORDINATION"]=[
            "TASK_TO_DELEGATION_GRAPH_001","OTHER"
        ]
        out=lift(**x)
        self.assertFalse(out["pass"])
        self.assertIn("FAMILY_NOT_EXACT_SINGLE_RESIDUAL_CONTRACT",out["errors"])

    def test_behavioral_family_pass_is_required(self):
        x=self.live_inputs()
        x["behavioral_reduction"]=copy.deepcopy(x["behavioral_reduction"])
        x["behavioral_reduction"]["family_verdict"]["passed_families"].remove("SUBAGENT_DELEGATION_AND_COORDINATION")
        out=lift(**x)
        self.assertFalse(out["pass"])
        self.assertIn("FAMILY_BEHAVIORAL_PASS_MISSING",out["errors"])

    def test_lossless_registry_rule_is_required(self):
        x=self.live_inputs()
        x["registry"]=copy.deepcopy(x["registry"])
        x["registry"]["rules"]=[
            r for r in x["registry"]["rules"]
            if not r.startswith("REGISTRY_IS_A_LOSSLESS_DECOMPOSITION")
        ]
        out=lift(**x)
        self.assertFalse(out["pass"])
        self.assertIn("LOSSLESS_ATOMIC_DECOMPOSITION_NOT_BOUND",out["errors"])

    def test_reconciliation_candidate_must_reach_ceiling(self):
        x=self.live_inputs()
        x["reconciliation"]=copy.deepcopy(x["reconciliation"])
        x["reconciliation"]["candidate_predicate_witnesses"][0]["result"]["brain_lower_bound"]=0.99
        out=lift(**x)
        self.assertFalse(out["pass"])
        self.assertIn("TARGET_ATOMIC_NOT_AT_CEILING",out["errors"])

    def test_open_protocol_is_required(self):
        x=self.live_inputs()
        x["protocols"]=copy.deepcopy(x["protocols"])
        p=next(p for p in x["protocols"]["protocols"] if p.get("family")=="SUBAGENT_DELEGATION_AND_COORDINATION")
        p["status"]="PASS"
        out=lift(**x)
        self.assertFalse(out["pass"])
        self.assertIn("FAMILY_PROTOCOL_NOT_OPEN",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
