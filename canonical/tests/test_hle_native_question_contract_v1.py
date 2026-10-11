from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.hle_native_question_contract_v1 import compile_question

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / "governance" / "HLE_NATIVE_QUESTION_CONTRACT_PREEXPOSURE_20261011_V1.json"


class HLENativeQuestionContractV1Tests(unittest.TestCase):
    def test_frozen_synthetic_population(self):
        doc = json.loads(PRE.read_text(encoding="utf-8"))
        self.assertEqual(len(doc["tasks"]), 20)
        for task in doc["tasks"]:
            out = compile_question(task_id=task["id"], question=task["q"])
            self.assertTrue(out["pass"], (task["id"], out))
            self.assertEqual(out["question_kind"], task["kind"], (task["id"], out))
            self.assertEqual(out["polarity"], task["polarity"], (task["id"], out))
            self.assertFalse(out["gold_accessed"])
            self.assertFalse(out["answer_type_metadata_consumed"])
            self.assertEqual(out["external_model_calls"], 0)
            self.assertEqual(out["model_dependency_count"], 0)
            self.assertFalse(out["candidate_answer_authority"])
            self.assertFalse(out["terminal_authority"])
            self.assertEqual(out["terminal_credit_delta"], 0)
            self.assertFalse(out["research_focus"]["full_question_verbatim_used"])

    def test_unknown_surface_fails_closed(self):
        out = compile_question(task_id="x", question="Contemplate synthetic Alder.")
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED__QUESTION_SURFACE_UNRESOLVED")
        self.assertIsNone(out["question_kind"])

    def test_no_answer_type_argument_exists(self):
        with self.assertRaises(TypeError):
            compile_question(
                task_id="x",
                question="Who discovered synthetic Alder?",
                answer_type="exactMatch",
            )

    def test_visible_mcq_syntax_not_metadata_driven(self):
        q = "Synthetic stem?\nAnswer Choices:\nA. One\nB. Two\nC. Three"
        out = compile_question(task_id="m", question=q)
        self.assertTrue(out["pass"])
        self.assertEqual(out["question_kind"], "BARE_OPTION_LETTER")
        self.assertEqual(out["answer_contract"]["allowed_values"], ["A", "B", "C"])
        self.assertFalse(out["answer_type_metadata_consumed"])

    def test_negative_polarity(self):
        out = compile_question(
            task_id="neg",
            question="Which synthetic compound is NOT produced by the fictional pathway?",
        )
        self.assertTrue(out["pass"])
        self.assertEqual(out["polarity"], "NEGATIVE")

    def test_image_flag_preserves_upstream_requirement(self):
        out = compile_question(
            task_id="img",
            question="Where is the fictional Ardent observatory located?",
            has_nonempty_image_payload=True,
        )
        self.assertTrue(out["pass"])
        self.assertEqual(out["image_requirement"], "IMAGE_SEMANTICS_REQUIRED_UPSTREAM")

    def test_research_focus_is_bounded_and_not_verbatim(self):
        q = "Who discovered the synthetic Zephyr particle in the fictional Alder experiment?"
        out = compile_question(task_id="q", question=q)
        focus = out["research_focus"]
        self.assertLessEqual(focus["token_count"], 36)
        self.assertLessEqual(len(focus["query"]), 700)
        self.assertNotEqual(" ".join(focus["query"].split()).casefold(), " ".join(q.split()).casefold())


if __name__ == "__main__":
    unittest.main(verbosity=2)
