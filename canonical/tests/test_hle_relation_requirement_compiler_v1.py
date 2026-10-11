import unittest
from canonical.runtime.hle_relation_requirement_compiler_v1 import compile_requirements

class RelationRequirementCompilerV1Tests(unittest.TestCase):
    def reqs(self,q):
        out=compile_requirements(task_id="synthetic",question=q)
        self.assertFalse(out["gold_accessed"])
        self.assertFalse(out["answer_value_accessed"])
        self.assertEqual(out["external_model_calls"],0)
        self.assertEqual(out["model_dependency_count"],0)
        self.assertFalse(any(x["full_question_verbatim_used"] for x in out["requirements"]))
        return out["requirements"]

    def test_pairwise_relation_preserves_both_entities(self):
        rows=self.reqs("What relation was Emperor Alpha to Emperor Beta?")
        q=" ".join(x["query"] for x in rows if x["method"]=="PAIRWISE_RELATION")
        self.assertIn("Emperor Alpha",q)
        self.assertIn("Emperor Beta",q)
        self.assertIn("kinship",q)

    def test_university_relation_preserves_full_person(self):
        rows=self.reqs("Business magnate Ada Example dropped out of which university?")
        q=" ".join(x["query"] for x in rows if x["method"]=="SUBJECT_INSTITUTION_RELATION")
        self.assertIn("Ada Example",q)
        self.assertIn("dropped out",q)
        self.assertIn("university",q)

    def test_ordinal_role_is_preserved(self):
        rows=self.reqs("Which president was the first to be assassinated in Exampleland?")
        q=" ".join(x["query"] for x in rows if x["method"]=="ORDINAL_PERSON_IDENTITY")
        self.assertIn("first president",q.casefold())
        self.assertIn("assassinated",q.casefold())

    def test_definition_relation_preserves_definition_tokens(self):
        rows=self.reqs("What is the term for a triangle with two equal sides?")
        q=" ".join(x["query"] for x in rows if x["method"]=="DEFINITION_RELATION")
        self.assertIn("triangle",q.casefold())
        self.assertIn("equal",q.casefold())
        self.assertIn("sides",q.casefold())
        self.assertIn("definition",q.casefold())

    def test_named_after_relation(self):
        rows=self.reqs("Which city was named after the explorer Rowan Example?")
        q=" ".join(x["query"] for x in rows if x["method"]=="NAMED_AFTER_RELATION")
        self.assertIn("Rowan Example",q)
        self.assertIn("named after",q)

    def test_descriptive_person(self):
        rows=self.reqs("Which artist famously produced posters for the Red Windmill?")
        q=" ".join(x["query"] for x in rows if x["method"]=="DESCRIPTIVE_PERSON_IDENTITY")
        self.assertIn("artist",q.casefold())
        self.assertIn("posters",q.casefold())

    def test_alias_entity(self):
        rows=self.reqs("Which dynasty, known as the Iron House, was based in Exampletown?")
        q=" ".join(x["query"] for x in rows if x["method"]=="ALIAS_ENTITY_RELATION")
        self.assertIn("Iron House",q)
        self.assertIn("dynasty",q.casefold())
        self.assertIn("known as",q.casefold())

    def test_bounded_and_deduplicated(self):
        rows=self.reqs("What relation was Alpha One to Beta Two?")
        self.assertLessEqual(len(rows),8)
        qs=[x["query"].casefold() for x in rows]
        self.assertEqual(len(qs),len(set(qs)))

if __name__=="__main__":
    unittest.main(verbosity=2)
