from __future__ import annotations
import copy, unittest
from canonical.runtime.synthesis_implication_residual_verifier_v1 import (
    INPUT,TARGETS,BINDING,RECEIPT,ALGEBRA,blob_sha,evaluate,load
)

class SynthesisImplicationResidualTests(unittest.TestCase):
    def docs(self):
        return (
            load(INPUT),load(TARGETS),load(BINDING),load(RECEIPT),
            {"targets":blob_sha(TARGETS),"binding":blob_sha(BINDING),"receipt":blob_sha(RECEIPT),"algebra":blob_sha(ALGEBRA)}
        )

    def test_exact_residual(self):
        out=evaluate(*self.docs())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["missing_atoms"],["metric:matched_quality"])
        self.assertEqual(set(out["missing_metric_bounds"]),{"matched_quality_noninferiority","required_claim_coverage_noninferiority"})
        self.assertFalse(out["implies_target"])

    def test_invented_numeric_bound_fails(self):
        doc,targets,binding,receipt,shas=self.docs()
        doc=copy.deepcopy(doc)
        doc["algebra_input"]["witness"]["metric_bounds"]={"matched_quality_noninferiority":{"lower":0.0}}
        out=evaluate(doc,targets,binding,receipt,shas)
        self.assertFalse(out["pass"])
        self.assertIn("WITNESS_METRIC_BOUND_INVENTION",out["errors"])

    def test_invented_implication_edge_fails(self):
        doc,targets,binding,receipt,shas=self.docs()
        doc=copy.deepcopy(doc)
        doc["algebra_input"]["verified_implications"]=[{"if_all":[],"then":["metric:matched_quality"],"receipt":"fake","verified":True}]
        out=evaluate(doc,targets,binding,receipt,shas)
        self.assertFalse(out["pass"])
        self.assertIn("UNVERIFIED_IMPLICATION_EDGE_FORBIDDEN",out["errors"])

    def test_target_mutation_fails(self):
        doc,targets,binding,receipt,shas=self.docs()
        doc=copy.deepcopy(doc)
        doc["algebra_input"]["target"]["required_atoms"].remove("metric:matched_quality")
        out=evaluate(doc,targets,binding,receipt,shas)
        self.assertFalse(out["pass"])
        self.assertIn("TARGET_INPUT_NOT_EXACT_CANONICAL_ROW",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
