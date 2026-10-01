import unittest
from canonical.runtime.explicit_definition_reference_graph import compile_reference_graph

class Tests(unittest.TestCase):
    def test_cross_sentence_named_definition(self):
        text="Critical artifact means a signed release package. Every Critical artifact must be archived."
        out=compile_reference_graph(text)
        self.assertEqual(out["status"],"COMPILED",out)
        self.assertEqual(out["definition_count"] if "definition_count" in out else len(out["definitions"]),1)
        self.assertEqual(out["references"][0]["resolved_named_definitions"][0]["term"],"Critical artifact")

    def test_refers_to_form(self):
        text="Primary record refers to the newest valid row. The Primary record must be returned."
        out=compile_reference_graph(text)
        self.assertEqual(out["status"],"COMPILED",out)
        self.assertEqual(len(out["references"]),1)

    def test_conflicting_definition_fails(self):
        text="Mode means alpha. Mode means beta. Mode must be used."
        out=compile_reference_graph(text)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertTrue(any(x.startswith("CONFLICTING_DEFINITION:") for x in out["errors"]))

    def test_definition_cycle_fails(self):
        text="Alpha means Beta. Beta means Alpha. Alpha must be emitted."
        out=compile_reference_graph(text)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertTrue(any(x.startswith("DEFINITION_CYCLE:") for x in out["errors"]))

    def test_pronoun_is_not_claimed(self):
        text="Primary record means the newest valid row. It must be returned."
        out=compile_reference_graph(text)
        self.assertEqual(out["status"],"COMPILED")
        self.assertEqual(out["references"],[])
        self.assertIn("PRONOUN_RESOLUTION",out["unresolved_semantics"])

if __name__=="__main__":
    unittest.main()
