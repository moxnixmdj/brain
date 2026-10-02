from __future__ import annotations
import unittest
from canonical.runtime.cad_t0_geometry_population import (
    FAMILIES,SLOT_COUNT,derive_seed,generate_case,generate_post_freeze,public_case
)
from canonical.runtime.cad_t0_oracle_adapter import (
    measure_result,metrics_match,observe_candidate,validate_ambiguity_witness
)

class BB:
    xlen=10.0; ylen=20.0; zlen=30.0
class Shape:
    def BoundingBox(self): return BB()
    def Volume(self): return 6000.0
    def Area(self): return 2200.0
    def Faces(self): return [0]*6
    def Edges(self): return [0]*12
    def Vertices(self): return [0]*8
class Solids:
    def vals(self): return [Shape()]
class Result:
    def solids(self): return Solids()
    def val(self): return Shape()

class PopulationTests(unittest.TestCase):
    def test_post_freeze_determinism_and_size(self):
        a=generate_post_freeze("commitment-x","beacon-y")
        b=generate_post_freeze("commitment-x","beacon-y")
        self.assertEqual(a,b)
        self.assertEqual(len(a),SLOT_COUNT)

    def test_beacon_changes_hidden_cases(self):
        a=generate_post_freeze("commitment-x","beacon-a")
        b=generate_post_freeze("commitment-x","beacon-b")
        self.assertNotEqual(a,b)

    def test_family_schedule_covers_all_declared_families(self):
        seen={generate_case(derive_seed("c","b",f"CAD_T0_GEOMETRY_V1::slot::{i}"),i)["_oracle"]["family"] for i in range(len(FAMILIES))}
        self.assertEqual(seen,set(FAMILIES))

    def test_public_case_strips_every_hidden_oracle_field(self):
        c=generate_case(derive_seed("c","b","CAD_T0_GEOMETRY_V1::slot::0"),0)
        p=public_case(c)
        self.assertNotIn("_oracle",p)
        self.assertIn("drawing_svg",p)
        self.assertNotIn("reference_geometry_contract",str(p))

    def test_nonidentifiable_depth_has_constructive_ambiguity(self):
        slot=7
        c=generate_case(derive_seed("c","b",f"CAD_T0_GEOMETRY_V1::slot::{slot}"),slot)
        self.assertFalse(c["_oracle"]["identifiable"])
        vals=c["_oracle"]["consistent_alternatives"]
        self.assertEqual(len(vals),2)
        self.assertNotEqual(vals[0],vals[1])

class OracleAdapterTests(unittest.TestCase):
    def test_real_result_interface_is_measured_evaluator_side(self):
        m=measure_result(Result())
        self.assertEqual(m["volume"],6000.0)
        self.assertEqual(m["surface_area"],2200.0)
        self.assertEqual(m["bbox"],[10.0,20.0,30.0])
        self.assertEqual(m["topology_counts"],{"faces":6,"edges":12,"vertices":8})

    def test_identifiable_observation_ignores_candidate_supplied_metrics(self):
        case={
            "_oracle":{
                "identifiable":True,
                "reference_constraint_graph":{"x":1},
                "reference_geometry_metrics":{
                    "volume":6000.0,"surface_area":2200.0,"bbox":[10.0,20.0,30.0],
                    "topology_counts":{"faces":6,"edges":12,"vertices":8},
                },
                "required_geometry_metrics":["volume","surface_area","bbox","topology_counts"],
                "metric_tolerances":{
                    "volume":{"abs":0.05,"rel":1e-7},"surface_area":{"abs":0.05,"rel":1e-7},
                    "bbox":{"abs":0.01,"rel":1e-7},"topology_counts":{"abs":0,"rel":0},
                },
            }
        }
        candidate={"status":"SOLID","constraint_graph":{"x":1},"candidate_geometry_metrics":{"volume":1}}
        obs=observe_candidate(case,candidate,Result())
        self.assertTrue(obs["candidate_solid_valid"])
        self.assertTrue(obs["end_to_end_final_geometry_correct"])
        self.assertEqual(obs["candidate_geometry_metrics"]["volume"],6000.0)

    def test_graph_state_loss_is_detected_independently(self):
        case={"_oracle":{"identifiable":True,"reference_constraint_graph":{"x":1},
              "reference_geometry_metrics":{"volume":6000.0},"required_geometry_metrics":["volume"],
              "metric_tolerances":{"volume":{"abs":0.01,"rel":0}}}}
        obs=observe_candidate(case,{"status":"SOLID","constraint_graph":{"x":2}},Result())
        self.assertTrue(obs["cross_stage_state_loss"])

    def test_nonidentifiable_witness_requires_two_distinct_positive_values(self):
        case={"_oracle":{"identifiable":False,"ambiguity_parameter":"depth_mm"}}
        good={"status":"NONIDENTIFIABLE","ambiguity_witness":{"parameter":"depth_mm","alternatives":[10,20]}}
        bad={"status":"NONIDENTIFIABLE","ambiguity_witness":{"parameter":"depth_mm","alternatives":[10,10]}}
        self.assertTrue(validate_ambiguity_witness(case,good))
        self.assertFalse(validate_ambiguity_witness(case,bad))
        self.assertTrue(observe_candidate(case,good,None)["ambiguity_witness_valid"])

if __name__=="__main__":
    unittest.main(verbosity=2)
