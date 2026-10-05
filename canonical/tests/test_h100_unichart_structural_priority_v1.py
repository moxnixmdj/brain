import unittest
from canonical.runtime.h100_unichart_structural_priority_v1 import structural_class

class StructuralPriorityTests(unittest.TestCase):
    def test_tied_embedding_forced(self):
        self.assertEqual(structural_class([
            "decoder.lm_head.weight",
            "decoder.model.decoder.embed_tokens.weight",
        ],{"decoder.lm_head.weight":[57531,1024],"decoder.model.decoder.embed_tokens.weight":[57531,1024]}),
        "TOKEN_EMBEDDING_LM_HEAD")

    def test_norm_forced(self):
        self.assertEqual(structural_class(
            ["decoder.model.decoder.layers.0.final_layer_norm.weight"],
            {"decoder.model.decoder.layers.0.final_layer_norm.weight":[1024]},
        ),"NORM")

    def test_bias_forced(self):
        self.assertEqual(structural_class(
            ["decoder.model.decoder.layers.0.fc2.bias"],
            {"decoder.model.decoder.layers.0.fc2.bias":[1024]},
        ),"BIAS")

    def test_relative_position_bias_forced(self):
        self.assertEqual(structural_class(
            ["encoder.encoder.layers.0.blocks.0.attention.self.relative_position_bias_table"],
            {"encoder.encoder.layers.0.blocks.0.attention.self.relative_position_bias_table":[361,4]},
        ),"RELATIVE_POSITION_BIAS")

    def test_regular_matrix_not_forced(self):
        self.assertIsNone(structural_class(
            ["decoder.model.decoder.layers.0.fc1.weight"],
            {"decoder.model.decoder.layers.0.fc1.weight":[4096,1024]},
        ))

if __name__=="__main__":
    unittest.main(verbosity=2)
