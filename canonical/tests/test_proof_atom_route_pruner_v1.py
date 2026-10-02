from __future__ import annotations
import json
import unittest
from pathlib import Path
from canonical.runtime.proof_atom_route_pruner_v1 import prune

ROOT=Path(__file__).resolve().parents[2]

def adj(cid="C1",target="T1",prop="P"):
    return {
        "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__TEST",
        "atom":{
            "proposition":prop,
            "parent_certificate_id":cid,
            "target_predicate":target,
            "adjudication":"FALSIFIED_UNDER_CURRENT_FROZEN_NO_REPLAY_ROUTE",
        },
    }

class TestProofAtomRoutePruner(unittest.TestCase):
    def test_only_route_becomes_uncovered(self):
        f={"unresolved_predicates":["T1"],"certificates":[{"id":"C1","target_predicates":["T1"],"requires":["P"]}]}
        out=prune(f,[adj()])
        self.assertTrue(out["status"].startswith("PASS"))
        self.assertEqual(out["blocked_certificate_ids"],["C1"])
        self.assertEqual(out["uncovered_target_predicates"],["T1"])
        self.assertEqual(out["target_predicates_removed"],[])

    def test_alternative_certificate_preserves_coverage(self):
        f={"unresolved_predicates":["T1"],"certificates":[
            {"id":"C1","target_predicates":["T1"],"requires":["P"]},
            {"id":"C2","target_predicates":["T1"],"requires":["Q"]},
        ]}
        out=prune(f,[adj()])
        self.assertEqual(out["uncovered_target_predicates"],[])
        self.assertEqual(out["blocked_targets_still_covered_by_alternative_certificate"],["T1"])

    def test_wrong_literal_fails_closed(self):
        f={"unresolved_predicates":["T1"],"certificates":[{"id":"C1","target_predicates":["T1"],"requires":["P"]}]}
        self.assertEqual(prune(f,[adj(prop="NOT_P")])["status"],"FAIL_CLOSED")

    def test_nonindependent_adjudication_fails_closed(self):
        a=adj(); a["status"]="CANDIDATE"
        f={"unresolved_predicates":["T1"],"certificates":[{"id":"C1","target_predicates":["T1"],"requires":["P"]}]}
        self.assertEqual(prune(f,[a])["status"],"FAIL_CLOSED")

    def test_live_tb4_route_is_pruned_target_preserved(self):
        frontier=json.loads((ROOT/"canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json").read_text())
        a=json.loads((ROOT/"canonical/governance/TB4_PROOF_ATOM_FALSIFICATION_ADJUDICATION_V1.json").read_text())
        out=prune(frontier,[a])
        self.assertTrue(out["status"].startswith("PASS"))
        self.assertEqual(out["falsified_atom_count"],1)
        self.assertEqual(out["blocked_certificate_ids"],["TB4_ATTAINABLE_ROUTE_CERTIFICATE"])
        self.assertEqual(out["uncovered_target_predicates"],["CODING_TB4_GE_66_4"])
        self.assertEqual(out["alternative_certificate_required"],["CODING_TB4_GE_66_4"])
        self.assertEqual(out["target_predicates_removed"],[])
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)

if __name__=="__main__":
    unittest.main()
