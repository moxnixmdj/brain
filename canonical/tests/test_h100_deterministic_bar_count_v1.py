import unittest, tempfile
from PIL import Image, ImageDraw
from canonical.runtime import h100_deterministic_bar_count_v1 as b

class T(unittest.TestCase):
 def _img(self,n,horizontal=True):
  im=Image.new("RGB",(400,300),"white"); d=ImageDraw.Draw(im)
  if horizontal:
   for i in range(n): d.rectangle((80,20+i*25,80+120+i*3,35+i*25),fill=(40,118,221))
  else:
   for i in range(n): d.rectangle((30+i*30,250-(80+i*4),45+i*30,250),fill=(220,80,30))
  f=tempfile.NamedTemporaryFile(suffix=".png",delete=False); im.save(f.name); return f.name
 def test_horizontal(self):
  self.assertEqual(b.count_bars(self._img(7,True))["prediction"],7)
 def test_vertical(self):
  self.assertEqual(b.count_bars(self._img(6,False))["prediction"],6)
 def test_no_candidate(self):
  f=self._img(1,True)
  with self.assertRaises(b.BarGeometryError): b.count_bars(f)
if __name__=="__main__": unittest.main(verbosity=2)
