import hashlib, json, unittest
from pathlib import Path
from canonical.runtime import h100_reference_machine_u1_v1 as u
from canonical.runtime import h100_u1_bar_geometry_program_v1 as p

ROOT=Path(__file__).resolve().parents[2]
EVAL=ROOT/"canonical/governance/H100_U1_BAR_GEOMETRY_FRESH_EVAL_PRECOMMIT_V1.json"

class T(unittest.TestCase):
    def test_subject_bytes(self):
        self.assertEqual(len(p.PROGRAM_BYTES),5263)
        self.assertEqual(hashlib.sha256(p.PROGRAM_BYTES).hexdigest(),"567be36a04611c2314b24e5a9681eb10dc6cde9970c18932aa880c0633ea859f")
    def test_fresh_rasters(self):
        spec=json.loads(EVAL.read_text())
        for task in spec["tasks"]:
            got=u.execute(p.PROGRAM_BYTES,task["input"],step_limit=100000)["output"]
            self.assertEqual(got,task["gold"],task["id"])
    def test_six(self):
        self.assertEqual(len(json.loads(EVAL.read_text())["tasks"]),6)

if __name__=="__main__":
    unittest.main(verbosity=2)
