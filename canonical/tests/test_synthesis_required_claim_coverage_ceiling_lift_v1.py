from __future__ import annotations
import copy, unittest
from canonical.runtime.synthesis_required_claim_coverage_ceiling_lift_verifier_v1 import CAND,SUITES,WAVE,POST,TARGETS,BIND,RESID,sha,load,evaluate

class CoverageCeilingLiftTests(unittest.TestCase):
    def docs(self):
        return load(CAND),load(SUITES),load(WAVE),load(POST),load(TARGETS),load(BIND),load(RESID),{"suites":sha(SUITES),"wave":sha(WAVE),"post":sha(POST),"targets":sha(TARGETS),"bind":sha(BIND),"resid":sha(RESID)}
    def test_live_candidate_is_blocked_until_scope_relation_is_independently_proved(self):
        out=evaluate(*self.docs())
        self.assertFalse(out["pass"],out)
        self.assertIn("SOURCE_SCOPE_NOT_PROVED_EXACT_OR_SUPERSET_OF_TARGET_SCOPE",out["errors"])
        self.assertIn("SOURCE_TARGET_SCOPE_RELATION_NOT_INDEPENDENTLY_VERIFIED",out["errors"])

    def test_exact_independently_verified_scope_relation_allows_the_ceiling_theorem(self):
        docs=list(self.docs()); docs[0]=copy.deepcopy(docs[0])
        docs[0]["scope_firewall"]["verified_source_to_target_relation"]="EXACT"
        docs[0]["scope_firewall"]["independent_verification"]=True
        docs[0]["scope_firewall"]["verification_receipt"]="receipt://independent/same-scope-proof"
        out=evaluate(*docs)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["brain_minus_comparator_lower_bound"],0.0)
        self.assertEqual(set(out["remaining_unproved"]),{"metric:matched_quality","matched_quality_noninferiority"})
    def test_overclaim_matched_quality_fails(self):
        docs=list(self.docs()); docs[0]=copy.deepcopy(docs[0]); docs[0]["explicitly_not_proved"]=[]
        out=evaluate(*docs); self.assertFalse(out["pass"])
        self.assertIn("MATCHED_QUALITY_EXCLUSION_MISSING",out["errors"])
    def test_ceiling_mutation_fails(self):
        docs=list(self.docs()); docs[1]=copy.deepcopy(docs[1])
        suite=next(x for x in docs[1]["suites"] if x.get("behavior_id")=="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001")
        suite["oracle"].remove("100_PERCENT_REQUIRED_CLAIM_COVERAGE")
        out=evaluate(*docs); self.assertFalse(out["pass"])
        self.assertIn("COVERAGE_CEILING_ORACLE_MISSING",out["errors"])
    def test_target_threshold_mutation_fails(self):
        docs=list(self.docs()); docs[4]=copy.deepcopy(docs[4])
        target=next(x for x in docs[4]["targets"] if x.get("predicate_id")=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR")
        req=next(x for x in target["metric_requirements"] if x.get("metric")=="required_claim_coverage_noninferiority")
        req["threshold"]=0.1
        out=evaluate(*docs); self.assertFalse(out["pass"])
        self.assertIn("TARGET_METRIC_REQUIREMENT_MISMATCH",out["errors"])

if __name__=="__main__": unittest.main(verbosity=2)
