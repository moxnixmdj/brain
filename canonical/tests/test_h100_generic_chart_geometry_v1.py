import tempfile,unittest
from pathlib import Path
from PIL import Image,ImageDraw
from canonical.runtime import h100_generic_chart_geometry_v1 as g

class T(unittest.TestCase):
 def _bar(self,color=(100,100,100),horizontal=False):
  im=Image.new("RGB",(240,200),"white"); d=ImageDraw.Draw(im)
  vals=[40,75,55]
  if not horizontal:
   for i,v in enumerate(vals): d.rectangle([35+i*45,180-v,50+i*45,179],fill=color)
  else:
   for i,v in enumerate(vals): d.rectangle([15,30+i*45,14+v,45+i*45],fill=color)
  f=tempfile.NamedTemporaryFile(suffix=".png",delete=False);f.close();im.save(f.name);return Path(f.name)
 def test_grayscale_bars(self):
  r=g.parse_chart_geometry(self._bar((120,120,120)))
  self.assertEqual(r["chart_type"],"BAR"); self.assertEqual(r["category_count"],3)
  self.assertEqual(g.answer_geometry(r,"ARGMAX_INDEX"),1)
 def test_horizontal(self):
  r=g.parse_chart_geometry(self._bar((120,180,140),True))
  self.assertEqual(r["orientation"],"HORIZONTAL"); self.assertEqual(r["category_count"],3)
 def test_zero_learned(self):
  self.assertEqual(g.parse_chart_geometry(self._bar())["persistent_learned_bytes"],0)
if __name__=="__main__":unittest.main(verbosity=2)
