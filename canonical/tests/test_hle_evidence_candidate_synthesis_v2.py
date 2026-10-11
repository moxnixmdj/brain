import unittest
from canonical.runtime.hle_evidence_candidate_synthesis_v2 import synthesize

class EvidenceCandidateSynthesisV2Tests(unittest.TestCase):
    def one(self, kind, focus, evidence):
        o=synthesize(contract={"kind":kind,"polarity":"POSITIVE"},focus_terms=focus,evidence=evidence)
        self.assertEqual(o["status"],"ONE_RELATION_BOUND_CANDIDATE",o)
        self.assertEqual(len(o["candidates"]),1)
        self.assertEqual(o["external_model_calls"],0)
        self.assertEqual(o["model_dependency_count"],0)
        return o["candidates"][0]["answer"]

    def test_kinship(self):
        self.assertEqual(self.one("RELATION_TERM",["emperor","france"],
            "The later emperor was the nephew of the earlier ruler of France.").casefold(),"nephew")

    def test_capital(self):
        self.assertEqual(self.one("LOCATION",["fictionland","capital"],
            "The capital of Fictionland is Nova City.").casefold(),"nova city")

    def test_birthplace(self):
        self.assertEqual(self.one("LOCATION",["singer","mississippi"],
            "The singer was born in Tupelo, Mississippi.").casefold(),"tupelo")

    def test_person_composed_by(self):
        self.assertEqual(self.one("PERSON",["alpha","beta","opera"],
            "The operas Alpha and Beta were composed by Richard Example.").casefold(),"richard example")

    def test_person_role_subject(self):
        self.assertEqual(self.one("PERSON",["fourteen","peaks"],
            "Reinhold Example was the first mountaineer to complete all fourteen peaks.").casefold(),"reinhold example")

    def test_term_known_as(self):
        self.assertEqual(self.one("TERM",["sugar","dextrose"],
            "This form of sugar is also known as Glucose.").casefold(),"glucose")

    def test_newton(self):
        self.assertEqual(self.one("SHORT_TEXT",["mass","acceleration"],
            "In Newtonian mechanics, mass times acceleration equals force.").casefold(),"force")

    def test_reject_focus_replay(self):
        o=synthesize(contract={"kind":"PERSON","polarity":"POSITIVE"},
            focus_terms=["richard example","alpha"],
            evidence="Alpha was composed by Richard Example.")
        self.assertNotEqual(o["status"],"ONE_RELATION_BOUND_CANDIDATE")

    def test_no_external_cognition(self):
        o=synthesize(contract={"kind":"TERM","polarity":"POSITIVE"},
            focus_terms=["fictional"],evidence="The fictional object is called Zephyr.")
        self.assertEqual(o["external_model_calls"],0)
        self.assertEqual(o["external_reasoning_model_calls"],0)
        self.assertEqual(o["model_dependency_count"],0)
        self.assertFalse(o["gold_accessed"])

if __name__=="__main__":
    unittest.main(verbosity=2)
