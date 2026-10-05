import sys, unittest
from canonical.runtime import h100_non_synthetic_description_length_v1 as m

class H100NonSyntheticDescriptionLengthTests(unittest.TestCase):
    def test_gamma_length(self):
        self.assertEqual(m.gamma_length_bits_for_byte_count(0),1)
        self.assertEqual(m.gamma_length_bits_for_byte_count(1),3)
        self.assertEqual(m.gamma_length_bits_for_byte_count(3),5)

    def test_self_delimiting_bits_include_payload(self):
        self.assertEqual(m.raw_program_bits_from_canonical_bytes(0),1)
        self.assertEqual(m.raw_program_bits_from_canonical_bytes(1),11)

    def test_comments_whitespace_locations_and_docstrings_do_not_change_code(self):
        a='''"""doc"""\n# hi\ndef f(x):\n    """inner"""\n    return x+1\n'''
        b='''\ndef f( x ):\n\n    # other\n    return x + 1\n'''
        self.assertEqual(m.canonical_ast_text(a),m.canonical_ast_text(b))

    def test_literal_change_changes_code(self):
        self.assertNotEqual(
            m.canonical_ast_text("def f(x): return x+1"),
            m.canonical_ast_text("def f(x): return x+2"),
        )

    @unittest.skipUnless(sys.version_info[:2]==(3,11),"frozen AST code requires Python 3.11")
    def test_full_measurement_has_four_subjects_and_six_bit_refs(self):
        out=m.run()
        self.assertEqual(len(out["subjects"]),4)
        self.assertEqual(out["persistent_learned_bytes"],0)
        for row in out["subjects"]:
            self.assertEqual(row["compiled_registry_reference_bits"],6)
            self.assertGreater(row["description_bit_reduction"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
