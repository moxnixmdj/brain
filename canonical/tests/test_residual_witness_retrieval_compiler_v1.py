#!/usr/bin/env python3
from __future__ import annotations
import unittest

from canonical.runtime import residual_witness_retrieval_compiler_v1 as r


class ResidualWitnessRetrievalCompilerTests(unittest.TestCase):
    def residual(self):
        return {
            "residual_id": "R-CODEC-UBJSON",
            "effect": "Encode structured records as UBJSON without network-dependent runtime cost",
            "required_capabilities": ["structured.binary.encode.ubjson"],
            "aliases": ["Universal Binary JSON", "UBJSON codec"],
            "language_variants": {
                "zh": ["通用二进制 JSON 编码", "UBJSON 编解码器"],
                "ar": ["ترميز UBJSON", "مُرمِّز UBJSON"],
            },
            "observables": {
                "api_symbols": ["dumpb", "loadb"],
                "file_formats": ["ubj", "ubjson"],
                "commands": ["ubjson"],
                "imports": ["ubjson"],
            },
            "constraints": {"incremental_spend_usd": 0},
        }

    def test_unicode_tokens_preserve_non_latin_scripts(self):
        tokens = r.unicode_tokens("中文 编解码器 العربية ترميز кодек")
        self.assertIn("中文", tokens)
        self.assertIn("编解码器", tokens)
        self.assertIn("العربية", tokens)
        self.assertIn("ترميز", tokens)
        self.assertIn("кодек", tokens)

    def test_query_lattice_contains_language_and_code_observables(self):
        p = r.compile_residual(self.residual())
        rows = p["query_lattice"]
        texts = [x["text"] for x in rows]
        self.assertIn("通用二进制 JSON 编码", texts)
        self.assertIn("ترميز UBJSON", texts)
        self.assertIn("dumpb", texts)
        self.assertIn("loadb", texts)
        self.assertTrue(any(x["basis"] == "BEHAVIOR_PLUS_OBSERVABLE" for x in rows))
        self.assertIn("NO_RESULT_IS_NOT_NONEXISTENCE", p["hard_rules"])
        self.assertEqual(p["model_dependency_count"], 0)
        self.assertEqual(p["incremental_spend_usd"], 0)

    def test_verified_witness_stops_immediately_even_with_unqueried_cells(self):
        p = r.compile_residual(self.residual())
        s = r.initial_state(p)
        self.assertFalse(r.terminal_status(s)["stop"])
        s = r.add_verified_witness(
            s,
            witness_id="repo@sha:contract",
            residual_id=p["residual_id"],
            source_surface="CODE_CONTENT",
            independent_receipt="receipt://independent/1",
        )
        out = r.terminal_status(s)
        self.assertTrue(out["stop"], out)
        self.assertEqual(out["status"], "VERIFIED_WITNESS_FOUND", out)
        action = r.next_action(p, s)
        self.assertEqual(action["action"], "STOP", action)

    def test_no_results_never_become_nonexistence(self):
        p = r.compile_residual(self.residual())
        s = r.initial_state(p)
        for cell in list(s["cells"]):
            s = r.update_cell(
                s,
                query_id=cell["query_id"],
                surface=cell["surface"],
                cell_state="QUERIED_NO_CANDIDATE",
                candidate_count=0,
            )
        out = r.terminal_status(s)
        self.assertEqual(out["status"], "UNKNOWN_CONTINUE_RETRIEVAL", out)
        self.assertFalse(out["nonexistence_claim_authorized"], out)
        action = r.next_action(p, s)
        self.assertEqual(action["action"], "ESCALATE", action)
        self.assertEqual(
            action["reason"],
            "NO_QUERYABLE_CELL_BUT_SCOPE_NOT_PROVEN_COMPLETE",
        )

    def test_declared_scope_closure_requires_independent_complete_marks(self):
        x = self.residual()
        x["declared_scope"] = {
            "scope_id": "FROZEN-REGISTRY-SNAPSHOT-1",
            "independently_verified_complete": True,
        }
        p = r.compile_residual(x)
        s = r.initial_state(p)
        for cell in list(s["cells"]):
            s = r.update_cell(
                s,
                query_id=cell["query_id"],
                surface=cell["surface"],
                cell_state="EXHAUSTIVELY_CLOSED",
                independently_complete=True,
            )
        out = r.terminal_status(s)
        self.assertTrue(out["stop"], out)
        self.assertEqual(out["status"], "DECLARED_SCOPE_EXHAUSTIVELY_CLOSED", out)
        self.assertTrue(out["scope_limited"], out)

    def test_candidate_only_surfaces_cannot_self_verify(self):
        p = r.compile_residual(self.residual())
        s = r.initial_state(p)
        for surface in ("SOCIAL_TECHNICAL_DISCUSSION", "REPOSITORY_METADATA"):
            with self.assertRaisesRegex(
                ValueError,
                "CANDIDATE_ONLY_SURFACE_CANNOT_VERIFY",
            ):
                r.add_verified_witness(
                    s,
                    witness_id="candidate-only",
                    residual_id=p["residual_id"],
                    source_surface=surface,
                    independent_receipt="receipt://nope",
                )

    def test_first_action_does_not_default_to_repository_metadata(self):
        p = r.compile_residual(self.residual())
        s = r.initial_state(p)
        a = r.next_action(p, s)
        self.assertNotEqual(a["surface"], "REPOSITORY_METADATA", a)
        self.assertEqual(a["action"], "QUERY", a)

    def test_scheduler_diversifies_after_one_surface_miss(self):
        p = r.compile_residual(self.residual())
        s = r.initial_state(p)
        first = r.next_action(p, s)
        s = r.update_cell(
            s,
            query_id=first["query_id"],
            surface=first["surface"],
            cell_state="QUERIED_NO_CANDIDATE",
        )
        second = r.next_action(p, s)
        self.assertNotEqual(first["surface"], second["surface"], (first, second))

    def test_scope_can_close_only_its_independently_complete_matrix(self):
        x = self.residual()
        x["declared_scope"] = {
            "scope_id": "FROZEN-CODE-SYMBOL-SNAPSHOT",
            "independently_verified_complete": True,
            "required_surfaces": ["CODE_CONTENT", "SYMBOLS"],
            "required_query_ids": ["Q000"],
        }
        p = r.compile_residual(x)
        s = r.initial_state(p)
        for surface in ("CODE_CONTENT", "SYMBOLS"):
            s = r.update_cell(
                s,
                query_id="Q000",
                surface=surface,
                cell_state="EXHAUSTIVELY_CLOSED",
                independently_complete=True,
            )
        out = r.terminal_status(s)
        self.assertEqual(out["status"], "DECLARED_SCOPE_EXHAUSTIVELY_CLOSED", out)

    def test_capture_recapture_is_never_a_completeness_proof(self):
        out = r.capture_recapture_unseen(10, 5)
        self.assertEqual(out["estimated_unseen"], 10.0)
        self.assertFalse(out["completeness_proof"])
        no_overlap = r.capture_recapture_unseen(10, 0)
        self.assertIsNone(no_overlap["estimated_unseen"])
        self.assertFalse(no_overlap["completeness_proof"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
