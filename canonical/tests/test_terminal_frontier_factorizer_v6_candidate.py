import unittest
from canonical.runtime.terminal_frontier_factorizer_v6_candidate import (
    ATOMIC_V10, DERIVED, EXTERNAL_RESULT_ATOMS, STRUCTURAL_V10,
    STRUCTURAL_INDEPENDENT, INDEPENDENT, factorize,
)

class TestTerminalFrontierFactorizerV6Candidate(unittest.TestCase):
    def test_v10_input_is_exact_20(self):
        self.assertEqual(len(ATOMIC_V10),20)
        self.assertEqual(len(set(ATOMIC_V10)),20)

    def test_only_composition_reclassified_derived(self):
        self.assertEqual(DERIVED,{"COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR"})
        self.assertEqual(set(ATOMIC_V10)-set(INDEPENDENT),DERIVED)

    def test_direct15_unchanged(self):
        self.assertEqual(len(EXTERNAL_RESULT_ATOMS),15)
        self.assertTrue(EXTERNAL_RESULT_ATOMS <= set(INDEPENDENT))

    def test_structural_five_to_four_independent(self):
        self.assertEqual(len(STRUCTURAL_V10),5)
        self.assertEqual(len(STRUCTURAL_INDEPENDENT),4)
        self.assertNotIn("COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",STRUCTURAL_INDEPENDENT)

    def test_no_semantic_requirement_deleted(self):
        out=factorize()
        self.assertFalse(out["semantic_requirement_deleted"])
        self.assertEqual(out["derived_assertion_failure_reopens"],"ABC_SELECTED_CONTEXT_COVER")

    def test_counts(self):
        out=factorize()
        self.assertEqual(out["independent_terminal_conjunct_count"],19)
        self.assertEqual(out["direct_result_conjunct_count"],15)
        self.assertEqual(out["structural_independent_conjunct_count"],4)
        self.assertEqual(out["truth_repair_delta"],-1)
        self.assertEqual(out["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main()
