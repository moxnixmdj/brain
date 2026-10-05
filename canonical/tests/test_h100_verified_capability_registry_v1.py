import json, unittest
from pathlib import Path
from canonical.runtime import h100_verified_capability_registry_v1 as r
from canonical.runtime import h100_zero_learned_transfer_v1 as t

ROOT=Path(__file__).resolve().parents[1]

class H100VerifiedCapabilityRegistryTests(unittest.TestCase):
    def test_registry_has_seven_prior_verified_entries(self):
        snap=r.registry_snapshot()
        self.assertEqual(snap["entry_count"],7)
        self.assertEqual(snap["persistent_learned_bytes"],0)
        self.assertEqual(len({x["capability_id"] for x in snap["entries"]}),7)
        for row in snap["entries"]:
            self.assertTrue(row["prior_verification"].startswith("canonical/verification/"))

    def test_frozen_transfer_tasks_hit_library_before_raw_search(self):
        cases=[("SIN_B","CAP_LINEAR_TREND_SINUSOID_V1"),("EXP_B","CAP_EXP_ABS_V1"),("STEP_B","CAP_THRESHOLD_STEP_V1")]
        xs=[-4,-3,-2,-1,0,1,2,3,4]
        for task,cap in cases:
            rows=t._rows(task,xs)
            out=r.resolve_verified_capability(rows,target="y",input_name="x")
            self.assertEqual(out["status"],"LIBRARY_HIT__VERIFY_BEFORE_USE",out)
            self.assertEqual(out["match"]["capability_id"],cap)
            self.assertEqual(out["raw_synthesis_attempts_before_hit"],0)

    def test_direct_oewn_invocation_matches_frozen_task(self):
        know=json.loads((ROOT/"governance/H100_OEWN_REAL_LEXICAL_KNOWLEDGE_V1.json").read_text())
        pre=json.loads((ROOT/"governance/H100_OEWN_REAL_LEXICAL_PREEXPOSURE_V1.json").read_text())
        task=pre["tasks"][0]
        out=r.invoke("CAP_OEWN_REAL_LEXICAL_V1",{"cue":task["cue"],"context":task["context"],"knowledge":know})
        self.assertEqual(out["result"]["status"],task["expected_status"])
        self.assertEqual(out["result"]["role"],task["expected_role"])
        self.assertEqual(out["raw_synthesis_attempts_before_hit"],0)

    def test_direct_lexical_source_invocation_matches_frozen_task(self):
        know=json.loads((ROOT/"governance/H100_LEXICAL_SOURCE_FALLBACK_KNOWLEDGE_V1.json").read_text())
        pre=json.loads((ROOT/"governance/H100_LEXICAL_SOURCE_FALLBACK_PREEXPOSURE_V1.json").read_text())
        task=pre["tasks"][0]
        records=[x for x in know["records"] if x["term"]==task["term"]]
        out=r.invoke("CAP_LEXICAL_SOURCE_FALLBACK_V1",{"term":task["term"],"records":records})
        self.assertEqual(out["result"]["status"],task["expected_status"])
        self.assertEqual(out["result"]["role"],task["expected_role"])

    def test_direct_compositional_language_invocation_matches_frozen_task(self):
        pre=json.loads((ROOT/"governance/H100_ZERO_LEARNED_COMPOSITIONAL_LANGUAGE_PREEXPOSURE_V1.json").read_text())
        task=pre["tasks"][0]
        out=r.invoke("CAP_COMPOSITIONAL_LANGUAGE_V1",{"text":task["text"]})
        self.assertEqual(out["result"]["status"],task["expected_status"])
        self.assertEqual(out["result"]["inputs"],task["expected_inputs"])
        self.assertEqual(out["result"]["target"],task["expected_target"])

    def test_direct_tool_trace_invocation_matches_frozen_task(self):
        pre=json.loads((ROOT/"governance/H100_ZERO_LEARNED_TOOL_TRACE_VARIATION_PREEXPOSURE_V1.json").read_text())
        task=pre["tasks"][0]; schema=pre["declared_schema"]
        out=r.invoke("CAP_TOOL_TRACE_NORMALIZER_V1",{"payload":task["payload"],"inputs":schema["inputs"],"target":schema["target"],"format_hint":task["format"]})
        self.assertEqual(out["result"]["status"],task["expected_status"])
        self.assertEqual(out["result"]["rows"],task["expected_rows"])

    def test_predictions_remain_exact_on_distinct_points(self):
        rows=t._rows("EXP_B",[-4,-3,-2,-1,0,1,2,3,4])
        out=r.resolve_verified_capability(rows,target="y",input_name="x")
        for x in (-3.7,-0.7,0.6,2.8):
            self.assertAlmostEqual(r.predict(out,{"x":x}),t._truth("EXP_B",x),places=9)

    def test_out_of_family_cubic_fails_closed_to_raw_synthesis(self):
        rows=[{"x":float(x),"y":float(x**3+0.123*x)} for x in range(-5,6)]
        out=r.resolve_verified_capability(rows,target="y",input_name="x")
        self.assertEqual(out["status"],"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED")
        self.assertIsNone(out["match"])

    def test_unknown_direct_id_fails_closed(self):
        with self.assertRaises(r.CapabilityRegistryError):
            r.invoke("CAP_UNKNOWN",{})

if __name__=="__main__":
    unittest.main(verbosity=2)
