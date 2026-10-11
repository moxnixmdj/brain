import unittest
from canonical.runtime.hle_native_question_contract_v3 import compile_question

class QuestionContractV3Tests(unittest.TestCase):
    def kind(self,q):
        x=compile_question(task_id="x",question=q)
        self.assertTrue(x["pass"])
        self.assertEqual(x["external_model_calls"],0)
        self.assertEqual(x["model_dependency_count"],0)
        self.assertFalse(x["gold_accessed"])
        return x["question_kind"],x["answer_subtype"]

    def test_capital(self): self.assertEqual(self.kind("What is the capital of Fictionland?")[0],"LOCATION")
    def test_malformed_which_city(self): self.assertEqual(self.kind("Which. Australian city is named after a governor?")[0],"LOCATION")
    def test_country_origin(self): self.assertEqual(self.kind("What is the country of origin of ExampleCo?"),("LOCATION","COUNTRY"))
    def test_region(self): self.assertEqual(self.kind("X came from which French region?"),("LOCATION","REGION"))
    def test_university(self): self.assertEqual(self.kind("A person dropped out which US university?"),("LOCATION","UNIVERSITY"))
    def test_person_role(self): self.assertEqual(self.kind("Which composer wrote the operas A and B?")[0],"PERSON")
    def test_person_embedded_role(self): self.assertEqual(self.kind("Which five foot tall French artist made posters?")[0],"PERSON")
    def test_work_title(self): self.assertEqual(self.kind("Which of Shakespeare's plays is set in Vienna?")[0],"WORK_TITLE")
    def test_film_title(self): self.assertEqual(self.kind("In which Walt Disney film does the song Example appear?")[0],"WORK_TITLE")
    def test_relation(self): self.assertEqual(self.kind("What relation was X to Y?")[0],"RELATION_TERM")
    def test_term_equal(self): self.assertEqual(self.kind("What does mass times acceleration equal?")[0],"TERM")

if __name__=="__main__": unittest.main(verbosity=2)
