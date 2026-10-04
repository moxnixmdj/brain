from __future__ import annotations

import unittest

from canonical.runtime import unknown_domain_direct_candidate_v1 as c
from canonical.runtime import unknown_domain_direct_generator_v1 as g
from canonical.runtime import unknown_domain_direct_scorer_v1 as s


class UnknownDomainDirectCandidateTests(unittest.TestCase):
    def test_candidate_closes_all_public_prequalification_fixtures(self):
        cases=g.generate("PUBLIC-PREQUALIFICATION-BEACON-0001")["cases"]
        results=[c.solve(case["visible"]) for case in cases]
        scored=s.score_cases(cases,results)
        self.assertTrue(scored["pass"],scored)
        self.assertEqual(scored["by_mode"]["IDENTIFIABLE_TRANSFER"],{"pass":24,"total":24})
        self.assertEqual(scored["by_mode"]["NONIDENTIFIABLE_ABSTAIN"],{"pass":12,"total":12})
        self.assertEqual(scored["by_mode"]["UNDERSPECIFIED_REQUEST_DISCRIMINATOR"],{"pass":12,"total":12})

    def test_zero_learned_and_zero_external_model_boundary(self):
        case=g.generate("PUBLIC-PREQUALIFICATION-BEACON-0002")["cases"][0]
        out=c.solve(case["visible"])
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["external_frontier_model_calls"],0)
        self.assertEqual(out["external_learned_capability_calls"],0)

    def test_candidate_does_not_need_hidden_evaluator(self):
        case=g.generate("PUBLIC-PREQUALIFICATION-BEACON-0003")["cases"][0]
        visible=case["visible"]
        self.assertNotIn("hidden_evaluator",visible)
        out=c.solve(visible)
        self.assertIn(out["verdict"],{"ANSWER","ABSTAIN","REQUEST_DISCRIMINATOR"})

    def test_tampered_source_receipt_fails_closed(self):
        case=g.generate("PUBLIC-PREQUALIFICATION-BEACON-0004")["cases"][0]
        visible=case["visible"]
        visible["source_primitives"][0]["verification_receipt"]["independent_verified"]=False
        with self.assertRaisesRegex(c.DirectCandidateError,"SOURCE_RECEIPT_NOT_INDEPENDENT"):
            c.solve(visible)


if __name__=="__main__":
    unittest.main(verbosity=2)
