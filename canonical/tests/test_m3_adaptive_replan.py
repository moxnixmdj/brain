import unittest
from canonical.runtime.m3_contract_task_decomposition import ContractStep
from canonical.runtime.shared_decision_primitives import Worker
from canonical.runtime.m3_adaptive_replan import adaptive_replan

class Tests(unittest.TestCase):
    def test_replan_uses_alternative(self):
        steps=[
            ContractStep("route0",frozenset({"raw"}),frozenset({"done"}),1),
            ContractStep("extract",frozenset({"raw"}),frozenset({"facts"}),1),
            ContractStep("finish",frozenset({"facts"}),frozenset({"done"}),1),
        ]
        out=adaptive_replan(current_facts={"raw"},invalidated_facts=set(),observed_facts=set(),required_outputs={"done"},steps=steps,unavailable_step_ids={"route0"})
        self.assertEqual(out["status"],"PASS",out)
        self.assertEqual(out["task_ids"],["extract","finish"])

    def test_fact_retraction(self):
        steps=[ContractStep("restore",frozenset({"raw"}),frozenset({"valid"}),1),ContractStep("finish",frozenset({"valid"}),frozenset({"done"}),1)]
        out=adaptive_replan(current_facts={"raw","valid"},invalidated_facts={"valid"},observed_facts=set(),required_outputs={"done"},steps=steps)
        self.assertEqual(out["task_ids"],["restore","finish"])

    def test_ready_assignment(self):
        steps=[ContractStep("extract",frozenset({"raw"}),frozenset({"done"}),1)]
        out=adaptive_replan(
            current_facts={"raw"},invalidated_facts=set(),observed_facts=set(),required_outputs={"done"},steps=steps,
            workers=[Worker("w1",frozenset({"extract"}))],
            task_capabilities={"extract":frozenset({"extract"})},
        )
        self.assertEqual(out["status"],"PASS",out)
        self.assertEqual(out["ready_assignments"],{"extract":"w1"})

if __name__=="__main__":
    unittest.main(verbosity=2)
