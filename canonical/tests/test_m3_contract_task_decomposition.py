import unittest

from canonical.runtime.m3_contract_task_decomposition import ContractStep, compile_task_plan


class Tests(unittest.TestCase):
    def test_infers_chain_without_predeclared_dependencies(self):
        out = compile_task_plan(
            initial_facts={"raw"},
            required_outputs={"report"},
            steps=[
                ContractStep("extract", frozenset({"raw"}), frozenset({"facts"}), 1),
                ContractStep("write", frozenset({"facts"}), frozenset({"report"}), 1),
            ],
        )
        self.assertEqual(out["status"], "PASS", out)
        self.assertEqual(out["task_ids"], ["extract", "write"])
        self.assertEqual(out["dependencies"], {"extract": [], "write": ["extract"]})

    def test_global_minimum_cost_beats_shorter_expensive_plan(self):
        out = compile_task_plan(
            initial_facts={"x"},
            required_outputs={"z"},
            steps=[
                ContractStep("direct", frozenset({"x"}), frozenset({"z"}), 5),
                ContractStep("a", frozenset({"x"}), frozenset({"y"}), 1),
                ContractStep("b", frozenset({"y"}), frozenset({"z"}), 1),
            ],
        )
        self.assertEqual(out["task_ids"], ["a", "b"])
        self.assertEqual(out["total_cost"], 2)

    def test_min_task_count_breaks_equal_cost_tie(self):
        out = compile_task_plan(
            initial_facts={"x"},
            required_outputs={"z"},
            steps=[
                ContractStep("direct", frozenset({"x"}), frozenset({"z"}), 2),
                ContractStep("a", frozenset({"x"}), frozenset({"y"}), 1),
                ContractStep("b", frozenset({"y"}), frozenset({"z"}), 1),
            ],
        )
        self.assertEqual(out["task_ids"], ["direct"])

    def test_lexicographic_tie_break_is_deterministic(self):
        out = compile_task_plan(
            initial_facts={"x"},
            required_outputs={"z"},
            steps=[
                ContractStep("beta", frozenset({"x"}), frozenset({"z"}), 1),
                ContractStep("alpha", frozenset({"x"}), frozenset({"z"}), 1),
            ],
        )
        self.assertEqual(out["task_ids"], ["alpha"])

    def test_unverified_and_unavailable_steps_are_ineligible(self):
        out = compile_task_plan(
            initial_facts={"x"},
            required_outputs={"z"},
            steps=[
                ContractStep("guess", frozenset({"x"}), frozenset({"z"}), 0, verified=False),
                ContractStep("offline", frozenset({"x"}), frozenset({"z"}), 0, available=False),
            ],
        )
        self.assertEqual(out["status"], "ESCALATE", out)

    def test_cycle_without_seed_escalates(self):
        out = compile_task_plan(
            initial_facts={"x"},
            required_outputs={"z"},
            steps=[
                ContractStep("a", frozenset({"b"}), frozenset({"c"})),
                ContractStep("b", frozenset({"c"}), frozenset({"b"})),
                ContractStep("z", frozenset({"b"}), frozenset({"z"})),
            ],
        )
        self.assertEqual(out["status"], "ESCALATE", out)

    def test_already_satisfied_requires_no_steps(self):
        out = compile_task_plan(
            initial_facts={"done"},
            required_outputs={"done"},
            steps=[],
        )
        self.assertEqual(out["status"], "PASS", out)
        self.assertEqual(out["task_ids"], [])

    def test_duplicate_ids_fail_closed(self):
        out = compile_task_plan(
            initial_facts={"x"},
            required_outputs={"z"},
            steps=[
                ContractStep("dup", frozenset({"x"}), frozenset({"y"})),
                ContractStep("dup", frozenset({"y"}), frozenset({"z"})),
            ],
        )
        self.assertEqual(out["status"], "FAIL_CLOSED", out)

    def test_invalid_cost_fails_closed(self):
        out = compile_task_plan(
            initial_facts={"x"},
            required_outputs={"z"},
            steps=[ContractStep("bad", frozenset({"x"}), frozenset({"z"}), float("nan"))],
        )
        self.assertEqual(out["status"], "FAIL_CLOSED", out)

    def test_empty_required_outputs_fail_closed(self):
        out = compile_task_plan(initial_facts={"x"}, required_outputs=set(), steps=[])
        self.assertEqual(out["status"], "FAIL_CLOSED", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
