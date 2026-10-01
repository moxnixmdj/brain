import json, tempfile, unittest
from pathlib import Path
from canonical.runtime.prequalification_stage_a_reducer_v2 import evaluate

TASK="session-window-debug"; RANK=16
LEDGER="canonical/capabilities/opus55/SESSION_WINDOW_DEBUG_RANK16_CONTAMINATION_LEDGER_V1.json"

class TestGenericStageA(unittest.TestCase):
    def test_live_rank16_repo_passes(self):
        root=Path(__file__).resolve().parents[2]
        out=evaluate(root,task=TASK,rank=RANK,ledger_path=LEDGER)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["authorization"],"STAGE_B_INSTRUCTION_EXPOSURE_ONLY")
        self.assertFalse(out["task_execution_authorized"])

    def test_wrong_task_fails(self):
        root=Path(__file__).resolve().parents[2]
        out=evaluate(root,task="wrong",rank=RANK,ledger_path=LEDGER)
        self.assertFalse(out["pass"])
        self.assertIn("QUALIFICATION_CONTAMINATION_LEDGER",out["failed_predicates"])

if __name__=="__main__": unittest.main()
