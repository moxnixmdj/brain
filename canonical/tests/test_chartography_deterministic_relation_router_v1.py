from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from canonical.runtime.chartography_deterministic_relation_router_v1 import (
    ChartographyRelationRouterError,
    solve_supported_relation,
)
from canonical.tests.test_chartography_deterministic_geometry_v1 import (
    BLACK,
    BLUE,
    CYAN,
    GREEN,
    ORANGE,
    PURPLE,
    RED,
    YELLOW,
    axes,
    bmp,
    canvas,
    dot,
    line,
    rect,
)


def write_case(tmp: Path, name: str, im) -> Path:
    p = tmp / f"{name}.bmp"
    p.write_bytes(bmp(im))
    return p


class DeterministicRelationRouterTests(unittest.TestCase):
    def test_exact_six_case_semantics(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)

            im = canvas(); axes(im)
            rect(im,55,120,90,160,RED); rect(im,110,80,145,160,GREEN); rect(im,165,40,200,160,BLUE)
            out = solve_supported_relation(
                write_case(tmp,"bar_order",im),
                "Which colored bar is tallest? Answer exactly one word: RED, GREEN, or BLUE.",
            )
            self.assertEqual((out["route"], out["answer"]), ("BAR_ORDERING","BLUE"))

            im = canvas(); axes(im)
            rect(im,75,64,115,160,CYAN); rect(im,150,112,190,160,YELLOW)
            out = solve_supported_relation(
                write_case(tmp,"ratio",im),
                "The cyan and yellow bars start at the same baseline. Cyan is how many times as tall as yellow? Answer exactly 2.",
            )
            self.assertEqual((out["route"], out["answer"]), ("BAR_RATIO","2"))

            im = canvas(); axes(im)
            pts=[(48,140),(85,120),(122,96),(159,70),(205,46)]
            for a,b in zip(pts,pts[1:]): line(im,*a,*b,RED,4)
            out = solve_supported_relation(
                write_case(tmp,"trend",im),
                "From left to right, does the red line increase or decrease in plotted value? Answer exactly INCREASE or DECREASE.",
            )
            self.assertEqual((out["route"], out["answer"]), ("LINE_TREND","INCREASE"))

            im = canvas(); axes(im)
            line(im,48,50,210,135,RED,4); line(im,48,135,210,50,BLUE,4)
            out = solve_supported_relation(
                write_case(tmp,"cross",im),
                "At the right side of the chart, which line is higher in plotted value? Answer exactly RED or BLUE.",
            )
            self.assertEqual((out["route"], out["answer"]), ("LINE_RIGHT_ORDER","BLUE"))

            im = canvas(); axes(im); line(im,130,25,130,160,BLACK,1)
            for p in [(50,55),(70,80),(88,108),(105,65),(116,130)]: dot(im,*p,GREEN,6)
            for p in [(155,75),(183,112),(214,52)]: dot(im,*p,RED,6)
            out = solve_supported_relation(
                write_case(tmp,"scatter",im),
                "How many green data points are left of the vertical divider? Answer exactly one digit.",
            )
            self.assertEqual((out["route"], out["answer"]), ("SCATTER_COUNT","5"))

            im = canvas(); axes(im)
            rect(im,60,100,85,160,PURPLE); rect(im,88,75,113,160,ORANGE)
            rect(im,155,55,180,160,PURPLE); rect(im,183,95,208,160,ORANGE)
            out = solve_supported_relation(
                write_case(tmp,"grouped",im),
                "There are two groups of purple/orange bars. In which group is the PURPLE bar taller than the ORANGE bar? Answer exactly LEFT or RIGHT.",
            )
            self.assertEqual((out["route"], out["answer"]), ("GROUPED_BAR_COMPARISON","RIGHT"))

    def test_effect_distinguishing_metamorphic_variants(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)

            im = canvas(); axes(im)
            line(im,48,135,210,50,RED,4); line(im,48,50,210,135,BLUE,4)
            out = solve_supported_relation(
                write_case(tmp,"cross_swap",im),
                "On the far right, which line is above the other? RED or BLUE.",
            )
            self.assertEqual(out["answer"], "RED")

            im = canvas(); axes(im)
            rect(im,60,55,85,160,PURPLE); rect(im,88,95,113,160,ORANGE)
            rect(im,155,100,180,160,PURPLE); rect(im,183,75,208,160,ORANGE)
            out = solve_supported_relation(
                write_case(tmp,"group_swap",im),
                "There are two groups of PURPLE and ORANGE bars. Which group has the PURPLE bar higher than the ORANGE bar, LEFT or RIGHT?",
            )
            self.assertEqual(out["answer"], "LEFT")

            im = canvas(); axes(im)
            rect(im,55,30,90,160,RED); rect(im,110,80,145,160,GREEN); rect(im,165,100,200,160,BLUE)
            out = solve_supported_relation(
                write_case(tmp,"bar_swap",im),
                "Among the RED, GREEN and BLUE bars, which bar is highest?",
            )
            self.assertEqual(out["answer"], "RED")

    def test_fail_closed_outside_supported_grammar(self):
        with tempfile.TemporaryDirectory() as td:
            tmp=Path(td); im=canvas(); axes(im)
            p=write_case(tmp,"blank",im)
            with self.assertRaisesRegex(ChartographyRelationRouterError,"UNSUPPORTED"):
                solve_supported_relation(p,"Explain the overall business meaning of this chart.")
            with self.assertRaisesRegex(ChartographyRelationRouterError,"EXACTLY_2"):
                solve_supported_relation(p,"At the right side, which line is higher: RED?")

if __name__ == "__main__":
    unittest.main(verbosity=2)
