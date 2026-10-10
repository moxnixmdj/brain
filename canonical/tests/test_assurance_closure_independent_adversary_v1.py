from __future__ import annotations

import unittest

from canonical.runtime import assurance_closure_adversary_v1 as adv
from canonical.runtime import assurance_closure_reference_checker_v1 as ref


class AssuranceClosureIndependentAdversaryV1Tests(unittest.TestCase):
    def test_reference_base_structurally_closes(self):
        out=ref.check(adv.challenge_corpus()[0][1])
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["representation_closure"])
        self.assertTrue(out["proof_closure"])
        self.assertFalse(out["terminal_authority"])

    def test_reference_supported_defeater_dominates_unresolved_regardless_of_order(self):
        for order in (["open_d","active_d"], ["active_d","open_d"]):
            g=adv._base()
            g["nodes"].extend([
                {"id":"open_d","type":"DEFEATER","status":"OPEN"},
                {"id":"active_d","type":"DEFEATER","status":"SUPPORTED","depends_on":["de"],"defeated_by":[]},
                {"id":"de","type":"EVIDENCE","status":"SUPPORTED","authoritative_leaf":True},
            ])
            g["nodes"][0]["defeated_by"]=order
            out=ref.check(g)
            self.assertEqual(out["active_defeater_ids"],["active_d"],(order,out))
            self.assertEqual(out["unresolved_defeater_ids"],[],(order,out))
            self.assertFalse(out["proof_closure"],(order,out))

    def test_differential_corpus_matches(self):
        out=adv.run()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["case_count"],13)
        self.assertEqual(out["matched_count"],13)
        self.assertEqual(out["mismatches"],[])
        self.assertFalse(out["terminal_authority"])


if __name__=="__main__":
    unittest.main()
