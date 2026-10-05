import copy, unittest
from canonical.runtime import synthesis_whole_leaf_target_obligation_cut_v1 as cut

class TestSynthesisWholeLeafTargetObligationCut(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs,cls.blob_errors=cut.load()

    def run(self,docs=None):
        return cut.evaluate(copy.deepcopy(self.docs if docs is None else docs))

    def test_current_cut_is_valid_and_five_roots_remain(self):
        out=cut.derive()
        self.assertTrue(out["valid"],out)
        self.assertTrue(out["exact_blob_binding"],out)
        self.assertFalse(out["whole_leaf_scope_complete"])
        self.assertFalse(out["whole_leaf_current_terminal_obligation"])
        self.assertTrue(out["predicate_target_scope_closed"])
        self.assertTrue(out["matched_performance_open"])
        self.assertEqual(out["scope_root_count_before"],6)
        self.assertEqual(out["scope_root_count_after"],5)

    def test_reopens_if_target_entailment_becomes_mandatory(self):
        d=copy.deepcopy(self.docs)
        for e in d["sep"]["current_frontier_audit"]["edges"]:
            if e.get("family")=="PROFESSIONAL_KNOWLEDGE_WORK" and e.get("behavior_id")=="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001":
                e["mandatory_from_registry_incidence"]=True
        out=self.run(d)
        self.assertFalse(out["valid"])
        self.assertIn("SYNTHESIS_EDGE_BECAME_MANDATORY_WITHOUT_RECOMPUTE",out["errors"])

    def test_reopens_if_communication_target_dimensions_expand(self):
        d=copy.deepcopy(self.docs)
        p=next(x for x in d["protocols"]["protocols"] if x["family"]=="COMMUNICATION_AND_SYNTHESIS")
        p["task_dimensions"].append("new target dimension")
        out=self.run(d)
        self.assertFalse(out["valid"])
        self.assertIn("COMMUNICATION_TARGET_DIMENSIONS_CHANGED",out["errors"])

    def test_fails_if_target_scope_certificate_weakens(self):
        d=copy.deepcopy(self.docs)
        d["cert"]["coverage_complete"]=False
        out=self.run(d)
        self.assertFalse(out["valid"])
        self.assertIn("CERT_SCOPE_NOT_COMPLETE_STRONGER_EXACT_UNION",out["errors"])

    def test_never_upgrades_whole_leaf_scope_truth(self):
        d=copy.deepcopy(self.docs)
        d["collision"]["fail_closed_truth"]["whole_behavior_leaf_input_domain_scope_complete"]=True
        out=self.run(d)
        self.assertFalse(out["valid"])
        self.assertIn("COLLISION_NO_LONGER_FAILS_CLOSED_ON_WHOLE_LEAF",out["errors"])

if __name__=="__main__":
    unittest.main()
