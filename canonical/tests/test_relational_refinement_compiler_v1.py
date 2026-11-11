import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import canonical.runtime.relational_refinement_compiler_v1 as rr
from canonical.runtime.relational_refinement_compiler_v1 import (
    SCHEMA,
    compile_relational_refinement,
)

SHA = "a" * 40


def receipt(kind=None, path="canonical/proof.json"):
    out = {"path": path, "git_blob_sha": SHA}
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


def row_binding(row):
    return {
        "schema": "PROJECT_BRAIN_RELATIONAL_REFINEMENT_CONTRACT_BINDING_V1",
        "row_id": row["id"],
        "relation_id": "R_EVAL_AWARE_V1",
        "precondition_spec": row["precondition_spec"],
        "target_transition_class": row["target_transition_class"],
        "brain_macrostep_contract": row["brain_macrostep_contract"],
        "postcondition_spec": row["postcondition_spec"],
        "evaluator_binding": row["evaluator_binding"],
        "evidence_receipts": {
            field: row[field]
            for field in (
                "relation_soundness_receipt",
                "local_refinement_receipt",
                "scope_authority_receipt",
                "state_carry_receipt",
                "ownership_receipt",
            )
        },
    }


def global_binding(doc):
    return {
        "schema": "PROJECT_BRAIN_RELATIONAL_REFINEMENT_GLOBAL_BINDING_V1",
        "target_claim": doc["target_claim"],
        "relation_id": doc["relation_id"],
        "global_receipts": {
            field: doc[field]
            for field in (
                "trace_scope_receipt",
                "initialization_receipt",
                "constructor_preservation_receipt",
                "terminal_preservation_receipt",
                "acceptance_order_soundness_receipt",
            )
        },
    }


def base_doc():
    row = base_row()
    row["contract_binding_receipt"] = receipt(
        "ROW_BINDING", "canonical/row_binding.json"
    )
    doc = {
        "schema": SCHEMA,
        "target_claim": "C_UNIVERSAL_OBSERVABLE_BEHAVIOR_DOMINANCE_BINDING_V1",
        "relation_id": "R_EVAL_AWARE_V1",
        "trace_scope_receipt": receipt("TRACE_SCOPE"),
        "initialization_receipt": receipt("INIT"),
        "constructor_preservation_receipt": receipt("CONSTRUCTOR"),
        "terminal_preservation_receipt": receipt("TERMINAL"),
        "acceptance_order_soundness_receipt": receipt("ORDER"),
        "global_contract_binding_receipt": receipt(
            "GLOBAL_BINDING", "canonical/global_binding.json"
        ),
        "rows": [row],
    }
    return doc


