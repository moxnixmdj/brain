import json
from pathlib import Path
import unittest
from canonical.runtime import h100_axes_text_legend_raster_parser_v1 as p

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_AXES_TEXT_LEGEND_RASTER_FRESH_HOLDOUT_V1.json"

class T(unittest.TestCase):
 def test_fresh_holdout(self):
  spec=json.loads(PRE.read_text())
  got=[p.parse(t["rows"],t["query"]) for t in spec["tasks"]]
  self.assertEqual(got,[t["gold"] for t in spec["tasks"]])
 def test_templates_are_explicit_persistent_state(self):
  self.assertEqual(len(p.TEMPLATES),10)
 def test_no_case_specific_colors(self):
  src=(ROOT/"canonical/runtime/h100_axes_text_legend_raster_parser_v1.py").read_text()
  for c in ["'r'","'b'","'g'","'m'","'u'","'v'","'c'","'d'","'K'"]:
   self.assertNotIn(c,src)
if __name__=="__main__": unittest.main(verbosity=2)
