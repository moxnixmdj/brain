import unittest
import numpy as np
from canonical.runtime import h100_zero_learned_bar_count_v3 as b

class ZeroLearnedBarCountV3Tests(unittest.TestCase):
    def blank(self,h=600,w=850):
        return np.full((h,w,3),255,dtype=np.uint8)

    def test_two_large_different_color_horizontal(self):
        img=self.blank()
        img[108:278,65:797]=[32,144,144]
        img[322:492,65:440]=[80,96,112]
        self.assertEqual(b.count_bars_from_rgb(img)["count"],2)

    def test_short_second_horizontal_bar(self):
        img=self.blank()
        img[105:276,81:786]=[208,32,112]
        img[320:492,81:137]=[80,96,112]
        self.assertEqual(b.count_bars_from_rgb(img)["count"],2)

    def test_five_vertical_different_colors_with_sparse_label_tails(self):
        img=self.blank(h=507,w=858)
        colors=[[224,32,32],[112,144,32],[144,48,128],[16,144,208],[224,80,16]]
        xs=[57,218,379,540,701]
        tops=[255,127,121,109,65]
        for c,x,top in zip(colors,xs,tops):
            img[top:435,x:x+107]=c
            # sparse same-color tail below baseline; dense-core extractor must ignore it
            img[470:490,x:x+8]=c
        self.assertEqual(b.count_bars_from_rgb(img)["count"],5)

    def test_stacked_horizontal_rows_count_once(self):
        img=self.blank(h=600,w=800)
        for i in range(12):
            y=40+i*40
            split=380-i*8
            img[y:y+24,240:split]=[32,112,208]
            img[y:y+24,split:630]=[0,32,48]
        self.assertEqual(b.count_bars_from_rgb(img)["count"],12)

    def test_thin_stripes_rejected(self):
        img=self.blank()
        img[100:260,60:760]=[32,144,144]
        img[320:480,60:430]=[80,96,112]
        for x in (150,250,350,450):
            img[100:260,x:x+2]=[32,144,128]
        self.assertEqual(b.count_bars_from_rgb(img)["count"],2)

    def test_blank_abstains(self):
        self.assertTrue(b.count_bars_from_rgb(self.blank())["status"].startswith("ABSTAIN"))

    def test_zero_learned(self):
        img=self.blank()
        img[100:200,60:500]=[32,112,208]
        img[260:360,60:400]=[32,112,208]
        out=b.count_bars_from_rgb(img)
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["external_learned_capability_calls"],0)
        self.assertEqual(out["pretrained_vision_models"],0)
        self.assertEqual(out["ocr_models"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
