from __future__ import annotations

import unittest
from pathlib import Path

from canonical.runtime import cad_t0_geometry_population as population
from canonical.runtime import cad_t0_route_specific_terminal_executor_v1 as ex


class CadT0RouteSpecificTerminalExecutorTests(unittest.TestCase):
    C = "TEST_ONLY_COMMITMENT"
    B = "TEST_ONLY_NONTERMINAL_BEACON"

    def test_static_dependency_preflight_fails_closed_on_reopened_cad_binding(self):
        out = ex.static_dependency_preflight(Path("."))
        self.assertFalse(out["pass"], out)
        self.assertIn("CAD_BINDING_NOT_PREWAVE_ADMISSIBLE", out["errors"])
        self.assertIn("CAD_ANTISHORTCUT_FALSIFICATION_ACTIVE", out["errors"])

    def test_exact_frozen_count_and_family_cycle(self):
        self.assertEqual(ex.COUNT, 128)
        cases = population.generate_post_freeze(self.C, self.B)
        self.assertEqual(len(cases), 128)
        self.assertEqual(
            [cases[i]["_oracle"]["family"] for i in range(8)],
            list(population.FAMILIES),
        )

    def test_all_eight_families_execute_information_safely(self):
        cases = population.generate_post_freeze(self.C, self.B)
        for i in range(8):
            with self.subTest(slot=i):
                row = ex.run_case(cases[i])
                self.assertTrue(row["pass"], row)
                self.assertFalse(row["candidate_hidden_oracle_present"])

    def test_full_executor_refuses_to_consume_cases_while_binding_reopened(self):
        out = ex.execute_cad_route(commitment=self.C, beacon=self.B, root=Path("."))
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "FAIL_CLOSED_PREEXECUTION")
        self.assertEqual(out["case_count"], 0)
        self.assertFalse(out["terminal_result"])

    def test_no_reduced_count_argument(self):
        with self.assertRaises(TypeError):
            ex.execute_cad_route(commitment=self.C, beacon=self.B, root=Path("."), count=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
