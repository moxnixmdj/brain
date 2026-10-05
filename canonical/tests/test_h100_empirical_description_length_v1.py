import json
import unittest
from canonical.runtime import h100_empirical_description_length_v1 as m
from canonical.runtime import h100_zero_learned_parametric_unary_v1 as param

class H100EmpiricalDescriptionLengthTests(unittest.TestCase):
    def test_frozen_bit_formulas(self):
        self.assertEqual(m.raw_program_bits("linear_trend_sinusoid",32),19*5+6*32)
        self.assertEqual(m.compiled_reference_bits("linear_trend_sinusoid",32),1+5+5*32)
        self.assertEqual(m.raw_program_bits("exp_abs",32),7*5+2*32)
        self.assertEqual(m.compiled_reference_bits("exp_abs",32),1+5+2*32)
        self.assertEqual(m.raw_program_bits("threshold_step",32),7*5+3*32)
        self.assertEqual(m.compiled_reference_bits("threshold_step",32),1+5+3*32)

    def test_structural_savings_are_positive_for_every_precision_rung(self):
        for width in m.WIDTHS:
            for family in m.PARAMS:
                self.assertGreater(m.raw_program_bits(family,width),m.compiled_reference_bits(family,width))

    def test_float_quantization_is_deterministic(self):
        for width in m.WIDTHS:
            self.assertEqual(m._quantize(1.2345,width),m._quantize(1.2345,width))

    def test_quantized_candidate_preserves_family_and_interface(self):
        c={"family":"exp_abs","scale":1.2,"rate":0.31,"input_name":"x"}
        q=m.quantized_candidate(c,32)
        self.assertEqual(q["family"],"exp_abs")
        self.assertEqual(q["input_name"],"x")
        self.assertEqual(set(q),{"family","input_name","scale","rate"})

    def test_measurement_precommit_is_frozen(self):
        d=json.loads(m.PRE.read_text())
        self.assertEqual(d["canonical_code"]["raw_program_dsl"]["opcode_width_bits"],5)
        self.assertEqual(d["canonical_code"]["compiled_reference"]["library_selector_bits"],5)
        self.assertEqual(d["canonical_code"]["float_precision_ladder_bits"],[16,32,64])
        self.assertEqual(d["timing"]["repetitions"],7)

    def test_full_measurement_has_three_families_and_zero_learned_bytes(self):
        out=m.run()
        self.assertEqual(out["family_count"],3)
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["h100_terminal_credit_delta"],0)
        for row in out["families"]:
            self.assertLessEqual(row["holdout_nrmse"],1e-7)
            self.assertGreater(row["description_bit_reduction"],0)
            self.assertIn(row["selected_float_precision_bits"],(16,32,64))
            self.assertGreater(row["verification_median_seconds"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
