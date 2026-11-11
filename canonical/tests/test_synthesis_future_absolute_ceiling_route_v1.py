from __future__ import annotations
import copy, json, unittest
from pathlib import Path
from canonical.runtime.synthesis_future_absolute_ceiling_route_v1 import evaluate, blob_sha

ROOT=Path(__file__).resolve().parents[2]
def load(rel): return json.loads((ROOT/rel).read_text())
def live():
    paths={
      "route":"canonical/governance/SYNTHESIS_FUTURE_ABSOLUTE_CEILING_ROUTE_V1.json",
      "protocols":"canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json",
      "targets":"canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V1.json",
      "super":"canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json",
      "suites":"canonical/governance/CONTRACT_NATIVE_ABSOLUTE_PROOF_SUITES_V1.json",
    }
    return dict(
      route=load(paths["route"]), protocols=load(paths["protocols"]),
      targets=load(paths["targets"]), superportfolio=load(paths["super"]),
      suites=load(paths["suites"]),
      shas={k:blob_sha(ROOT/v) for k,v in paths.items() if k!="route"},
    )

class Tests(unittest.TestCase):
    def test_live_preexposure_route_passes_zero_credit(self):
        out=evaluate(**live())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["future_case_count"],18)
        self.assertTrue(out["route_preexposure_valid"])
        self.assertFalse(out["exact_opus_required_if_brain_hits_ceiling"])
        self.assertFalse(out["old_terminal_evidence_admissible"])
        self.assertFalse(out["scope_completeness_currently_proved"])
        self.assertEqual(out["required_scope_completeness_basis"],"EXACT_COMPLETE_TARGET_CASE_UNIVERSE")
        self.assertEqual(out["acceptance_credit_delta"],0)
        self.assertFalse(out["execution_authority"])

    def test_old_result_transport_fails_closed(self):
        x=live(); x["route"]=copy.deepcopy(x["route"])
        x["route"]["existing_result_inputs"]=["canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"]
        out=evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("POSTHOC_RESULT_TRANSPORT_FORBIDDEN",out["errors"])

    def test_known_beacon_fails_preexposure(self):
        x=live(); x["route"]=copy.deepcopy(x["route"])
        x["route"]["preexposure_scope_blueprint"]["beacon_known_now"]=True
        out=evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("PREEXPOSURE_FLAG_MUST_BE_FALSE:beacon_known_now",out["errors"])

    def test_missing_quality_dimension_fails_closed(self):
        x=live(); x["route"]=copy.deepcopy(x["route"])
        x["route"]["frozen_task_dimensions"]=x["route"]["frozen_task_dimensions"][:-1]
        out=evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("ROUTE_DIMENSIONS_DRIFT",out["errors"])

    def test_mean_dimension_score_cannot_replace_strict_min(self):
        x=live(); x["route"]=copy.deepcopy(x["route"])
        x["route"]["scorer"]["matched_quality"]["case_score"]="ARITHMETIC_MEAN_OF_SIX_DIMENSION_PASS_BITS"
        out=evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("QUALITY_CEILING_SCORER_DRIFT",out["errors"])

    def test_blueprint_cannot_claim_scope_complete(self):
        x=live(); x["route"]=copy.deepcopy(x["route"])
        x["route"]["scope_completeness_requirement"]["current_state"]="VERIFIED"
        out=evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("SCOPE_COMPLETENESS_STATE_DRIFT",out["errors"])

    def test_scope_source_class_drift_fails_closed(self):
        x=live(); x["route"]=copy.deepcopy(x["route"])
        x["route"]["preexposure_scope_blueprint"]["source_classes"]=x["route"]["preexposure_scope_blueprint"]["source_classes"][:-1]
        out=evaluate(**x)
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_CLASSES_NOT_EXACT_PREWAVE_SUITE",out["errors"])

if __name__=="__main__": unittest.main(verbosity=2)
