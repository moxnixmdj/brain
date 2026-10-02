from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime.cad_t0_prewave_binding_guard import evaluate,REQ

class GuardTests(unittest.TestCase):
    def fixture(self):
        return {
          REQ["source_pool"]:{
            "behavior_id":"CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001",
            "eligible_cases":[{"content_opened_before_candidate_freeze":False}],
            "forbidden_before_candidate_freeze":["READ_INSTRUCTION_CONTENT","READ_SOLUTION_CONTENT","READ_GRADER_CONTENT","READ_REFERENCE_MODEL_CONTENT","READ_VISIBLE_ASSET_PIXELS"],
            "terminal_results_observed":0,"fresh_terminal_evidence_consumed":0},
          REQ["candidate_freeze"]:{
            "behavior_id":"CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001",
            "contamination_state":{"task_instruction_opened":False,"task_solution_opened":False,"task_reference_model_opened":False,"task_grader_content_opened":False},
            "post_freeze_rules":["HIDDEN_TASK_GRADER_OR_REFERENCE_CONTENT_MAY_BE_READ_ONLY_BY_EVALUATOR_SIDE_AFTER_THIS_FREEZE","ANY_REQUIRED_CAD_RUNTIME_CHANGE_AFTER_HIDDEN_GRADER_EXPOSURE_INVALIDATES_THIS_CASE_FOR_CLEAN_PROMOTION"],
            "terminal_results_observed":0,"fresh_terminal_evidence_consumed":0},
          REQ["binding"]:{
            "behavior_id":"CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001",
            "selector":"GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2_POST_FREEZE_BEACON_RULE",
            "contamination":{"case_specific_tuning_after_freeze":False,"case_replacement":False,"result_to_runtime_feedback_during_wave":False,"evaluator_or_threshold_edit_after_first_terminal_result":False},
            "terminal_acceptance":{"prewave_binding_is_terminal_result":False},
            "terminal_results_observed":0,"fresh_terminal_evidence_consumed":0},
          REQ["observation_schema"]:{
            "behavior_id":"CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001",
            "observation_fields":{"metric":{"candidate_may_supply":False}},
            "forbidden_sources":["CANDIDATE_SELF_REPORT","REFERENCE_DATA_LEAKED_INTO_CANDIDATE_INPUT"]},
        }
    def run_guard(self,payload):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for rel,obj in payload.items():
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj),encoding="utf-8")
            return evaluate(root)
    def test_pass(self):
        self.assertTrue(self.run_guard(self.fixture())["pass"])
    def test_hidden_content_exposure_fails(self):
        f=self.fixture();f[REQ["candidate_freeze"]]["contamination_state"]["task_grader_content_opened"]=True
        self.assertFalse(self.run_guard(f)["pass"])
    def test_candidate_supplied_observation_fails(self):
        f=self.fixture();f[REQ["observation_schema"]]["observation_fields"]["metric"]["candidate_may_supply"]=True
        self.assertFalse(self.run_guard(f)["pass"])
    def test_terminal_result_before_wave_fails(self):
        f=self.fixture();f[REQ["binding"]]["terminal_results_observed"]=1
        self.assertFalse(self.run_guard(f)["pass"])
if __name__=="__main__": unittest.main()
