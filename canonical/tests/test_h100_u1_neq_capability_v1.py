import json, unittest
from pathlib import Path
from canonical.runtime import h100_reference_machine_u1 as u

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_U1_NEQ_CAPABILITY_PRECOMMIT_V1.json"
SUB=ROOT/"canonical/capabilities/h100/u1/H100_U1_NEQ_CAPABILITY_SUBJECT_V1.json"

class T(unittest.TestCase):
 def test_fresh_cases(self):
  pre=json.loads(PRE.read_text()); sub=json.loads(SUB.read_text())
  program=bytes.fromhex(sub["program_hex"])
  self.assertEqual(len(program),12)
  for x,t,gold in pre["fresh_cases"]:
   out=u.run(program,[x,t],**pre["resource_gate"])
   self.assertEqual(out["output"],[gold])
 def test_exact_bits(self):
  sub=json.loads(SUB.read_text())
  self.assertEqual(sub["program_bits"],96)
  self.assertEqual(sub["persistent_data_bytes"],0)
if __name__=="__main__": unittest.main(verbosity=2)
