import json
import pathlib
import unittest

from canonical.runtime.proof_route_dominance import evaluate


class ProofRouteDominanceTests(unittest.TestCase):
    def base_obligations(self):
        return [
            {"id":"A","min_oracle_strength":2},
            {"id":"B","min_oracle_strength":1},
        ]

    def test_blocked_route_deleted_when_all_obligations_covered(self):
        out=evaluate({
            "obligations":self.base_obligations(),
            "routes":[
                {"id":"private","covers":["A","B"],"oracle_strength":2,"blocked":True},
                {"id":"public_a","covers":["A"],"oracle_strength":2,"zero_cost":True,"executable":True,"independent_oracle":True,"scope_mapping_frozen":True,"contamination_boundary_frozen":True},
                {"id":"public_b","covers":["B"],"oracle_strength":1,"zero_cost":True,"executable":True,"independent_oracle":True,"scope_mapping_frozen":True,"contamination_boundary_frozen":True},
            ]
        })
        v=out["blocked_route_verdicts"][0]
        self.assertTrue(v["redundant"])
        self.assertEqual(v["uncovered_obligations"],[])

    def test_unique_private_coverage_stays_blocked(self):
        out=evaluate({
            "obligations":self.base_obligations(),
            "routes":[
                {"id":"private","covers":["A","B"],"oracle_strength":2,"blocked":True},
                {"id":"public_a","covers":["A"],"oracle_strength":2,"zero_cost":True,"executable":True,"independent_oracle":True,"scope_mapping_frozen":True,"contamination_boundary_frozen":True},
            ]
        })
        v=out["blocked_route_verdicts"][0]
        self.assertFalse(v["redundant"])
        self.assertEqual(v["uncovered_obligations"],["B"])

    def test_weak_oracle_does_not_dominate(self):
        out=evaluate({
            "obligations":[{"id":"A","min_oracle_strength":3}],
            "routes":[
                {"id":"private","covers":["A"],"oracle_strength":3,"blocked":True},
                {"id":"weak","covers":["A"],"oracle_strength":2,"zero_cost":True,"executable":True,"independent_oracle":True,"scope_mapping_frozen":True,"contamination_boundary_frozen":True},
            ]
        })
        self.assertFalse(out["blocked_route_verdicts"][0]["redundant"])

    def test_unfrozen_scope_does_not_dominate(self):
        out=evaluate({
            "obligations":[{"id":"A","min_oracle_strength":1}],
            "routes":[
                {"id":"private","covers":["A"],"oracle_strength":1,"blocked":True},
                {"id":"candidate","covers":["A"],"oracle_strength":9,"zero_cost":True,"executable":True,"independent_oracle":True,"scope_mapping_frozen":False,"contamination_boundary_frozen":True},
            ]
        })
        self.assertEqual(out["status"],"FAIL_CLOSED_UNCOVERED_OBLIGATIONS")

    def test_frozen_private_surface_input_fails_closed_on_true_uncovered_obligations(self):
        root=pathlib.Path(__file__).resolve().parents[2]
        payload=json.loads((root/"canonical/governance/PRIVATE_SURFACE_DOMINANCE_INPUT_V1.json").read_text())
        out=evaluate(payload)
        self.assertEqual(out["status"],"FAIL_CLOSED_UNCOVERED_OBLIGATIONS")
        self.assertEqual(out["global_uncovered_obligations"],[
            "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001",
            "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
            "STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001",
            "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        ])
        verdicts={v["route_id"]:v for v in out["blocked_route_verdicts"]}
        self.assertTrue(verdicts["BLOCKED_MYSTERYMECHANISM"]["redundant"])
        self.assertFalse(verdicts["BLOCKED_FRONTIERCODE_1_1"]["redundant"])
        self.assertFalse(verdicts["BLOCKED_AA_BRIEFCASE_V1_1"]["redundant"])

    def test_invalid_unknown_coverage_rejected(self):
        out=evaluate({
            "obligations":[{"id":"A","min_oracle_strength":1}],
            "routes":[{"id":"bad","covers":["Z"],"oracle_strength":1}]
        })
        self.assertEqual(out["status"],"INVALID")


if __name__=="__main__":
    unittest.main()
