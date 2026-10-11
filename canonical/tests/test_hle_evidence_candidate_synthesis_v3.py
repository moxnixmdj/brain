import unittest
from canonical.runtime.hle_evidence_candidate_synthesis_v3 import synthesize

class EvidenceSynthesisV3Tests(unittest.TestCase):
    def one(self,kind,subtype,focus,evidence):
        x=synthesize(contract={"kind":kind,"subtype":subtype,"polarity":"POSITIVE"},focus_terms=focus,evidence=evidence)
        self.assertEqual(x["status"],"ONE_RELATION_BOUND_CANDIDATE",x)
        self.assertEqual(x["external_model_calls"],0)
        self.assertEqual(x["model_dependency_count"],0)
        return x["candidates"][0]["answer"]

    def test_person_by(self):
        self.assertEqual(self.one("PERSON","PERSON",["opera"],"The opera was composed by Richard Example."),"Richard Example")
    def test_person_subject_action(self):
        self.assertEqual(self.one("PERSON","PERSON",["operas"],"Richard Example composed the operas Alpha and Beta."),"Richard Example")
    def test_person_first(self):
        self.assertEqual(self.one("PERSON","PERSON",["peaks"],"Reinhold Example was the first mountaineer to complete the peaks."),"Reinhold Example")
    def test_capital(self):
        self.assertEqual(self.one("LOCATION","CAPITAL",["fictionland","capital"],"The capital of Fictionland is Nova City."),"Nova City")
    def test_birthplace(self):
        self.assertEqual(self.one("LOCATION","CITY",["singer","born"],"The singer was born in Tupelo, Mississippi."),"Tupelo")
    def test_country_demonym_only_for_country(self):
        self.assertEqual(self.one("LOCATION","COUNTRY",["country","retailer"],"ExampleCo is a German retailer."),"Germany")
        y=synthesize(contract={"kind":"LOCATION","subtype":"CITY"},focus_terms=["singer"],evidence="The American singer performed.")
        self.assertNotEqual(y["status"],"ONE_RELATION_BOUND_CANDIDATE")
    def test_work(self):
        self.assertEqual(self.one("WORK_TITLE","WORK_TITLE",["play","example"],"Measure for Example is a play by William Example."),"Measure for Example")
    def test_kinship(self):
        self.assertEqual(self.one("RELATION_TERM","KINSHIP_OR_RELATION",["napoleon"],"Napoleon III was the nephew of Napoleon I."),"nephew")
    def test_lowercase_garbage_not_person(self):
        y=synthesize(contract={"kind":"PERSON","subtype":"PERSON"},focus_terms=["composer"],evidence="The package was composed by an application-level dependency manager for PHP.")
        self.assertNotEqual(y["status"],"ONE_RELATION_BOUND_CANDIDATE")
    def test_focus_replay_rejected(self):
        y=synthesize(contract={"kind":"PERSON","subtype":"PERSON"},focus_terms=["Richard Example","opera"],evidence="The opera was composed by Richard Example.")
        self.assertNotEqual(y["status"],"ONE_RELATION_BOUND_CANDIDATE")

if __name__=="__main__":unittest.main(verbosity=2)
