import unittest
from unittest.mock import patch

from canonical.runtime import root2_livebench_if_astra_inference_adapter_v5 as v5


class LiveBenchV5Tests(unittest.TestCase):
    def req(self, instruction):
        return {
            "task_id":"t",
            "benchmark_id":v5.BENCHMARK_ID,
            "task_payload":{"instruction":instruction},
            "allowed_tools":[],
        }

    def test_single_public_checker_promotes_without_model(self):
        out=v5.infer(self.req("Include exactly 3 numbers in the response; do not use commas within the numbers."))
        self.assertEqual(out["status"],"PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE")
        self.assertEqual(out["response_route"],"LIVEBENCH_IF_PUBLIC_SINGLE_CHECKER_WITNESS_V5")
        self.assertEqual(out["checker_id"],"count:numbers")
        self.assertEqual(out["model_dependency_count"],0)

    def test_conjunction_preserves_v3_route(self):
        req=self.req("Include exactly 3 numbers in the response. Use at least 2 different coordinating conjunctions in the response.")
        sentinel={"status":"V3_SENTINEL"}
        with patch.object(v5.fallback_v3,"infer",return_value=sentinel) as fb:
            out=v5.infer(req)
        self.assertIs(out,sentinel)
        fb.assert_called_once_with(req)

    def test_unknown_preserves_v3_route(self):
        req=self.req("Explain photosynthesis clearly.")
        sentinel={"status":"V3_SENTINEL"}
        with patch.object(v5.fallback_v3,"infer",return_value=sentinel) as fb:
            out=v5.infer(req)
        self.assertIs(out,sentinel)
        fb.assert_called_once_with(req)

    def test_external_tools_still_forbidden(self):
        req=self.req("The output should not contain any whitespace.")
        req["allowed_tools"]=["browser"]
        with self.assertRaises(v5.Root2InferenceBlocked):
            v5.infer(req)


if __name__=="__main__":
    unittest.main()
