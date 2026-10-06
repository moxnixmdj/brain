import unittest

from canonical.runtime.relational_refinement_compiler_v1 import (
    SCHEMA,
    compile_relational_refinement,
)

SHA = "a" * 40


def receipt(kind=None):
    out = {"path": "canonical/proof.json", "git_blob_sha": SHA}
    if kind is not None:
        out["proof_kind"] = kind
    return out


def base_row():
    return {
        "id": "R1",
        "precondition_spec": "P",
        "target_transition_class": "T",
        "brain_macrostep_contract": "B",
        "postcondition_spec": "Q",
        "evaluator_binding": {
            "mode": "EXPLICIT",
            "evaluator_receipt": receipt("EXPLICIT_EVALUATOR"),
        },
        "relation_soundness_receipt": receipt("RELATION_SOUNDNESS"),
        "local_refinement_receipt": receipt("FORMAL_REFINEMENT"),
        "scope_authority_receipt": receipt("SCOPE"),
        "state_carry_receipt": receipt("STATE"),
        "ownership_receipt": receipt("OWNERSHIP"),
    }


def base_doc():
    return {
        "schema": SCHEMA,
        "target_claim": "C_UNIVERSAL_OBSERVABLE_BEHAVIOR_DOMINANCE_BINDING_V1",
        "relation_id": "R_EVAL_AWARE_V1",
        "trace_scope_receipt": receipt("TRACE_SCOPE"),
        "initialization_receipt": receipt("INIT"),
        "constructor_preservation_receipt": receipt("CONSTRUCTOR"),
        "terminal_preservation_receipt": receipt("TERMINAL"),
        "acceptance_order_soundness_receipt": receipt("ORDER"),
        "rows": [base_row()],
    }


class RelationalRefinementCompilerTests(unittest.TestCase):
    def setUp(self):
        self._blob_patch = patch(
            "canonical.runtime.relational_refinement_compiler_v1._git_blob_sha",
            return_value=SHA,
        )
        self._blob_patch.start()

    def tearDown(self):
        self._blob_patch.stop()

    def test_complete_row_and_globals_ready(self):
        out = compile_relational_refinement(base_doc())
        self.assertTrue(out["whole_trace_candidate_ready"])
        self.assertEqual(out["closed_row_count"], 1)
        self.assertEqual(out["open_row_count"], 0)
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_missing_local_receipt_remains_open(self):
        doc = base_doc()
        doc["rows"][0]["local_refinement_receipt"] = None
        out = compile_relational_refinement(doc)
        self.assertFalse(out["whole_trace_candidate_ready"])
        self.assertEqual(out["open_rows"], ["R1"])
        self.assertIn("local_refinement_receipt", out["rows"][0]["missing_receipts"])

    def test_benchmark_score_cannot_substitute_for_local_refinement(self):
        doc = base_doc()
        doc["rows"][0]["local_refinement_receipt"] = receipt("BENCHMARK_SCORE")
        out = compile_relational_refinement(doc)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(
            any("LOCAL_REFINEMENT_FORBIDDEN_PROOF_KIND:BENCHMARK_SCORE" in e for e in out["errors"])
        )

    def test_unrestricted_hidden_requires_observational_equivalence(self):
        doc = base_doc()
        doc["rows"][0]["evaluator_binding"] = {
            "mode": "UNRESTRICTED_HIDDEN",
            "equivalence_receipt": receipt("NOT_EQUIVALENCE"),
        }
        out = compile_relational_refinement(doc)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("R1:equivalence_receipt:PROOF_KIND_INVALID", out["errors"])

    def test_restricted_hidden_requires_order_and_utility_class(self):
        doc = base_doc()
        doc["rows"][0]["evaluator_binding"] = {
            "mode": "RESTRICTED_HIDDEN",
            "utility_class_receipt": receipt("UTILITY_CLASS"),
        }
        out = compile_relational_refinement(doc)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn(
            "R1:material_order_receipt:MISSING_OR_INVALID_CONTENT_ADDRESS",
            out["errors"],
        )

    def test_missing_global_receipt_blocks_whole_trace_not_row(self):
        doc = base_doc()
        doc["constructor_preservation_receipt"] = None
        out = compile_relational_refinement(doc)
        self.assertFalse(out["whole_trace_candidate_ready"])
        self.assertEqual(out["closed_row_count"], 1)
        self.assertEqual(out["global_missing_receipts"], ["constructor_preservation_receipt"])

    def test_duplicate_row_id_fails_closed(self):
        doc = base_doc()
        doc["rows"].append(dict(base_row()))
        out = compile_relational_refinement(doc)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("R1:DUPLICATE_ID", out["errors"])

    def test_invalid_content_address_does_not_close(self):
        doc = base_doc()
        doc["rows"][0]["ownership_receipt"] = {
            "path": "canonical/x.json",
            "git_blob_sha": "bad",
        }
        out = compile_relational_refinement(doc)
        self.assertFalse(out["whole_trace_candidate_ready"])
        self.assertIn("ownership_receipt", out["rows"][0]["missing_receipts"])

    def test_existing_shape_with_mismatched_actual_blob_fails_closed(self):
        doc = base_doc()
        with patch(
            "canonical.runtime.relational_refinement_compiler_v1._git_blob_sha",
            return_value="b" * 40,
        ):
            out = compile_relational_refinement(doc)
        self.assertFalse(out["whole_trace_candidate_ready"])
        self.assertIn(
            "trace_scope_receipt",
            out["global_missing_receipts"],
        )

    def test_empty_rows_fail_closed(self):
        doc = base_doc()
        doc["rows"] = []
        out = compile_relational_refinement(doc)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("ROWS_INVALID_OR_EMPTY", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
