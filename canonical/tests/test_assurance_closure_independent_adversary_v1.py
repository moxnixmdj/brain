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

    def test_differential_corpus_matches(self):
        out=adv.run()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["case_count"],11)
        self.assertEqual(out["matched_count"],11)
        self.assertEqual(out["mismatches"],[])
        self.assertFalse(out["terminal_authority"])


if __name__=="__main__":
    unittest.main()
