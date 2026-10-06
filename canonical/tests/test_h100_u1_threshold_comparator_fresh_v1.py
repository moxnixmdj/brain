import json, unittest
from pathlib import Path
from canonical.runtime import h100_reference_machine_u1_v1 as u
from canonical.runtime import h100_u1_threshold_comparator_program_v1 as p

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_U1_THRESHOLD_COMPARATOR_FRESH_EVAL_PRECOMMIT_V1.json"

class T(unittest.TestCase):
    def test_program_size(self):
        self.assertEqual(len(p.PROGRAM_BYTES),73)
    def test_fresh_tasks(self):
        spec=json.loads(PRE.read_text())
        for task in spec["tasks"]:
            self.assertEqual(u.execute(p.PROGRAM_BYTES,task["input"])["output"],task["gold"],task["id"])
    def test_six_tasks(self):
        self.assertEqual(len(json.loads(PRE.read_text())["tasks"]),6)

if __name__=="__main__":
    unittest.main(verbosity=2)
