import unittest

from canonical.runtime.hle_native_semantic_compiler_v1 import compile_question


class HLENativeSemanticCompilerTests(unittest.TestCase):
    def test_compiles_contiguous_mcq_and_bare_letter_contract(self):
        q = """Which synthetic statement is selected?
Answer Choices:
A. Alpha statement
B. Beta statement
C. Gamma statement"""
        out = compile_question(task_id="s1", answer_type="multipleChoice", question=q)
        self.assertTrue(out["pass"])
        self.assertEqual(
            [x["id"] for x in out["typed_decision"]["alternatives"]],
            ["A", "B", "C"],
        )
        self.assertEqual(
            out["typed_decision"]["answer_contract"]["kind"],
            "BARE_OPTION_LETTER",
        )
        self.assertFalse(out["candidate_answer_authority"])

    def test_multiline_option_text_is_preserved(self):
        q = """Synthetic technical stem.
Answer Choices:
A. First line
continued detail
B. Second option"""
        out = compile_question(task_id="s2", answer_type="multipleChoice", question=q)
        self.assertTrue(out["pass"])
        self.assertIn("continued detail", out["typed_decision"]["alternatives"][0]["label"])

    def test_rejects_noncontiguous_letters(self):
        q = """Synthetic?
Answer Choices:
A. One
C. Three"""
        out = compile_question(task_id="s3", answer_type="multipleChoice", question=q)
        self.assertFalse(out["pass"])
        self.assertIn("OPTION_LETTERS_NOT_CONTIGUOUS", out["reason"])

    def test_rejects_missing_marker(self):
        q = "Synthetic? A. One B. Two"
        out = compile_question(task_id="s4", answer_type="multipleChoice", question=q)
        self.assertFalse(out["pass"])
        self.assertIn("ANSWER_CHOICES_MARKER_CARDINALITY", out["reason"])

    def test_exact_match_remains_explicitly_unresolved(self):
        out = compile_question(task_id="s5", answer_type="exactMatch", question="Synthetic exact?")
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__EXACT_MATCH_SEMANTIC_COMPILATION_NOT_IN_V1",
        )

    def test_query_focus_does_not_use_full_raw_question(self):
        q = """Which synthetic astronomy object has property delta?
Answer Choices:
A. Object alpha
B. Object beta"""
        out = compile_question(task_id="s6", answer_type="multipleChoice", question=q)
        self.assertTrue(out["pass"])
        raw = q.strip()
        for alt in out["typed_decision"]["alternatives"]:
            focus = alt["research_focus"]
            self.assertFalse(focus["full_question_verbatim_used"])
            self.assertNotEqual(focus["query"], raw)

    def test_image_flag_only_routes_upstream_semantics(self):
        q = """What does the synthetic image indicate?
Answer Choices:
A. Alpha
B. Beta"""
        out = compile_question(
            task_id="s7",
            answer_type="multipleChoice",
            question=q,
            has_nonempty_image_payload=True,
        )
        self.assertTrue(out["pass"])
        self.assertEqual(
            out["next_required_capability"],
            "VERIFIED_IMAGE_SEMANTICS_AND_OPTION_RELATION_EVIDENCE",
        )
        self.assertFalse(out["candidate_answer_authority"])

    def test_deterministic_hash(self):
        q = """Synthetic?
Answer Choices:
A. One
B. Two"""
        a = compile_question(task_id="s8", answer_type="multipleChoice", question=q)
        b = compile_question(task_id="s8", answer_type="multipleChoice", question=q)
        self.assertEqual(a["typed_decision_sha256"], b["typed_decision_sha256"])
        self.assertEqual(a["question_sha256"], b["question_sha256"])


if __name__ == "__main__":
    unittest.main()
