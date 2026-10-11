import unittest
from canonical.runtime.hle_question_shape_router_v1 import route_question

class HLEQuestionShapeRouterTests(unittest.TestCase):
    def test_symbolic(self):
        out=route_question(task_id="a",answer_type="exactMatch",
            question=r"Let x satisfy \(x^2=16\). What is the positive value of x?")
        self.assertIn("SYMBOLIC_NUMERIC_REASONING",out["candidate_lanes"])
        self.assertFalse(out["answer_authority"])

    def test_numeric_prose(self):
        out=route_question(task_id="b",answer_type="exactMatch",
            question="A synthetic box has 7 items and gains 5. How many items are there?")
        self.assertIn("SYMBOLIC_NUMERIC_REASONING",out["candidate_lanes"])

    def test_entity(self):
        out=route_question(task_id="c",answer_type="exactMatch",
            question="Synthetic context. What is the name of the fictional process?")
        self.assertIn("ENTITY_TERM_OR_RELATION_LOOKUP",out["candidate_lanes"])

    def test_temporal(self):
        out=route_question(task_id="d",answer_type="exactMatch",
            question="Synthetic event description. In what year did the fictional event occur?")
        self.assertIn("TEMPORAL_LOOKUP_OR_DERIVATION",out["candidate_lanes"])

    def test_boolean(self):
        out=route_question(task_id="e",answer_type="exactMatch",
            question="Synthetic proposition. Is it true that alpha implies beta?")
        self.assertIn("BOOLEAN_PROPOSITION",out["candidate_lanes"])

    def test_code(self):
        out=route_question(task_id="f",answer_type="exactMatch",
            question="Consider this code:\n```python\nx=1\n```\nWhat is printed?")
        self.assertIn("PROGRAMMATIC_CODE_REASONING",out["candidate_lanes"])

    def test_mcq_lane(self):
        out=route_question(task_id="g",answer_type="multipleChoice",
            question="Synthetic?\nAnswer Choices:\nA. One\nB. Two")
        self.assertIn("MULTIPLE_CHOICE_TYPED_DECISION",out["candidate_lanes"])

    def test_image_lane(self):
        out=route_question(task_id="h",answer_type="exactMatch",
            question="What object is shown?",has_nonempty_image_payload=True)
        self.assertEqual(out["primary_lane"],"IMAGE_SEMANTICS_REQUIRED")

    def test_open_fallback(self):
        out=route_question(task_id="i",answer_type="exactMatch",
            question="Discuss synthetic alpha under synthetic beta.")
        self.assertEqual(out["candidate_lanes"],["OPEN_SEMANTIC_REASONING"])

    def test_deterministic_hashes(self):
        q="What is the name of synthetic alpha?"
        a=route_question(task_id="j",answer_type="exactMatch",question=q)
        b=route_question(task_id="j",answer_type="exactMatch",question=q)
        self.assertEqual(a["question_sha256"],b["question_sha256"])
        self.assertEqual(a["tail_clause_sha256"],b["tail_clause_sha256"])

if __name__=="__main__":
    unittest.main()
