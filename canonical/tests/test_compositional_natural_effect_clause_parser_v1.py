from __future__ import annotations
import unittest
from canonical.runtime.certified_compositional_natural_effect_clause_v1 import parse_compositional_effect_clauses

def sentence(eid="B.t",value="12"):
    return (
        f"The complete effect {eid} on threshold replaces it with {value}, "
        "is unconditional, is valid from 2026-07-01, has no end date, "
        "and supersedes A.t."
    )

class Parser(unittest.TestCase):
    def test_complete_replace(self):
        out=parse_compositional_effect_clauses(sentence(),source="B")
        self.assertEqual(out["status"],"PARSED",out)
        row=out["clauses"][0]
        self.assertEqual(row["inventory"],{"target_id":"threshold","effect_ids":["B.t"]})
        e=row["effect"]
        self.assertEqual(e["effect_class"],"REPLACE")
        self.assertEqual(e["value"],12)
        self.assertEqual(e["conditions"],{})
        self.assertEqual(e["valid_from"],"2026-07-01")
        self.assertIsNone(e["valid_until"])
        self.assertEqual(e["supersedes"],["A.t"])

    def test_unrecognized_text_produces_no_claim(self):
        out=parse_compositional_effect_clauses(
            "The threshold becomes 12 next July.",source="B"
        )
        self.assertEqual(out["status"],"PARSED")
        self.assertEqual(out["clauses"],[])

    def test_noncanonical_json_unresolved(self):
        text=sentence(value='{"b": 2, "a": 1}')
        out=parse_compositional_effect_clauses(text,source="B")
        self.assertEqual(out["status"],"UNRESOLVED")

    def test_duplicate_target_unresolved(self):
        out=parse_compositional_effect_clauses(
            sentence()+"\n"+sentence("B.2","13"),source="B"
        )
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertIn("DUPLICATE_COMPLETE_TARGET",out["reason"])

if __name__=="__main__":
    unittest.main()
