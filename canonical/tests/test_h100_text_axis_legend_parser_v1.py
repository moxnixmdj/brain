import json, unittest
from pathlib import Path
from canonical.runtime import h100_text_axis_legend_parser_v1 as p
ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_TEXT_AXIS_LEGEND_VISION_HOLDOUT_PRECOMMIT_V1.json"

class T(unittest.TestCase):
 def test_fresh_holdout(self):
  s=json.loads(PRE.read_text())
  rows=[]
  for task in s["tasks"]:
   got=p.parse(task["public_input"]["rows"])
   rows.append((task["id"],got,task["gold"]))
  self.assertTrue(all(got==gold for _,got,gold in rows),rows)
 def test_parser_has_no_gold_dependency(self):
  self.assertNotIn("gold",Path(p.__file__).read_text().lower())
 def test_font_scope(self):
  self.assertGreaterEqual(len(p.GLYPHS),18)
if __name__=="__main__": unittest.main(verbosity=2)
