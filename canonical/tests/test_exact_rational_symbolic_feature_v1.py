import unittest

from canonical.runtime.exact_rational_symbolic_feature_v1 import compile_basis


def var(name):
    return {"op": "var", "name": name}


def unary(op, arg):
    return {"op": op, "arg": arg}


def binary(op, left, right):
    return {"op": op, "left": left, "right": right}


def compile_one(tree, rows, queries=None, intercept=True):
    return compile_basis(
        {
            "trees": [tree],
            "rows": rows,
            "queries": queries or [],
            "include_intercept": intercept,
        }
    )


class ExactRationalSymbolicFeatureTests(unittest.TestCase):
    def test_variable_and_intercept_compile_exactly(self):
        out = compile_one(var("x"), [{"x": "3/2"}])
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["feature_rows"], [["1", "3/2"]])

    def test_unary_algebraic_subgrammar_is_exact(self):
        tree = unary("square", unary("abs", unary("neg", var("x"))))
        out = compile_one(tree, [{"x": "-3/2"}], intercept=False)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["feature_rows"], [["9/4"]])

    def test_saturation_is_exact_rational(self):
        out = compile_one(unary("sat", var("x")), [{"x": "-2"}], intercept=False)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["feature_rows"], [["-2/3"]])

    def test_binary_add_sub_mul_and_division_are_exact(self):
        tree = binary(
            "mul",
            binary("add", var("x"), var("y")),
            binary("safe_div", binary("sub", var("x"), var("y")), var("z")),
        )
        out = compile_one(
            tree,
            [{"x": "3", "y": "1", "z": "2"}],
            intercept=False,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["feature_rows"], [["4"]])

    def test_stable_div_is_exact_rational(self):
        tree = binary("stable_div", var("x"), var("y"))
        out = compile_one(tree, [{"x": "3", "y": "-2"}], intercept=False)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["feature_rows"], [["1"]])

    def test_safe_div_zero_fails_closed(self):
        tree = binary("safe_div", var("x"), var("y"))
        out = compile_one(tree, [{"x": "1", "y": "0"}], intercept=False)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EXACT_FEATURE_EVALUATION_FAILED")
        self.assertIn("SAFE_DIV_ZERO", out["detail"])

    def test_reciprocal_zero_fails_closed(self):
        out = compile_one(unary("reciprocal", var("x")), [{"x": "0"}], intercept=False)
        self.assertFalse(out["pass"])
        self.assertIn("RECIPROCAL_ZERO", out["detail"])

    def test_fractional_power_operator_is_explicitly_unsupported(self):
        out = compile_one(
            {"op": "pow_abs_1_3", "arg": var("x")},
            [{"x": "8"}],
            intercept=False,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "TREE_BINDING_FAILED")
        self.assertIn("UNSUPPORTED_OR_INVALID_OPERATOR:pow_abs_1_3", out["detail"])

    def test_binary_float_input_is_rejected(self):
        out = compile_one(var("x"), [{"x": 0.5}], intercept=False)
        self.assertFalse(out["pass"])
        self.assertIn("EXACT_RATIONAL_STRING_OR_INT_REQUIRED", out["detail"])

    def test_missing_variable_fails_closed(self):
        out = compile_one(var("x"), [{"y": "1"}], intercept=False)
        self.assertFalse(out["pass"])
        self.assertIn("MISSING_VARIABLES:x", out["detail"])

    def test_query_features_and_zero_credit(self):
        out = compile_basis(
            {
                "trees": [var("x"), unary("square", var("x"))],
                "rows": [{"x": "2"}],
                "queries": [{"query_id": "q", "point": {"x": "3"}}],
                "include_intercept": True,
            }
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["feature_rows"], [["1", "2", "4"]])
        self.assertEqual(out["query_features"], [{"query_id": "q", "features": ["1", "3", "9"]}])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
