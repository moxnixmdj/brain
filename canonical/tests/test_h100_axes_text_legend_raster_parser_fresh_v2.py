import json
from pathlib import Path
import unittest
from canonical.runtime import h100_axes_text_legend_raster_parser_v1 as p
from canonical.runtime import h100_axes_text_legend_holdout_renderer_v2 as r

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_AXES_TEXT_LEGEND_RASTER_FRESH_HOLDOUT_V2.json"

class T(unittest.TestCase):
 def test_fresh_v2(self):
  spec=json.loads(PRE.read_text())
  got=[]
  for case in spec["cases"]:
   rows=r.render(case["layout"])
   got.append(p.parse(rows,case["query"]))
  self.assertEqual(got,[c["gold"] for c in spec["cases"]])
if __name__=="__main__": unittest.main(verbosity=2)
