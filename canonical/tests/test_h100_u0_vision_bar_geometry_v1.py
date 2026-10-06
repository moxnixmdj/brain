import json
from pathlib import Path
import unittest
from canonical.runtime import h100_reference_machine_u0_v1 as u

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_U0_VISION_BAR_FRESH_HOLDOUT_PRECOMMIT_V1.json"
PROGRAM=ROOT/"canonical/capabilities/h100/u0_programs/vision_bar_geometry_v1.py"

class T(unittest.TestCase):
 def test_fresh_holdout(self):
  spec=json.loads(PRE.read_text())
  src=PROGRAM.read_text()
  rows=[]
  for task in spec["tasks"]:
   got=u.execute(src,task["public_input"])
   rows.append(got==task["gold"])
  self.assertEqual(rows,[True,True,True,True])
 def test_program_is_u0_valid(self):
  src=PROGRAM.read_text()
  u.parse_and_validate(src)
 def test_program_bits_positive(self):
  self.assertGreater(u.target_program_bits(PROGRAM.read_text()),0)
if __name__=="__main__": unittest.main(verbosity=2)
