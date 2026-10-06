import tempfile, unittest
from pathlib import Path
import numpy as np
from PIL import Image
from canonical.runtime import h100_generic_bar_geometry_v0 as g

class T(unittest.TestCase):
 def _img(self,vertical=True):
  a=np.full((240,320,3),255,dtype=np.uint8)
  color=np.array([48,112,208],dtype=np.uint8)
  if vertical:
   for x,h in [(40,50),(90,90),(140,130),(190,70)]:
    a[220-h:220,x:x+20]=color
  else:
   for y,w in [(30,70),(80,120),(130,50),(180,160)]:
    a[y:y+20,20:20+w]=color
  f=tempfile.NamedTemporaryFile(suffix=".png",delete=False); f.close()
  Image.fromarray(a).save(f.name)
  return Path(f.name)
 def test_vertical(self):
  p=self._img(True); r=g.detect_bar_geometry(p)
  self.assertEqual(r["status"],"BARLIKE_GEOMETRY_IDENTIFIED")
  self.assertEqual(r["orientation"],"VERTICAL")
  self.assertEqual(len(r["bar_intervals"]),4)
 def test_horizontal(self):
  p=self._img(False); r=g.detect_bar_geometry(p)
  self.assertEqual(r["status"],"BARLIKE_GEOMETRY_IDENTIFIED")
  self.assertEqual(r["orientation"],"HORIZONTAL")
  self.assertEqual(len(r["bar_intervals"]),4)
 def test_zero_learned(self):
  p=self._img(True)
  self.assertEqual(g.detect_bar_geometry(p)["persistent_learned_bytes"],0)
if __name__=="__main__": unittest.main(verbosity=2)
