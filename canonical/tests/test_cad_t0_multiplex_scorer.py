import unittest
from canonical.runtime.cad_t0_multiplex_scorer import public_case,score_case

REF_GRAPH={"views":{"front":["edge-a"],"top":["edge-b"]},"features":[{"id":"H1","kind":"hole"}]}
REF_METRICS={
  "watertight":True,
  "volume":100.0,
  "surface_area":250.0,
  "principal_inertia":[10.0,20.0,30.0],
  "euler_number":2,
  "curvature_signature":{"flat":8,"curved":2},
}
TOLS={
  "watertight":{"abs":0,"rel":0},
  "volume":{"abs":0.01,"rel":1e-6},
  "surface_area":{"abs":0.01,"rel":1e-6},
  "principal_inertia":{"abs":0.01,"rel":1e-6},
  "euler_number":{"abs":0,"rel":0},
  "curvature_signature":{"abs":0,"rel":0},
}

def identifiable_case():
    return {
      "case_id":"CAD-T0-X",
      "drawing":"visible-only",
      "_oracle":{
        "reference_constraint_graph":REF_GRAPH,
        "identifiable":True,
        "reference_geometry_metrics":dict(REF_METRICS),
        "required_geometry_metrics":list(REF_METRICS),
        "metric_tolerances":{k:dict(v) for k,v in TOLS.items()},
      }
    }

def good_candidate():
    return {"status":"SOLID","constraint_graph":REF_GRAPH}

def good_observation():
    return {
      "candidate_solid_valid":True,
      "geometry_class_covered":True,
      "candidate_geometry_metrics":REF_METRICS,
      "end_to_end_final_geometry_correct":True,
      "cross_stage_state_loss":False,
      "failure_localization_consistent":True,
    }

class Tests(unittest.TestCase):
    def test_public_case_strips_hidden_oracle(self):
        p=public_case(identifiable_case())
        self.assertNotIn("_oracle",p)

    def test_identifiable_good_case_passes_all_three_lanes(self):
        out=score_case(identifiable_case(),good_candidate(),good_observation())
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["lane_A_m1a_pass"])
        self.assertTrue(out["lane_B_m1b_pass"])
        self.assertTrue(out["lane_C_composition_pass"])

    def test_graph_mutation_fails_lane_a(self):
        c=good_candidate()
        c["constraint_graph"]={"views":{},"features":[]}
        out=score_case(identifiable_case(),c,good_observation())
        self.assertFalse(out["pass"])
        self.assertIn("LANE_A_CONSTRAINT_GRAPH_MISMATCH",out["errors"])

    def test_wrong_global_geometry_fails_even_when_local_graph_is_right(self):
        obs=good_observation()
        obs["candidate_geometry_metrics"]={**REF_METRICS,"volume":130.0}
        out=score_case(identifiable_case(),good_candidate(),obs)
        self.assertFalse(out["pass"])
        self.assertIn("LANE_B_METRIC_MISMATCH:volume",out["errors"])

    def test_nonidentifiable_requires_independent_witness_validation(self):
        case={
          "case_id":"CAD-T0-A",
          "_oracle":{"reference_constraint_graph":REF_GRAPH,"identifiable":False}
        }
        cand={"status":"NONIDENTIFIABLE","constraint_graph":REF_GRAPH}
        obs={
          "ambiguity_witness_valid":True,
          "end_to_end_final_geometry_correct":True,
          "cross_stage_state_loss":False,
          "failure_localization_consistent":True,
        }
        self.assertTrue(score_case(case,cand,obs)["pass"])
        obs["ambiguity_witness_valid"]=False
        self.assertFalse(score_case(case,cand,obs)["pass"])

    def test_candidate_hidden_oracle_leak_fails_closed(self):
        cand=good_candidate()
        cand["_oracle"]={"cheat":True}
        out=score_case(identifiable_case(),cand,good_observation())
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("CANDIDATE_HIDDEN_FIELD_LEAK") for x in out["errors"]))

    def test_numeric_metric_without_frozen_tolerance_fails_closed(self):
        case=identifiable_case()
        del case["_oracle"]["metric_tolerances"]["volume"]
        out=score_case(case,good_candidate(),good_observation())
        self.assertFalse(out["pass"])
        self.assertIn("LANE_B_METRIC_TOLERANCE_INVALID:volume",out["errors"])

if __name__=="__main__":
    unittest.main()
