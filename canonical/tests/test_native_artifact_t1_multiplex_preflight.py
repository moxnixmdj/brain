from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime.native_artifact_t1_multiplex_preflight import evaluate
class Tests(unittest.TestCase):
    def run(self,mut=None):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for rel in ["canonical/runtime/native_artifact_cross_format_candidate_v1.py","canonical/runtime/native_artifact_cross_format_proof_v1.py","canonical/runtime/native_artifact_render_preservation_proof_v1.py"]:
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text("",encoding="utf-8")
            d={"behavior_id":"NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001","proof_mode":"T1_MULTIPLEXED_MECHANICAL_GATE_PLUS_PUBLIC_PROFESSIONAL_BAR","decomposition":{"excluded_adjacent_behavior":"SEMANTIC_TARGET_SELECTION_AND_PROFESSIONAL_QUALITY_JUDGMENT","adjacent_behavior_id":"PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"},"format_scope":{"docx":{"edit_kind":"XML_SET_TEXT"},"xlsx":{"edit_kind":"XML_SET_TEXT"},"pptx":{"edit_kind":"XML_SET_TEXT"},"pdf":{"edit_kind":"PDF_REPLACE_UNIQUE_TEXT"}},"candidate_visible_information":["NATIVE_ARTIFACT_BYTES"],"independent_preflights":["a","b"],"terminal_surface":{"portfolio":"T1","synthetic_whole_domain_superset_required":False},"abstention":{"silent_fallback":False},"contamination":{"post_freeze_case_specific_tuning":False,"case_replacement":False,"result_to_runtime_feedback_during_wave":False,"oracle_or_threshold_edit_after_first_terminal_result":False},"execution_authority":False,"terminal_results_observed":0}
            if mut:mut(d)
            p=root/"canonical/governance/NATIVE_ARTIFACT_T1_MULTIPLEX_TERMINAL_BINDING_V1.json";p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d),encoding="utf-8")
            return evaluate(root)
    def test_valid(self):self.assertTrue(self.run()["pass"])
    def test_oracle_leak(self):self.assertFalse(self.run(lambda d:d["candidate_visible_information"].append("RENDER_PIXEL_DIFF_ORACLE"))["pass"])
    def test_scope_stretch(self):self.assertFalse(self.run(lambda d:d["terminal_surface"].__setitem__("synthetic_whole_domain_superset_required",True))["pass"])
if __name__=="__main__":unittest.main()
