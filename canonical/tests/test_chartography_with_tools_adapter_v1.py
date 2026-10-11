from __future__ import annotations
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.chartography_with_tools_adapter_v1 import run_with_tools

class WithToolsAdapterTests(unittest.TestCase):
    def test_crop_then_final_and_fail_closed(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); src=root/"chart.png"
            im=Image.new("RGB",(10,10),(255,255,255))
            for x in range(4,8):
                for y in range(3,7):
                    im.putpixel((x,y),(0,0,255))
            im.save(src)
            calls=[]
            def fake(image_path,prompt,transcript):
                calls.append((Path(image_path).name,len(transcript)))
                if not transcript:
                    return '{"tool":"crop","left":4,"top":3,"right":8,"bottom":7}'
                with Image.open(image_path) as cur:
                    self.assertEqual(cur.size,(4,4))
                    self.assertTrue(all(px==(0,0,255) for px in cur.getdata()))
                return '{"final":"blue"}'
            out=run_with_tools(src,"What color?",fake,workdir=root/"work",max_crop_calls=2)
            self.assertEqual(out["answer"],"blue")
            self.assertEqual(out["crop_calls"],1)
            self.assertEqual(calls,[("chart.png",0),("crop_00.png",1)])
            with self.assertRaises(RuntimeError):
                run_with_tools(src,"x",lambda *args:'{"tool":"crop","left":0,"top":0,"right":2,"bottom":2}',workdir=root/"limit",max_crop_calls=0)
            with self.assertRaisesRegex(ValueError,"MODEL_ACTION_MUST_BE_JSON"):
                run_with_tools(src,"x",lambda *args:"not json",workdir=root/"bad")

if __name__=="__main__":
    unittest.main()
