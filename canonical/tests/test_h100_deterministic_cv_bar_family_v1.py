import unittest,tempfile
from PIL import Image,ImageDraw
from canonical.runtime import h100_deterministic_cv_bar_family_v1 as b

class T(unittest.TestCase):
 def image(self,n,horizontal=True,multicolor=False):
  im=Image.new("RGB",(420,320),"white"); d=ImageDraw.Draw(im)
  colors=[(40,118,221),(220,80,30),(50,160,90)]
  if horizontal:
   for i in range(n): d.rectangle((80,20+i*28,80+100+i*5,38+i*28),fill=colors[i%3] if multicolor else colors[0])
  else:
   for i in range(n): d.rectangle((30+i*32,260-(80+i*6),48+i*32,260),fill=colors[i%3] if multicolor else colors[0])
  f=tempfile.NamedTemporaryFile(suffix=".png",delete=False); im.save(f.name); return f.name
 def test_horizontal(self): self.assertEqual(b.count_bars(self.image(7,True,False))["prediction"],7)
 def test_vertical(self): self.assertEqual(b.count_bars(self.image(6,False,False))["prediction"],6)
 def test_horizontal_multicolor(self): self.assertEqual(b.count_bars(self.image(8,True,True))["prediction"],8)
 def test_vertical_multicolor(self): self.assertEqual(b.count_bars(self.image(5,False,True))["prediction"],5)
if __name__=="__main__": unittest.main(verbosity=2)
