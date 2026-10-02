from __future__ import annotations
import copy,unittest
from canonical.runtime.cad_t0_oracle_extractor import bind_case,_digest_bytes

def fixture():
    output=b"STEP-CANDIDATE-BYTES"
    meta={
      "portfolio":"T0_CODING_SEMANTIC_GEOMETRY_PORTFOLIO",
      "behavior_id":"CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001",
      "m1_load_bearing":True,
      "selected_after_post_freeze_beacon":True,
      "case_id":"T0::cad::7",
      "selector_commitment":"abc123",
      "post_freeze_beacon":"public-runner-999",
      "public_case":{"drawing_id":"case-7"},
    }
    oracle={
      "reference_constraint_graph":{"nodes":["A"],"edges":[]},
      "identifiable":True,
      "required_geometry_metrics":["bbox","volume"],
      "reference_geometry_metrics":{"bbox":[1.0,2.0,3.0],"volume":6.0},
      "metric_tolerances":{"bbox":{"abs":0.01,"rel":0.0},"volume":{"abs":0.05,"rel":0.0}},
      "geometry_class_label":"LOFT",
      "mutation_identity":"NONE",
    }
    candidate={"status":"SOLID","constraint_graph":{"nodes":["A"],"edges":[]}}
    measurement={
      "producer_id":"brain_owned_geometry_kernel",
      "producer_version_or_blob":"deadbeef",
      "input_artifact_digest":"source-digest",
      "candidate_output_digest":_digest_bytes(output),
      "candidate_solid_valid":True,
      "geometry_class_covered":True,
      "candidate_geometry_metrics":{"bbox":[1.0,2.0,3.0],"volume":6.0},
      "ambiguity_witness_valid":False,
      "end_to_end_final_geometry_correct":True,
      "cross_stage_state_loss":False,
      "failure_localization_consistent":True,
    }
    return meta,oracle,candidate,measurement,output

class CadT0OracleExtractorTests(unittest.TestCase):
    def test_valid_evaluator_only_binding(self):
        m,o,c,x,b=fixture()
        out=bind_case(m,o,c,x,candidate_output_bytes=b)
        self.assertTrue(out["pass"],out)
        self.assertNotIn("_oracle",c)
        self.assertEqual(out["scorer_case"]["_oracle"]["geometry_class_label"],"LOFT")
        self.assertEqual(out["measurement_provenance"]["candidate_output_digest"],_digest_bytes(b))

    def test_prebeacon_selection_fails_closed(self):
        m,o,c,x,b=fixture();m["selected_after_post_freeze_beacon"]=False
        self.assertFalse(bind_case(m,o,c,x,candidate_output_bytes=b)["pass"])

    def test_candidate_oracle_self_report_fails_closed(self):
        m,o,c,x,b=fixture();c["candidate_geometry_metrics"]={"volume":6}
        out=bind_case(m,o,c,x,candidate_output_bytes=b)
        self.assertFalse(out["pass"]);self.assertTrue(any("CANDIDATE_ORACLE_SELF_REPORT" in e for e in out["errors"]))

    def test_candidate_measurement_producer_fails_closed(self):
        m,o,c,x,b=fixture();x["producer_id"]="candidate"
        self.assertFalse(bind_case(m,o,c,x,candidate_output_bytes=b)["pass"])

    def test_digest_mismatch_fails_closed(self):
        m,o,c,x,b=fixture();x["candidate_output_digest"]="0"*64
        out=bind_case(m,o,c,x,candidate_output_bytes=b)
        self.assertFalse(out["pass"]);self.assertIn("CANDIDATE_OUTPUT_DIGEST_MISMATCH",out["errors"])

    def test_missing_reference_metric_fails_closed(self):
        m,o,c,x,b=fixture();del o["reference_geometry_metrics"]["volume"]
        out=bind_case(m,o,c,x,candidate_output_bytes=b)
        self.assertFalse(out["pass"]);self.assertIn("REFERENCE_METRIC_UNBOUND:volume",out["errors"])

    def test_nonidentifiable_case_can_bind_without_solid_claim(self):
        m,o,c,x,b=fixture()
        o["identifiable"]=False
        c={"status":"NONIDENTIFIABLE","constraint_graph":{"nodes":["A"],"edges":[]}}
        x["candidate_solid_valid"]=False;x["geometry_class_covered"]=False;x["candidate_geometry_metrics"]={}
        x["ambiguity_witness_valid"]=True
        out=bind_case(m,o,c,x,candidate_output_bytes=b)
        self.assertTrue(out["pass"],out)

if __name__=="__main__":
    unittest.main()
