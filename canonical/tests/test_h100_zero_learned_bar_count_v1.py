import unittest
import numpy as np
from canonical.runtime import h100_zero_learned_bar_count_v1 as b

class ZeroLearnedBarCountTests(unittest.TestCase):
    def _hbars(self,n:int)->np.ndarray:
        img=np.full((240,360,3),255,dtype=np.uint8)
        color=np.array([32,112,208],dtype=np.uint8)
        y=20
        for i in range(n):
            img[y:y+10,60:280-i*5]=color
            y+=18
        return img

    def _vbars(self,n:int)->np.ndarray:
        img=np.full((260,380,3),255,dtype=np.uint8)
        color=np.array([208,80,48],dtype=np.uint8)
        x=30
        for i in range(n):
            img[80+i%3*2:220,x:x+12]=color
            x+=24
        return img

    def test_horizontal_synthetic_count(self):
        out=b.count_bars_from_rgb(self._hbars(8))
        self.assertEqual(out["status"],"BAR_COUNT_IDENTIFIED")
        self.assertEqual(out["count"],8)
        self.assertEqual(out["orientation"],"HORIZONTAL")

    def test_vertical_synthetic_count(self):
        out=b.count_bars_from_rgb(self._vbars(9))
        self.assertEqual(out["status"],"BAR_COUNT_IDENTIFIED")
        self.assertEqual(out["count"],9)
        self.assertEqual(out["orientation"],"VERTICAL")

    def test_multiple_colors_aggregate(self):
        img=np.full((240,360,3),255,dtype=np.uint8)
        colors=[np.array([32,112,208],dtype=np.uint8),np.array([208,80,48],dtype=np.uint8)]
        for i in range(6):
            y=20+i*25
            img[y:y+10,40:180]=colors[i%2]
        out=b.count_bars_from_rgb(img)
        self.assertEqual(out["status"],"BAR_COUNT_IDENTIFIED")
        self.assertEqual(out["count"],6)

    def test_blank_abstains(self):
        img=np.full((120,180,3),255,dtype=np.uint8)
        self.assertTrue(b.count_bars_from_rgb(img)["status"].startswith("ABSTAIN"))

    def test_zero_learned(self):
        out=b.count_bars_from_rgb(self._hbars(5))
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["external_learned_capability_calls"],0)
        self.assertEqual(out["pretrained_vision_models"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
