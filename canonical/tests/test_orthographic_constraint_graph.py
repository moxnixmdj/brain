import unittest

from canonical.runtime.orthographic_constraint_graph import compile_constraint_graph


class OrthographicConstraintGraphTests(unittest.TestCase):
    def test_compile_basic_triplet(self):
        out = compile_constraint_graph([[1]], [[1]], [[1]])
        self.assertEqual(out["status"], "COMPILED")
        self.assertEqual((out["x_cells"], out["y_cells"], out["z_cells"]), (1, 1, 1))
        self.assertEqual(len(out["silhouette_constraints"]), 3)

    def test_axis_scale_from_explicit_dimension(self):
        out = compile_constraint_graph(
            [[1, 1]],
            [[1, 1]],
            [[1]],
            dimensions=[{"axis": "x", "value": 20, "units": "mm"}],
        )
        self.assertEqual(out["status"], "COMPILED")
        x = next(x for x in out["axis_scales"] if x["axis"] == "x")
        self.assertEqual(x["cell_size"], 10.0)

    def test_conflicting_dimension_fails_closed(self):
        out = compile_constraint_graph(
            [[1]], [[1]], [[1]],
            dimensions=[
                {"axis": "x", "value": 10, "units": "mm"},
                {"axis": "x", "value": 11, "units": "mm"},
            ],
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any(x.startswith("DIMENSION_CONFLICT:x") for x in out["errors"]))

    def test_feature_schema_is_typed(self):
        out = compile_constraint_graph(
            [[1]], [[1]], [[1]],
            features=[{"id": "H1", "kind": "hole", "diameter": 3.2, "through": True}],
        )
        self.assertEqual(out["status"], "COMPILED")
        self.assertEqual(out["explicit_features"][0]["kind"], "hole")

    def test_unknown_feature_kind_fails_closed(self):
        out = compile_constraint_graph(
            [[1]], [[1]], [[1]],
            features=[{"id": "F1", "kind": "mystery_curve"}],
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any(x.startswith("FEATURE_KIND_UNSUPPORTED:F1") for x in out["errors"]))


if __name__ == "__main__":
    unittest.main()
