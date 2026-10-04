from __future__ import annotations
import json
import unittest
from pathlib import Path
from canonical.runtime.zero_learned_extractive_summary_v1 import summarize

PRE=Path(__file__).resolve().parents[1]/"governance"/"LIVEBENCH_ZERO_LEARNED_EXTRACTIVE_SUMMARY_PREEXPOSURE_V1.json"

class ZeroLearnedExtractiveSummaryTests(unittest.TestCase):
    def test_frozen_tasks_are_compressed_and_extractively_faithful(self):
        doc=json.loads(PRE.read_text())
        self.assertEqual(len(doc["tasks"]),4)
        for task in doc["tasks"]:
            out=summarize(task["text"],max_sentences=task["max_sentences"])
            self.assertEqual(out["status"],"SUMMARY_READY",(task["task_id"],out))
            self.assertLess(out["summary_sentence_count"],out["source_sentence_count"])
            self.assertLessEqual(out["summary_sentence_count"],task["max_sentences"])
            self.assertTrue(out["extractive_faithfulness_verified"])
            for sentence in out["summary_sentences"]:
                self.assertIn(sentence,task["text"])
            self.assertEqual(out["persistent_learned_bytes"],0)
            self.assertEqual(out["external_model_calls"],0)

    def test_deterministic(self):
        text="Alpha systems store energy. Energy storage helps balance demand. Decorative paint changes appearance. Stored energy can be released later."
        a=summarize(text,max_sentences=2)
        b=summarize(text,max_sentences=2)
        self.assertEqual(a["summary"],b["summary"])
        self.assertEqual(a["selected_indices"],b["selected_indices"])

    def test_abstains_when_not_compressible(self):
        out=summarize("One sentence only.",max_sentences=2)
        self.assertEqual(out["status"],"ABSTAIN_NOT_COMPRESSIBLE")
        self.assertEqual(out["summary"],"")

    def test_rejects_invalid_limit(self):
        with self.assertRaisesRegex(ValueError,"MAX_SENTENCES_INVALID"):
            summarize("One. Two.",max_sentences=0)

    def test_no_sentence_invention_under_punctuation(self):
        text="First fact: alpha is measured. Second fact? Beta is observed! Third fact remains."
        out=summarize(text,max_sentences=2)
        for sentence in out["summary_sentences"]:
            self.assertIn(sentence,text)

if __name__=="__main__":
    unittest.main(verbosity=2)
