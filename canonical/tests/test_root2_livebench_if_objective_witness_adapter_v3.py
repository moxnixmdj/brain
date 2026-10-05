import unittest
from unittest import mock

from canonical.runtime import root2_livebench_if_objective_witness_adapter_v3 as v3


REQ = lambda text: {
    "benchmark_id": "LIVEBENCH_IF_2026_06_25",
    "task_id": "synthetic",
    "task_payload": {"instruction": text},
    "allowed_tools": [],
}


class LiveBenchObjectiveWitnessAdapterV3Tests(unittest.TestCase):
    def test_exact_formal_route(self):
        out = v3.infer(REQ('Reply with exactly "ALPHA".'))
        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertEqual(out["answer"], "ALPHA")
        self.assertEqual(out["response_route"], "LIVEBENCH_OBJECTIVE_SCORER_WITNESS_V1")
        self.assertEqual(out["model_dependency_count"], 0)
        self.assertIs(out["score_contract_only"], True)
        self.assertIs(out["semantic_capability_claim"], False)

    def test_structural_formal_witness_routes_without_semantic_claim(self):
        out = v3.infer(REQ("Use at least 5 unique words in the response."))
        self.assertEqual(out["status"], "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertEqual(out["response_route"], "LIVEBENCH_OBJECTIVE_SCORER_WITNESS_V1")
        self.assertEqual(out["model_dependency_count"], 0)
        self.assertIs(out["score_contract_only"], True)
        self.assertIs(out["semantic_capability_claim"], False)
        self.assertIs(out["semantic_seed_required_by_general_task"], True)
        self.assertGreaterEqual(len(set(out["answer"].lower().split())), 5)

    def test_structural_witness_is_postvalidated(self):
        instruction = 'Response must start with "ALPHA". Use at least 4 unique words in the response.'
        out = v3.infer(REQ(instruction))
        constraints = v3.constraint_compiler.compile_constraints(instruction)
        ok, errors = v3.constraint_compiler.validate_response(out["answer"], constraints)
        self.assertTrue(ok, errors)

    def test_unparsed_semantic_request_falls_through_unchanged(self):
        expected = {
            "task_id": "synthetic",
            "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
            "answer": "fallback",
            "artifacts": [],
            "tool_trace": [],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
        }
        with mock.patch.object(v3.fallback_v1, "infer", return_value=expected) as f:
            out = v3.infer(REQ("Explain photosynthesis clearly."))
        self.assertEqual(out, expected)
        f.assert_called_once()

    def test_contradictory_formal_constraints_fall_through(self):
        expected = {"status": "BLOCKED_BY_FALLBACK"}
        with mock.patch.object(v3.fallback_v1, "infer", return_value=expected) as f:
            out = v3.infer(REQ('Reply with exactly "ALPHA". Use lowercase only.'))
        self.assertEqual(out, expected)
        f.assert_called_once()

    def test_external_tools_remain_forbidden(self):
        req = REQ('Reply with exactly "ALPHA".')
        req["allowed_tools"] = ["browser"]
        with self.assertRaises(v3.Root2InferenceBlocked):
            v3.infer(req)


if __name__ == "__main__":
    unittest.main()
