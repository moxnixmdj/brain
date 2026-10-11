from __future__ import annotations

import unittest

from canonical.runtime.chartography_axis_calibration_v1 import (
    AxisCalibrationError,
    infer_linear_axes,
    pixel_to_x,
    pixel_to_y,
)


def word(text,cx,cy,w=18,h=10,line=1):
    return {
        "text":str(text),"cx":float(cx),"cy":float(cy),
        "left":float(cx-w/2),"top":float(cy-h/2),"width":w,"height":h,
        "block_num":1,"par_num":1,"line_num":line,"word_num":1,
    }


class AxisCalibrationTests(unittest.TestCase):
    def test_recovers_affine_xy_axes_with_distractor_numbers(self):
        words=[]
        for i,v in enumerate([0,20,40,60,80,100]):
            words.append(word(v,80+3.7*v,340,line=10))
        for i,v in enumerate([0,1,2,3,4,5,6]):
            words.append(word(v,55,320-45*v,line=20+i))
        # Legend-like distractor pairs must not win the repeated-coordinate vote.
        words += [word("700",500,80,line=30),word("0.02",560,80,line=30)]
        words += [word("900",500,105,line=31),word("0.03",560,105,line=31)]
        out=infer_linear_axes(words,image_width=700,image_height=420)
        self.assertAlmostEqual(pixel_to_x(out,265),50,places=6)
        self.assertAlmostEqual(pixel_to_y(out,185),3,places=6)

    def test_non_linear_ticks_fail_closed(self):
        words=[word(v,80+i*60,340,line=10) for i,v in enumerate([0,10,40,90])]
        words += [word(v,55,320-i*45,line=20+i) for i,v in enumerate([0,1,2,3])]
        with self.assertRaises(AxisCalibrationError):
            infer_linear_axes(words,image_width=500,image_height=400)


if __name__=="__main__":
    unittest.main()
