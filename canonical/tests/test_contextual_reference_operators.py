import unittest

from canonical.runtime.contextual_reference_operators import propose_contextual_references


def text_at(source, span):
    return source[span[0]:span[1]]


class ContextualReferenceOperatorsTests(unittest.TestCase):
    def test_singular_pronoun(self):
        s="The backup process shall verify the checksum. It shall abort on any mismatch."
        out=propose_contextual_references(s)
        b=out["proposal"]["bindings"]
        self.assertEqual(len(b),1,out)
        self.assertEqual(text_at(s,b[0]["mention_span"]),"It")
        self.assertEqual(text_at(s,b[0]["target_span"]),"The backup process")

    def test_plural_pronoun(self):
        s="The parser and verifier shall record their versions. They shall reject incompatible schemas."
        out=propose_contextual_references(s)
        b=out["proposal"]["bindings"]
        self.assertEqual(len(b),1,out)
        self.assertEqual(text_at(s,b[0]["mention_span"]),"They")
        self.assertEqual(text_at(s,b[0]["target_span"]),"The parser and verifier")

    def test_mode_anaphora(self):
        s="If maintenance mode is enabled, the service shall reject writes. In that mode, it may still serve reads."
        out=propose_contextual_references(s)
        rows=[x for x in out["proposal"]["bindings"] if x["kind"]=="explicit_mode_anaphora"]
        self.assertEqual(len(rows),1,out)
        self.assertEqual(text_at(s,rows[0]["target_span"]),"maintenance mode")
        self.assertEqual(text_at(s,rows[0]["mention_span"]),"that mode")

    def test_modal_ellipsis_too(self):
        s="The primary node must persist the lease. The replica must, too."
        out=propose_contextual_references(s)
        rows=out["proposal"]["obligations"]
        self.assertEqual(len(rows),1,out)
        self.assertEqual(text_at(s,rows[0]["subject_span"]),"The replica")
        self.assertEqual(text_at(s,rows[0]["predicate_span"]),"persist the lease")
        self.assertEqual(rows[0]["modality"],"must")

    def test_respectively_mapping(self):
        s="The producer and verifier shall write candidate.json and verdict.json, respectively."
        out=propose_contextual_references(s)
        obligations=out["proposal"]["obligations"]
        self.assertEqual(len(obligations),2,out)
        pairs=[(text_at(s,x["subject_span"]),text_at(s,x["object_span"])) for x in obligations]
        self.assertEqual(pairs,[("The producer","candidate.json"),("verifier","verdict.json")])

    def test_former_latter_fails_closed(self):
        s="The producer writes candidate.json and the verifier writes verdict.json. The former must not overwrite the latter."
        out=propose_contextual_references(s)
        unresolved=[x["type"] for x in out["unresolved"]]
        self.assertEqual(unresolved.count("FORMER_LATTER_REQUIRES_UNIQUE_PAIR_GRAPH"),2)
        self.assertFalse(any(x["kind"].startswith("former") for x in out["proposal"]["bindings"]))

    def test_demonstrative_event_remains_unresolved(self):
        s="The verifier shall recompute the manifest hash. This validation must occur before promotion."
        out=propose_contextual_references(s)
        self.assertIn("DEMONSTRATIVE_EVENT_REFERENCE_REQUIRES_EVENT_SEMANTICS",
                      [x["type"] for x in out["unresolved"]])


if __name__ == "__main__":
    unittest.main()
