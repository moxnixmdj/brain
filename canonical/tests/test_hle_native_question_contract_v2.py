import unittest
from canonical.runtime.hle_native_question_contract_v2 import compile_question

class HLEQuestionContractV2Tests(unittest.TestCase):
    def test_relative_who_does_not_override_leading_city_slot(self):
        o=compile_question(task_id="a",question="Which Australian city is named after the Scotsman who was Governor?")
        self.assertEqual(o["question_kind"],"LOCATION")
    def test_trailing_region_is_location(self):
        o=compile_question(task_id="b",question="A historical ruler came from which French region?")
        self.assertEqual(o["question_kind"],"LOCATION")
    def test_relation_slot(self):
        o=compile_question(task_id="c",question="What relation was Person A to Person B?")
        self.assertEqual(o["question_kind"],"RELATION_TERM")
    def test_composer_slot(self):
        o=compile_question(task_id="d",question="Which composer wrote the fictional operas 'Alpha' and 'Beta'?")
        self.assertEqual(o["question_kind"],"PERSON")
    def test_views_are_multiple_and_never_full_question(self):
        q="Which composer wrote the fictional operas 'Alpha' and 'Beta'?"
        o=compile_question(task_id="e",question=q)
        self.assertGreaterEqual(o["research_view_count"],2)
        self.assertTrue(all(not x["full_question_verbatim_used"] for x in o["research_views"]))
        self.assertTrue(all(x["query"].casefold()!=q.casefold() for x in o["research_views"]))
    def test_no_external_cognition_or_authority(self):
        o=compile_question(task_id="f",question="Who discovered the fictional Zephyr particle?")
        self.assertEqual(o["external_model_calls"],0)
        self.assertEqual(o["model_dependency_count"],0)
        self.assertFalse(o["gold_accessed"])
        self.assertFalse(o["candidate_answer_authority"])
        self.assertFalse(o["terminal_authority"])

if __name__=="__main__":unittest.main(verbosity=2)
