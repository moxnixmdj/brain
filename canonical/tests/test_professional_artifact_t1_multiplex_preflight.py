from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime.professional_artifact_t1_multiplex_preflight import evaluate

class Tests(unittest.TestCase):
    def eval_case(self,mut=None):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for rel in [
                "canonical/runtime/p2_p3_information_safe_candidate_v2.py",
                "canonical/governance/PROFESSIONAL_ARTIFACT_INTERNAL_PREWAVE_BINDING_V1.json",
                "canonical/governance/NATIVE_ARTIFACT_T1_MULTIPLEX_TERMINAL_BINDING_V1.json",
            ]:
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text("{}",encoding="utf-8")
            d={
                "behavior_id":"PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
                "proof_mode":"T1_MULTIPLEXED_DIRECT_PROFESSIONAL_QUALITY_GATE",
                "decomposition":{"reused_adjacent_gate":"NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001","no_cross_behavior_score_inheritance":True},
                "candidate_visible_information":["OBJECTIVE","AUDIENCE","REQUIRED_TOPICS","RUBRIC_WEIGHTS","SOURCE_FACTS_WITH_PROVENANCE","CURRENT_DRAFT_OR_RENDER_STATE","EDIT_CANDIDATES","EDIT_BUDGET","DECLARED_NATIVE_FORMAT_METADATA"],
                "candidate_must_not_receive":["HIDDEN_ORACLE_FACTORS","REFERENCE_SOLUTION","GOLD_PLAN","ABLATION_LABELS","EXPECTED_SCORE_DELTA","TERMINAL_ACCEPTANCE_LABEL"],
                "terminal_surface":{"portfolio":"T1","synthetic_whole_domain_superset_required":False,"named_private_benchmarks_required_for_execution":False,"deletion_policy":"canonical/governance/PRIVATE_SURFACE_DEPENDENCY_DELETION_AND_ABSOLUTE_PROOF_MAP_V1.json"},
                "direct_instrumentation":["SELECTED_EDIT_IDS_EXIST_AND_EDIT_BUDGET_IS_RESPECTED","EVERY_SELECTED_CLAIM_IS_TRACEABLE_TO_VISIBLE_SOURCE_FACTS","SUPPORTED_REQUIRED_TOPICS_ARE_NOT_SILENTLY_DROPPED","AUDIENCE_AND_ANALYSIS_KIND_ARE_LOAD_BEARING","INDEPENDENT_RUBRIC_DELTA_BEATS_MECHANICS_ONLY_BASELINE_WHEN_QUALITY_JUDGMENT_IS_LOAD_BEARING","SEEDED_PLAN_ABLATION_DEGRADES_OR_FAILS_THE_RELEVANT_RUBRIC_DIMENSION","SEEDED_RESCUE_EDIT_RESTORES_OR_IMPROVES_THE_RELEVANT_RUBRIC_DIMENSION","ANY_NATIVE_EDIT_USED_BY_THE_CASE_PASSES_THE_SEPARATE_NATIVE_ARTIFACT_MECHANICAL_GATE"],
                "uncovered_scope_rule":"ANY_UNEXERCISED_LEAF_REMAINS_OPEN__NO_SCOPE_INHERITANCE",
                "post_freeze_accounting":{"adaptive_case_selection":False,"case_replacement":False,"tuning_replay":False,"result_to_runtime_feedback_during_wave":False,"oracle_or_threshold_edit_after_first_terminal_result":False,"failed_case_counts_as_failure":True},
                "dependencies":["canonical/runtime/p2_p3_information_safe_candidate_v2.py","canonical/governance/PROFESSIONAL_ARTIFACT_INTERNAL_PREWAVE_BINDING_V1.json","canonical/governance/NATIVE_ARTIFACT_T1_MULTIPLEX_TERMINAL_BINDING_V1.json"],
                "prewave_admissible":False,"independent_verification":None,"execution_authority":False,"terminal_results_observed":0,
            }
            if mut: mut(d)
            p=root/"canonical/governance/PROFESSIONAL_ARTIFACT_T1_MULTIPLEX_TERMINAL_BINDING_V1.json";p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d),encoding="utf-8")
            return evaluate(root)
    def test_valid(self): self.assertTrue(self.eval_case()["pass"])
    def test_oracle_leak(self): self.assertFalse(self.eval_case(lambda d:d["candidate_visible_information"].append("GOLD_PLAN"))["pass"])
    def test_private_surface_dependency_rejected(self): self.assertFalse(self.eval_case(lambda d:d["terminal_surface"].__setitem__("named_private_benchmarks_required_for_execution",True))["pass"])
    def test_scope_inheritance_rejected(self): self.assertFalse(self.eval_case(lambda d:d.__setitem__("uncovered_scope_rule","CREDIT_ALL"))["pass"])

if __name__=="__main__":
    unittest.main()
