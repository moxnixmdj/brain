from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from canonical.runtime.bound_capabilities import chart_axis_title_unit_binding_v1 as c


def cand(text, conf=95, source="test"):
    return {
        "text": text,
        "confidence": conf,
        "source": source,
        "evidence_kind": "SUPPLIED_CANDIDATE",
    }


class ChartAxisTitleUnitBindingV1Tests(unittest.TestCase):
    def test_frequency_khz(self):
        out=c.parse_axis_label("Frequency (kHz)")
        self.assertEqual(out["semantic_role"],"FREQUENCY")
        self.assertEqual(out["canonical_unit"],"KILOHERTZ")
        self.assertEqual(out["unit_dimension"],"FREQUENCY")

    def test_age_months(self):
        out=c.parse_axis_label("Age (months)")
        self.assertEqual(out["semantic_role"],"AGE")
        self.assertEqual(out["canonical_unit"],"MONTH")
        self.assertEqual(out["unit_dimension"],"TIME")

    def test_height_centimeters(self):
        out=c.parse_axis_label("Height, cm")
        self.assertEqual(out["semantic_role"],"HEIGHT")
        self.assertEqual(out["canonical_unit"],"CENTIMETER")

    def test_survival_percent(self):
        out=c.parse_axis_label("Survival Probability (%)")
        self.assertEqual(out["semantic_role"],"SURVIVAL_PROBABILITY")
        self.assertEqual(out["canonical_unit"],"PERCENT")

    def test_bode_magnitude_db(self):
        out=c.parse_axis_label("Magnitude (dB)")
        self.assertEqual(out["semantic_role"],"MAGNITUDE")
        self.assertEqual(out["canonical_unit"],"DECIBEL")

    def test_phase_degrees(self):
        out=c.parse_axis_label("Phase (degrees)")
        self.assertEqual(out["semantic_role"],"PHASE")
        self.assertEqual(out["canonical_unit"],"DEGREE")

    def test_speed_compound_unit_does_not_split(self):
        units=c.extract_explicit_units("Wind Speed (m/s)")
        self.assertEqual(
            [(x["canonical_unit"],x["dimension"]) for x in units],
            [("METER_PER_SECOND","SPEED")],
        )

    def test_millisecond_does_not_split_into_meter_second(self):
        units=c.extract_explicit_units("Latency (ms)")
        self.assertEqual(
            [(x["canonical_unit"],x["dimension"]) for x in units],
            [("MILLISECOND","TIME")],
        )

    def test_numeric_tick_rejected(self):
        with self.assertRaisesRegex(c.AxisTitleUnitBindingError,"AXIS_LABEL_NUMERIC_ONLY"):
            c.parse_axis_label("100")

    def test_random_annotation_without_bounded_cue_rejected(self):
        with self.assertRaisesRegex(c.AxisTitleUnitBindingError,"AXIS_LABEL_NO_BOUNDED_SEMANTIC_CUE"):
            c.parse_axis_label("Specimen A")

    def test_conflicting_units_rejected(self):
        with self.assertRaisesRegex(c.AxisTitleUnitBindingError,"AXIS_UNIT_CONFLICT"):
            c.parse_axis_label("Time (s / min)")

    def test_conflicting_roles_rejected(self):
        with self.assertRaisesRegex(c.AxisTitleUnitBindingError,"AXIS_ROLE_CONFLICT"):
            c.parse_axis_label("Height and Weight")

    def test_same_candidate_from_two_orientations_deduplicates(self):
        out=c.select_axis_binding([
            cand("Frequency (Hz)",94,"rot90"),
            cand("Frequency (Hz)",96,"rot270"),
        ])
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["candidate_count"],1)
        self.assertEqual(out["binding"]["source"],"rot270")

    def test_competing_titles_fail_closed(self):
        out=c.select_axis_binding([
            cand("Time (s)",95,"a"),
            cand("Frequency (Hz)",95,"b"),
        ],ambiguity_margin=.5)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"AMBIGUOUS_AXIS_TITLE_UNIT_CANDIDATES")

    def test_clear_best_title_wins(self):
        out=c.select_axis_binding([
            cand("Time (s)",98,"primary"),
            cand("Hz",35,"noise"),
        ])
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["binding"]["semantic_role"],"TIME")

    def test_both_axis_binding(self):
        out=c.bind_axis_candidates(
            [cand("Time (months)")],
            [cand("Survival Probability (%)")],
        )
        self.assertTrue(out["pass"])
        self.assertEqual(out["bound_axis_count"],2)
        self.assertEqual(out["x_axis"]["binding"]["canonical_unit"],"MONTH")
        self.assertEqual(out["y_axis"]["binding"]["canonical_unit"],"PERCENT")
        self.assertFalse(out["domain_semantic_authority"])
        self.assertFalse(out["benchmark_score_authority"])

    def test_partial_axis_binding_is_explicit(self):
        out=c.bind_axis_candidates(
            [cand("Age (years)")],
            [cand("100")],
        )
        self.assertTrue(out["pass"])
        self.assertEqual(out["bound_axis_count"],1)
        self.assertEqual(out["status"],"PASS__PARTIAL_AXIS_TITLE_UNIT_BINDING")

    def test_no_axis_binding_fails_closed(self):
        out=c.bind_axis_candidates([cand("100")],[cand("200")])
        self.assertFalse(out["pass"])
        self.assertEqual(out["bound_axis_count"],0)

    def test_line_plus_unit_combined_candidate(self):
        ocr={
            "text_items":[
                {"text":"Frequency","confidence_min":91},
                {"text":"(Hz)","confidence_min":92},
                {"text":"100","confidence_min":99},
            ]
        }
        rows=c._candidate_rows(ocr,"bottom")
        combined=[r for r in rows if r["evidence_kind"]=="OCR_COMBINED_NONNUMERIC_LINES"]
        self.assertTrue(combined,rows)
        parsed=combined[0]
        self.assertEqual(parsed["semantic_role"],"FREQUENCY")
        self.assertEqual(parsed["canonical_unit"],"HERTZ")

    def test_image_binding_reuses_plot_box_and_rotated_sidebands(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"chart.png"
            Image.new("RGB",(400,300),"white").save(p)
            scene={"plot_box":[60,30,360,240]}
            calls=[]
            sizes=[]
            def fake_ocr(_image,*,source):
                calls.append(source)
                sizes.append((source,_image.size))
                if source=="BOTTOM_BAND":
                    return [cand("Age (years)",95,source)]
                if source=="LEFT_BAND_ROTATE_90":
                    return [cand("Height (cm)",95,source)]
                return [cand("Height (cm)",92,source)]
            with mock.patch.object(c,"build_scene_graph",return_value=scene), \
                 mock.patch.object(c,"_ocr_pil",side_effect=fake_ocr):
                out=c.bind_axis_titles_and_units(p)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["bound_axis_count"],2)
            self.assertEqual(out["x_axis"]["binding"]["semantic_role"],"AGE")
            self.assertEqual(out["y_axis"]["binding"]["semantic_role"],"HEIGHT")
            self.assertEqual(
                calls,
                ["BOTTOM_BAND","LEFT_BAND_ROTATE_90","LEFT_BAND_ROTATE_270"],
            )
            # Rotating the full-height left band swaps its dimensions. The
            # first rotated dimension must therefore equal the source height,
            # preventing vertical title clipping from being reintroduced.
            self.assertEqual(sizes[1][1][0],300)
            self.assertEqual(sizes[2][1][0],300)

    def test_source_declares_zero_external_cognition(self):
        self.assertEqual(c.MODEL_DEPENDENCY_COUNT,0)
        self.assertEqual(c.EXTERNAL_GENERAL_PURPOSE_MODEL_RUNTIME_DEPENDENCY_COUNT,0)
        self.assertEqual(c.DONOR_GENERAL_PURPOSE_MODEL_RUNTIME_DEPENDENCY_COUNT,0)
        self.assertEqual(c.NETWORK_DEPENDENCY_COUNT,0)
        source=Path(c.__file__).read_text(encoding="utf-8").casefold()
        for token in ("qwen","minicpm","claude","gemini","openai","anthropic","llama_cpp","vllm"):
            self.assertNotIn(token,source)


if __name__=="__main__":
    unittest.main(verbosity=2)
