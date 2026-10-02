import unittest

from canonical.runtime.source_traceable_semantic_ir import compile_semantic_ir


class SourceTraceableSemanticIRTests(unittest.TestCase):
    def src(self, span):
        return {"path": "spec.txt", "span": span}

    def test_compiles_and_merges_duplicate_support(self):
        out = compile_semantic_ir({
            "entities": [
                {"id": "pump", "type": "component", "source": self.src([0, 4])}
            ],
            "facts": [
                {"subject": "pump", "predicate": "state", "object": "ON", "source": self.src([10, 12])},
                {"subject": "pump", "predicate": "state", "object": "ON", "source": self.src([30, 32])},
            ],
        })
        self.assertEqual(out["status"], "COMPILED")
        self.assertEqual(len(out["facts"]), 1)
        self.assertEqual(len(out["facts"][0]["sources"]), 2)
        self.assertEqual(out["conflicts"], [])

    def test_conflict_becomes_unknown_not_guess(self):
        out = compile_semantic_ir({
            "entities": [
                {"id": "pump", "type": "component", "source": self.src([0, 4])}
            ],
            "facts": [
                {"subject": "pump", "predicate": "state", "object": "ON", "source": self.src([10, 12])},
                {"subject": "pump", "predicate": "state", "object": "OFF", "source": self.src([30, 33])},
            ],
        })
        self.assertEqual(out["status"], "COMPILED_WITH_UNKNOWNS")
        self.assertEqual(out["facts"], [])
        self.assertEqual(out["conflicts"][0]["status"], "UNKNOWN_CONFLICT")
        self.assertEqual(len(out["conflicts"][0]["alternatives"]), 2)

    def test_missing_provenance_fails_closed(self):
        out = compile_semantic_ir({
            "facts": [{"subject": "x", "predicate": "p", "object": 1}]
        })
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("missing source object", out["errors"][0])

    def test_unknown_subject_fails_when_entities_declared(self):
        out = compile_semantic_ir({
            "entities": [{"id": "known", "type": "thing", "source": self.src([0, 1])}],
            "facts": [{"subject": "other", "predicate": "p", "object": 1, "source": self.src([2, 3])}],
        })
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_ambiguity_is_preserved(self):
        out = compile_semantic_ir({
            "ambiguities": [{
                "id": "a1",
                "alternatives": ["A", "B"],
                "source": self.src([5, 9]),
            }]
        })
        self.assertEqual(out["status"], "COMPILED_WITH_UNKNOWNS")
        self.assertEqual(out["ambiguities"][0]["alternatives"], ["A", "B"])

    def test_deterministic_output_order(self):
        a = compile_semantic_ir({
            "facts": [
                {"subject": "b", "predicate": "p", "object": 2, "source": {"observation_id": "2"}},
                {"subject": "a", "predicate": "p", "object": 1, "source": {"observation_id": "1"}},
            ]
        })
        b = compile_semantic_ir({
            "facts": list(reversed([
                {"subject": "b", "predicate": "p", "object": 2, "source": {"observation_id": "2"}},
                {"subject": "a", "predicate": "p", "object": 1, "source": {"observation_id": "1"}},
            ]))
        })
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
