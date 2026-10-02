import unittest

from canonical.runtime.typed_template_synthesizer import synthesize_templates


class TypedTemplateSynthesizerTests(unittest.TestCase):
    def test_two_step_composition_is_found(self):
        primitives = [
            {"id": "decode", "inputs": ["bytes"], "output": "text"},
            {"id": "classify", "inputs": ["text"], "output": "intent"},
        ]
        out = synthesize_templates({"raw": "bytes"}, primitives, "intent", max_steps=2)
        self.assertEqual(out["status"], "COMPLETE_WITH_CANDIDATES")
        self.assertTrue(out["complete_within_declared_bound"])
        self.assertEqual(out["candidate_count"], 1)
        self.assertEqual(
            [step["primitive_id"] for step in out["candidates"][0]["steps"]],
            ["decode", "classify"],
        )

    def test_all_bounded_ambiguous_routes_are_preserved(self):
        primitives = [
            {"id": "route_a", "inputs": ["raw"], "output": "target"},
            {"id": "route_b", "inputs": ["raw"], "output": "target"},
        ]
        out = synthesize_templates({"x": "raw"}, primitives, "target", max_steps=1)
        self.assertEqual(out["status"], "COMPLETE_WITH_CANDIDATES")
        routes = {
            tuple(step["primitive_id"] for step in candidate["steps"])
            for candidate in out["candidates"]
        }
        self.assertEqual(routes, {("route_a",), ("route_b",)})
        self.assertTrue(all(not c["truth_authority"] for c in out["candidates"]))

    def test_existing_target_is_zero_step_candidate(self):
        out = synthesize_templates({"answer": "target"}, [], "target", max_steps=0)
        self.assertEqual(out["candidate_count"], 1)
        self.assertEqual(out["candidates"][0]["steps"], [])
        self.assertEqual(out["candidates"][0]["terminal"], "answer")

    def test_no_route_is_complete_no_candidate(self):
        primitives = [{"id": "decode", "inputs": ["bytes"], "output": "text"}]
        out = synthesize_templates({"raw": "bytes"}, primitives, "intent", max_steps=2)
        self.assertEqual(out["status"], "COMPLETE_NO_CANDIDATE")
        self.assertTrue(out["complete_within_declared_bound"])

    def test_repeated_identical_pure_application_is_not_reused(self):
        primitives = [{"id": "same", "inputs": ["x"], "output": "x"}]
        out = synthesize_templates({"a": "x"}, primitives, "never", max_steps=4)
        self.assertEqual(out["status"], "COMPLETE_NO_CANDIDATE")
        self.assertLess(out["explored_states"], 10)

    def test_candidate_limit_fails_exhaustive_claim_closed(self):
        primitives = [
            {"id": "a", "inputs": ["raw"], "output": "target"},
            {"id": "b", "inputs": ["raw"], "output": "target"},
        ]
        out = synthesize_templates(
            {"x": "raw"}, primitives, "target", max_steps=1, max_candidates=1
        )
        self.assertEqual(out["status"], "TRUNCATED")
        self.assertFalse(out["complete_within_declared_bound"])

    def test_invalid_primitive_fails_closed(self):
        out = synthesize_templates(
            {"x": "raw"},
            [{"id": "bad", "inputs": "raw", "output": "target"}],
            "target",
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
