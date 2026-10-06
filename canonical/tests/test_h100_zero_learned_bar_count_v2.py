import unittest
import numpy as np
from canonical.runtime import h100_zero_learned_bar_count_v2 as b

class ZeroLearnedBarCountV2Tests(unittest.TestCase):
    def _blank(self,h=260,w=380):
        return np.full((h,w,3),255,dtype=np.uint8)

    def test_horizontal_same_color(self):
        img=self._blank()
        c=np.array([32,112,208],dtype=np.uint8)
        for i in range(8):
            y=20+i*25
            img[y:y+10,50:300-i*8]=c
        out=b.count_bars_from_rgb(img)
        self.assertEqual((out["status"],out["count"],out["orientation"]),("BAR_COUNT_IDENTIFIED",8,"HORIZONTAL"))

    def test_vertical_same_color(self):
        img=self._blank()
        c=np.array([208,80,48],dtype=np.uint8)
        for i in range(9):
            x=25+i*30
            img[80:225,x:x+12]=c
        out=b.count_bars_from_rgb(img)
        self.assertEqual((out["status"],out["count"],out["orientation"]),("BAR_COUNT_IDENTIFIED",9,"VERTICAL"))

    def test_two_large_different_color_bars(self):
        img=self._blank(h=600,w=850)
        img[108:278,65:797]=np.array([32,144,144],dtype=np.uint8)
        img[322:492,65:440]=np.array([80,96,112],dtype=np.uint8)
        out=b.count_bars_from_rgb(img)
        self.assertEqual((out["status"],out["count"],out["orientation"]),("BAR_COUNT_IDENTIFIED",2,"HORIZONTAL"))

    def test_thin_grid_stripes_not_bars(self):
        img=self._blank(h=600,w=850)
        img[108:278,65:797]=np.array([32,144,144],dtype=np.uint8)
        img[322:492,65:440]=np.array([80,96,112],dtype=np.uint8)
        stripe=np.array([32,144,128],dtype=np.uint8)
        for x in (157,251,345,439):
            img[108:278,x:x+2]=stripe
        out=b.count_bars_from_rgb(img)
        self.assertEqual(out["count"],2)
        self.assertEqual(out["orientation"],"HORIZONTAL")

    def test_alternating_colors_aggregate(self):
        img=self._blank()
        cols=[np.array([32,112,208],dtype=np.uint8),np.array([208,80,48],dtype=np.uint8)]
        for i in range(6):
            y=25+i*30
            img[y:y+12,40:260]=cols[i%2]
        out=b.count_bars_from_rgb(img)
        self.assertEqual(out["count"],6)

    def test_blank_abstains(self):
        self.assertTrue(b.count_bars_from_rgb(self._blank())["status"].startswith("ABSTAIN"))

    def test_zero_learned(self):
        img=self._blank()
        c=np.array([32,112,208],dtype=np.uint8)
        img[50:90,30:250]=c
        img[120:160,30:210]=c
        out=b.count_bars_from_rgb(img)
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["external_learned_capability_calls"],0)
        self.assertEqual(out["pretrained_vision_models"],0)
        self.assertEqual(out["ocr_models"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
