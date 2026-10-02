from __future__ import annotations
import copy, json, unittest
from pathlib import Path

from canonical.runtime.acceptance_proof_transmuter_v1 import evaluate as transmute
from canonical.runtime.opus55_acceptance_residual_compiler_v2 import evaluate as reduce_residual

ROOT=Path(__file__).resolve().parents[2]

def load(rel: str):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class DelegationCeilingAcceptanceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
        self.trans_input=load("canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json")
        self.witness=load("canonical/governance/DELEGATION_ACCEPTANCE_CEILING_WITNESS_V1.json")
        self.verify=load("canonical/verification/DELEGATION_TERMINAL_CEILING_CONTINUITY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
        self.registry=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
        self.evidence=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
        self.comparator=load("canonical/reasoning/2026-10-02_EXACT_OPUS55_ZERO_COST_COMPARATOR_ROUTE_RECONCILIATION_V1.json")
        self.readiness=load("canonical/governance/OPUS55_PUBLIC_BAR_SCORE_READINESS_MATRIX_V1.json")

    def test_delegation_full_protocol_transmutes_to_four_of_nineteen(self):
        self.assertIn("INDEPENDENT_PUBLIC_RUNNER_PASS",self.verify["status"])
        self.assertTrue(self.witness["verified"])
        self.assertTrue(self.witness["independent"])
        out=transmute(self.protocols,self.trans_input)
        self.assertEqual(out["status"],"PASS")
        self.assertEqual((out["family_count"],out["closed_family_count"],out["open_family_count"]),(19,4,15))
        closed={r["family"] for r in out["families"] if r["result_status"]=="PASS"}
        self.assertEqual(closed,{
            "EXACT_SYMBOLIC_COMPUTATION",
            "LONG_HORIZON_MEMORY_AND_CONTINUITY",
            "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
            "SUBAGENT_DELEGATION_AND_COORDINATION",
        })
        row=next(r for r in out["families"] if r["family"]=="SUBAGENT_DELEGATION_AND_COORDINATION")
        self.assertEqual(row["closure_mode"],"ABSOLUTE_DOMINANCE")
        self.assertEqual(row["witness_id"],"DELEGATION_TERMINAL_CEILING_ABSOLUTE_DOMINANCE_20261002_V1")
        self.assertEqual(row["witness_reason"],"THEORETICAL_CEILING_DOMINANCE")

    def test_atomic_residual_delegation_is_three_of_three_proved(self):
        out=reduce_residual(self.registry,self.evidence,self.comparator,self.readiness)
        self.assertEqual(out["errors"],[])
        self.assertEqual(out["proved_predicate_count"],9)
        self.assertEqual(out["open_predicate_count"],0)
        self.assertEqual(out["blocked_predicate_count"],29)
        row=next(r for r in out["families"] if r["family"]=="SUBAGENT_DELEGATION_AND_COORDINATION")
        self.assertEqual(row["predicate_count"],3)
        self.assertEqual(row["proved"],3)
        self.assertEqual(row["open"],0)
        self.assertEqual(row["blocked"],0)
        self.assertEqual(row["state"],"PROVED")
        self.assertFalse(out["terminal_promotion_allowed"])
        claim=next(c for c in self.evidence["claims"] if c["predicate_id"]=="DELEGATION_TERMINAL_SUCCESS_NONINFERIOR")
        self.assertEqual(claim["proof_kind"],"ABSOLUTE_CEILING")
        self.assertEqual(claim["source_sha"],"344a501c22b898a2a1aaba8847892b442a5a2aa3")
        self.assertTrue(claim["scope_complete"])
        self.assertTrue(claim["independent_or_objective"])

    def test_removing_delegation_ceiling_reopens_only_delegation_family(self):
        t=copy.deepcopy(self.trans_input)
        t["evidence"]=[e for e in t["evidence"] if e.get("family")!="SUBAGENT_DELEGATION_AND_COORDINATION"]
        tout=transmute(self.protocols,t)
        self.assertEqual(tout["closed_family_count"],3)
        drow=next(r for r in tout["families"] if r["family"]=="SUBAGENT_DELEGATION_AND_COORDINATION")
        self.assertEqual(drow["result_status"],"DEFINED_RESULT_OPEN")

        e=copy.deepcopy(self.evidence)
        e["claims"]=[c for c in e["claims"] if c.get("predicate_id")!="DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"]
        rout=reduce_residual(self.registry,e,self.comparator,self.readiness)
        drow=next(r for r in rout["families"] if r["family"]=="SUBAGENT_DELEGATION_AND_COORDINATION")
        self.assertNotEqual(drow["state"],"PROVED")
        self.assertEqual(drow["proved"],2)
        self.assertFalse(rout["terminal_promotion_allowed"])

if __name__=="__main__":
    unittest.main(verbosity=2)
