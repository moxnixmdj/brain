from __future__ import annotations

import copy
import unittest

from canonical.runtime.structured_method_normalized_rule_graph_v3 import compile_graph
from canonical.runtime.structured_method_normalized_rule_oracle_v3 import score
from canonical.runtime.structured_method_terminal_population_v1 import (
    SOURCE_KINDS,
    generate_case,
    generate_population,
)


class StructuredMethodTerminalPopulationV1Tests(unittest.TestCase):
    def test_population_is_deterministic(self):
        self.assertEqual(generate_population(12345, 20), generate_population(12345, 20))

    def test_512_preflight_cases_pass_independent_oracle(self):
        seen_kinds = set()
        saw_exclusion = False
        saw_multi_output = False
        saw_shuffled_dependency = False
        for i, public in enumerate(generate_population(20261002, 512)):
            task = public["task"]
            seen_kinds.update(x["source_kind"] for x in task["requirements"])
            saw_exclusion |= any(x["status"] == "excluded" for x in task["requirements"])
            saw_multi_output |= len(task["required_outputs"]) > 1
            order = [int(x["id"].split("_")[1]) for x in task["normalized_rules"]]
            saw_shuffled_dependency |= order != sorted(order)
            candidate = compile_graph(public)
            verdict = score(public, candidate)
            self.assertTrue(verdict["pass"], (i, verdict, candidate))
        self.assertEqual(seen_kinds, set(SOURCE_KINDS))
        self.assertTrue(saw_exclusion)
        self.assertTrue(saw_multi_output)
        self.assertTrue(saw_shuffled_dependency)

    def test_wrong_graph_edge_is_rejected(self):
        public = generate_case(99, 7)
        candidate = compile_graph(public)
        self.assertTrue(score(public, candidate)["pass"])
        bad = copy.deepcopy(candidate)
        self.assertTrue(bad["edges"])
        bad["edges"][0]["source"] = "__wrong_source__"
        self.assertFalse(score(public, bad)["pass"])

    def test_different_seed_changes_population(self):
        self.assertNotEqual(generate_case(1, 0), generate_case(2, 0))

    def test_invalid_count_fails_closed(self):
        for value in (0, -1, True):
            with self.assertRaises(ValueError):
                generate_population(1, value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
