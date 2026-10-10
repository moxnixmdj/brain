from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from canonical.runtime import capability_parallel_frontier_v3 as p

def complete(work_id, cap_lcb, cap_ucb):
    row={
        "work_id":work_id,"scheduler_state":"READY_EXECUTION",
        "prerequisites_satisfied":True,"prerequisite_work_ids":[],
        "mutation_keys":[],"authority_keys":[],"explicit_conflict_work_ids":[],
        "evidence_conflict_keys":[],"evidence_acquisition_mode":"READ_ONLY",
        "vector_evidence_state":"COMPLETE",
    }
    for l,u in p.BENEFIT_INTERVALS:
        row[l]=1; row[u]=1
    for l,u in p.COST_INTERVALS:
        row[l]=1; row[u]=1
    row["expected_capability_gain_lcb"]=cap_lcb
    row["expected_capability_gain_ucb"]=cap_ucb
    row["vector_evidence"]={k:"e/"+work_id+"/"+k for k in p.VECTOR_FIELDS}
    return row

class ParallelFrontierV3Tests(unittest.TestCase):
    def test_overlap_does_not_fake_dominance(self):
        a=complete("A",2,3); b=complete("B",1,4)
        self.assertFalse(p._dominates(a,b))
        self.assertFalse(p._dominates(b,a))

    def test_postcomposition_phase_is_whole_leaf_domain_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            pp=root/p.PROFESSIONAL_SOURCE_REL
            ap=root/p.CURRENT_ASSURANCE_REL
            pp.parent.mkdir(parents=True,exist_ok=True)
            prof={
                "status":"X__12_OF_12_CURRENT_ROOT_BINDINGS__SAME_SUBJECT_COMPOSITION_ADMISSIBLE__NOT_LIVE_DEFAULT",
                "next":"RUN_WHOLE_LEAF_SCOPE_TRANSPORT__RUN_DOMAIN_SEMANTIC_AND_EXECUTION_CHALLENGES__RUN_FULL_CURRENT_MAIN_FULL_SYSTEM_REGRESSION",
                "same_subject_root_binding_frontier":{"verified_root_subject_binding_count":12,"composition_admissible":True},
                "final_subject":{"subject_id":"S","subject_sha256":"H"},
                "leaf_coverage_projection":{"partial_coverage_leaf_count":24,"verified_global_leaf_count":0,"open_global_leaf_count":24,"domain_semantic_closure":False,"domain_execution_closure":False},
            }
            ass={
                "schema":"PROJECT_BRAIN_CURRENT_ASSURANCE_CLOSURE_COMPILER_POINTER_V1",
                "status":"X__12_OF_12_CURRENT_ROOT_SUBJECT_BINDINGS__SAME_SUBJECT_COMPOSITION_ADMISSIBLE__NOT_LIVE_DEFAULT",
                "terminal_authority":False,"live_default":False,
                "activation":{"live_default":False,"required_before_promotion":sorted(p.EXPECTED_ASSURANCE_PROMOTION_BLOCKERS)},
                "professional_quality_same_subject_frontier":{"subject_id":"S","subject_sha256":"H","verified_root_subject_binding_count":12,"root_count":12,"composition_admissible":True,"next":"WHOLE_LEAF_SCOPE_TRANSPORT__DOMAIN_SEMANTIC_EXECUTION_EVIDENCE__FULL_CURRENT_MAIN_REGRESSION"},
            }
            pp.write_text(json.dumps(prof)); ap.write_text(json.dumps(ass))
            frontier={
                "scope":{"source_set":[{"path":p.PROFESSIONAL_SOURCE_REL,"git_blob_sha":p._git_blob_sha(pp)},{"path":p.CURRENT_ASSURANCE_REL,"git_blob_sha":p._git_blob_sha(ap)}]},
                "currentness_findings":[{"id":"PROFESSIONAL_CURRENT"},{"id":"ASSURANCE_CURRENT_PATH"}],
                "candidates":[
                    {"work_id":"PROFESSIONAL_QUALITY_V7_WHOLE_LEAF_DOMAIN_EVIDENCE","scheduler_state":"READY_EVIDENCE","prerequisites_satisfied":True,"prerequisite_work_ids":[],"mutation_keys":[],"authority_keys":[],"explicit_conflict_work_ids":[],"evidence_conflict_keys":[],"evidence_acquisition_mode":"READ_ONLY","vector_evidence_state":"PARTIAL","vector_evidence":{}},
                    {"work_id":"ASSURANCE_UVCK_V2_PROMOTION_GATES","scheduler_state":"BLOCKED","prerequisites_satisfied":False,"prerequisite_work_ids":["D"],"mutation_keys":[],"authority_keys":[],"explicit_conflict_work_ids":[],"evidence_conflict_keys":[],"evidence_acquisition_mode":"READ_ONLY","vector_evidence_state":"PARTIAL","vector_evidence":{}},
                ],
            }
            out=p.refresh_supported_dynamic_sources(frontier,root=root)
            self.assertEqual(out["dynamic_currentness"]["professional_next_root"],"WHOLE_LEAF_DOMAIN_EVIDENCE")
            self.assertEqual(out["dynamic_currentness"]["assurance_professional_count"],12)

if __name__=="__main__":
    unittest.main(verbosity=2)
