from __future__ import annotations
import json
import os
import unittest

from canonical.runtime import m0a_raw_source_terminal_suite_v2 as suite
from canonical.runtime import m0a_raw_source_brain_candidate_v2 as candidate

class M0ARawSourceTerminalDiagnosticTests(unittest.TestCase):
    def test_oracle_never_enters_public_payload(self):
        case=suite.generate_case(123,0)
        public=suite.public_task(case)
        self.assertNotIn("_oracle",public)
        self.assertNotIn("requirements",public)
        self.assertNotIn("transform_kind",json.dumps(public))

    def test_candidate_does_not_import_evaluator(self):
        import inspect
        src=inspect.getsource(candidate)
        self.assertNotIn("m0a_raw_source_terminal_suite_v2",src)
        self.assertNotIn("_oracle",src)

    def test_diagnostic_executes_and_preserves_failures(self):
        seed=int(os.environ.get("PROJECT_BRAIN_POST_FREEZE_SEED","8675309"))
        out=suite.run_batch(seed,64,candidate.solve)
        self.assertEqual(out["case_count"],64)
        self.assertEqual(out["passed"]+out["failed"],64)
        print("PROJECT_BRAIN_M0A_DIAGNOSTIC "+json.dumps(out,sort_keys=True))

if __name__=="__main__":
    unittest.main(verbosity=2)
