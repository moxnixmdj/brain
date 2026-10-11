from __future__ import annotations
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.chartography_crop_tool_v1 import crop_image

class CropToolTests(unittest.TestCase):
    def test_pixel_exact_and_bounds(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); src=root/"src.png"; dst=root/"crop.png"
            im=Image.new("RGB",(8,8),(255,0,0))
            for x in range(2,6):
                for y in range(1,5):
                    im.putpixel((x,y),(0,0,255))
            im.save(src)
            out=crop_image(src,dst,2,1,6,5)
            self.assertEqual(out["input_size"],(8,8))
            self.assertEqual(out["output_size"],(4,4))
            with Image.open(dst) as got:
                self.assertEqual(got.size,(4,4))
                self.assertTrue(all(px==(0,0,255) for px in got.getdata()))
            for box in ((-1,0,2,2),(0,0,9,2),(2,2,2,3)):
                with self.assertRaises(ValueError):
                    crop_image(src,dst,*box)

if __name__=="__main__":
    unittest.main()
