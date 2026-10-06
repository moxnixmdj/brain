import json, unittest
from pathlib import Path
from canonical.runtime import h100_reference_machine_u1_v1 as u

ROOT=Path(__file__).resolve().parents[2]
PROG=ROOT/"canonical/governance/H100_U1_MODULAR_AFFINE_PROGRAM_PRECOMMIT_V1.json"
EVAL=ROOT/"canonical/governance/H100_U1_MODULAR_AFFINE_FRESH_EVAL_PRECOMMIT_V1.json"

class T(unittest.TestCase):
    def test_fresh(self):
        p=json.loads(PROG.read_text())
        e=json.loads(EVAL.read_text())
        program=[tuple(x) for x in p["program"]]
        raw=u.encode(program)
        self.assertEqual(len(raw),9)
        for task in e["tasks"]:
            self.assertEqual(u.execute(raw,task["input"])["output"],task["gold"],task["id"])
    def test_six(self):
        self.assertEqual(len(json.loads(EVAL.read_text())["tasks"]),6)

if __name__=="__main__":
    unittest.main(verbosity=2)
