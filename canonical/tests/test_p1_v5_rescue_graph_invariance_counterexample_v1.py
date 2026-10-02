from __future__ import annotations
import inspect
import unittest

from canonical.runtime import p1_v5_rescue_graph_invariance_counterexample_v1 as cx
from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as v5


class Tests(unittest.TestCase):
    def test_counterexample_reproduces(self):
        out = cx.evaluate()
        self.assertTrue(out["status"].startswith("COUNTEREXAMPLE__"), out)
        self.assertTrue(out["original_v5_verdict"]["rescued"])
        self.assertTrue(out["mutated_v5_verdict"]["rescued"])
        self.assertNotEqual(
            out["original_terminal_failed_resources"],
            out["mutated_terminal_failed_resources"],
        )

    def test_v5_rescue_function_has_no_graph_or_terminal_read(self):
        src = inspect.getsource(v5.evaluate_intervention)
        self.assertNotIn('["task"]', src)
        self.assertNotIn("trajectory", src)
        self.assertNotIn("terminal_failed_resources", src)
        self.assertIn("required_root_repairs", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