class RelationalRefinementCompilerTests(unittest.TestCase):
    def setUp(self):
        self._blob_patch = patch(
            "canonical.runtime.relational_refinement_compiler_v1._git_blob_sha",
            return_value=SHA,
        )
        self._blob_patch.start()

        def load_binding(value):
            path = value.get("path") if isinstance(value, dict) else None
            if path == "canonical/row_binding.json":
                return row_binding(self._current_doc["rows"][0])
            if path == "canonical/global_binding.json":
                return global_binding(self._current_doc)
            return None

        self._current_doc = base_doc()
        self._json_patch = patch(
            "canonical.runtime.relational_refinement_compiler_v1._load_json_receipt",
            side_effect=load_binding,
        )
        self._json_patch.start()

    def tearDown(self):
        self._json_patch.stop()
        self._blob_patch.stop()

    def fresh_doc(self):
        self._current_doc = base_doc()
        return self._current_doc

    def test_complete_row_and_globals_ready(self):
        out = compile_relational_refinement(self.fresh_doc())
        self.assertTrue(out["whole_trace_candidate_ready"])
        self.assertEqual(out["closed_row_count"], 1)
        self.assertEqual(out["open_row_count"], 0)
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_missing_local_receipt_remains_open(self):
        doc = self.fresh_doc()
        doc["rows"][0]["local_refinement_receipt"] = None
        out = compile_relational_refinement(doc)
        self.assertFalse(out["whole_trace_candidate_ready"])
        self.assertEqual(out["open_rows"], ["R1"])
        self.assertIn("local_refinement_receipt", out["rows"][0]["missing_receipts"])

    def test_benchmark_score_cannot_substitute_for_local_refinement(self):
        doc = self.fresh_doc()
        doc["rows"][0]["local_refinement_receipt"] = receipt("BENCHMARK_SCORE")
        out = compile_relational_refinement(doc)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(
            any("LOCAL_REFINEMENT_FORBIDDEN_PROOF_KIND:BENCHMARK_SCORE" in e for e in out["errors"])
        )

    def test_unrestricted_hidden_requires_observational_equivalence(self):
        doc = self.fresh_doc()
        doc["rows"][0]["evaluator_binding"] = {
            "mode": "UNRESTRICTED_HIDDEN",
            "equivalence_receipt": receipt("NOT_EQUIVALENCE"),
        }
        out = compile_relational_refinement(doc)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("R1:equivalence_receipt:PROOF_KIND_INVALID", out["errors"])

    def test_restricted_hidden_requires_order_and_utility_class(self):
        doc = self.fresh_doc()
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
        doc = self.fresh_doc()
        doc["constructor_preservation_receipt"] = None
        out = compile_relational_refinement(doc)
        self.assertFalse(out["whole_trace_candidate_ready"])
        self.assertEqual(out["closed_row_count"], 1)
        self.assertEqual(out["global_missing_receipts"], ["constructor_preservation_receipt"])

    def test_duplicate_row_id_fails_closed(self):
        doc = self.fresh_doc()
        doc["rows"].append(dict(base_row()))
        out = compile_relational_refinement(doc)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("R1:DUPLICATE_ID", out["errors"])

    def test_invalid_content_address_does_not_close(self):
        doc = self.fresh_doc()
        doc["rows"][0]["ownership_receipt"] = {
            "path": "canonical/x.json",
            "git_blob_sha": "bad",
        }
        out = compile_relational_refinement(doc)
        self.assertFalse(out["whole_trace_candidate_ready"])
        self.assertIn("ownership_receipt", out["rows"][0]["missing_receipts"])

    def test_existing_shape_with_mismatched_actual_blob_fails_closed(self):
        doc = self.fresh_doc()
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

    def test_row_contract_binding_mismatch_fails_closed(self):
        doc = self.fresh_doc()

        def bad_load(value):
            path = value.get("path") if isinstance(value, dict) else None
            if path == "canonical/row_binding.json":
                obj = row_binding(doc["rows"][0])
                obj["postcondition_spec"] = "WRONG"
                return obj
            if path == "canonical/global_binding.json":
                return global_binding(doc)
            return None

        with patch(
            "canonical.runtime.relational_refinement_compiler_v1._load_json_receipt",
            side_effect=bad_load,
        ):
            out = compile_relational_refinement(doc)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn(
            "R1:contract_binding_receipt:MISMATCH:postcondition_spec",
            out["errors"],
        )

    def test_global_contract_binding_mismatch_fails_closed(self):
        doc = self.fresh_doc()

        def bad_load(value):
            path = value.get("path") if isinstance(value, dict) else None
            if path == "canonical/row_binding.json":
                return row_binding(doc["rows"][0])
            if path == "canonical/global_binding.json":
                obj = global_binding(doc)
                obj["relation_id"] = "WRONG"
                return obj
            return None

        with patch(
            "canonical.runtime.relational_refinement_compiler_v1._load_json_receipt",
            side_effect=bad_load,
        ):
            out = compile_relational_refinement(doc)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn(
            "GLOBAL_CONTRACT_BINDING_RELATION_ID_MISMATCH",
            out["errors"],
        )

    def test_empty_rows_fail_closed(self):
        doc = self.fresh_doc()
        doc["rows"] = []
        out = compile_relational_refinement(doc)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("ROWS_INVALID_OR_EMPTY", out["errors"])


class GitBlobHashTests(unittest.TestCase):
    def test_git_blob_sha_uses_nul_separator_and_actual_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "canonical" / "x.txt"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"abc")
            expected = hashlib.sha1(b"blob 3\0abc").hexdigest()
            with patch.object(rr, "ROOT", root):
                self.assertEqual(rr._git_blob_sha("canonical/x.txt"), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
