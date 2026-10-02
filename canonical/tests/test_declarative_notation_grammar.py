import unittest
from canonical.runtime.declarative_notation_grammar import parse_with_grammar, validate_grammar

class DeclarativeNotationGrammarTests(unittest.TestCase):
    def setUp(self):
        self.rules=[
            {
                "id":"surface_finish_ra",
                "kind":"surface_finish",
                "atoms":[
                    {"literal":"SF"},
                    {"capture":"roughness","type":"number","min":0},
                    {"capture":"units","type":"enum","values":["UM","MM"],"optional":True},
                ],
            },
            {
                "id":"fit_class",
                "kind":"fit_class",
                "atoms":[
                    {"literal":"FIT"},
                    {"capture":"class","type":"identifier"},
                    {"capture":"size","type":"number","min":0},
                    {"capture":"units","type":"unit"},
                ],
            },
        ]

    def test_unseen_surface_finish_grammar(self):
        o=parse_with_grammar("SF 3.2 um",self.rules)
        self.assertEqual(o["status"],"PARSED")
        self.assertEqual(o["kind"],"surface_finish")
        self.assertEqual(o["captures"]["roughness"],3.2)
        self.assertEqual(o["captures"]["units"],"UM")

    def test_unseen_fit_grammar(self):
        o=parse_with_grammar("FIT H7 20 mm",self.rules)
        self.assertEqual(o["status"],"PARSED")
        self.assertEqual(o["captures"]["class"],"H7")
        self.assertEqual(o["captures"]["size"],20.0)
        self.assertEqual(o["captures"]["units"],"mm")

    def test_optional_unit(self):
        o=parse_with_grammar("SF 1.6",self.rules)
        self.assertEqual(o["status"],"PARSED")
        self.assertNotIn("units",o["captures"])

    def test_unknown_fails_closed(self):
        o=parse_with_grammar("UNKNOWN 7",self.rules)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertEqual(o["error"],"NO_RULE_MATCH")

    def test_ambiguous_rules_fail_closed(self):
        rules=[
            {"id":"a","kind":"x","atoms":[{"literal":"X"},{"capture":"n","type":"number"}]},
            {"id":"b","kind":"y","atoms":[{"literal":"X"},{"capture":"n","type":"number"}]},
        ]
        o=parse_with_grammar("X 3",rules)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertEqual(o["error"],"AMBIGUOUS_RULE_MATCH")

    def test_invalid_grammar_fails_closed(self):
        rules=[{"id":"bad","kind":"x","atoms":[{"capture":"n","type":"magic"}]}]
        self.assertFalse(validate_grammar(rules)["valid"])
        o=parse_with_grammar("3",rules)
        self.assertEqual(o["status"],"FAIL_CLOSED")
        self.assertEqual(o["error"],"GRAMMAR_INVALID")

if __name__=="__main__":
    unittest.main()
