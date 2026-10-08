from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import tb_science_zero_exposure_transport_preflight_v1 as p


class ZeroExposurePreflightTests(unittest.TestCase):
    def test_prompt_contains_no_benchmark_task_content(self):
        prompt=p._prompt(3)
        self.assertIn("ZERO-BENCHMARK-EXPOSURE",prompt)
        self.assertIn("SYNTHETIC_INERT",prompt)
        self.assertNotIn("terminal-bench-science/",prompt.lower())

    def test_select_prompt_finds_exact_token_window(self):
        def fake_count(payload):
            user=payload["messages"][1]["content"]
            units=user.count(p._FILLER)
            return 1000 + units
        with patch.object(p.planner,"count_input_tokens",side_effect=fake_count):
            prompt,tokens,calls=p.select_prompt()
        self.assertGreaterEqual(tokens,p.TARGET_MIN_INPUT_TOKENS)
        self.assertLessEqual(tokens,p.TARGET_MAX_INPUT_TOKENS)
        self.assertEqual(tokens,1000+prompt.count(p._FILLER))
        self.assertLessEqual(calls,p.MAX_SEARCH_CALLS)

    def test_run_preflight_requires_stable_exact_count_and_candidate(self):
        selected=p.TARGET_MIN_INPUT_TOKENS
        proposal={
            "material_requirements":["PRECHECK"],
            "candidates":[{
                "action_id":"A1",
                "covers":["PRECHECK"],
                "command":"printf preflight-ready",
                "verify_command":"printf preflight-verified",
            }],
        }
        import json
        with patch.object(p,"select_prompt",return_value=("synthetic",selected,4)), \
             patch.object(p.planner,"effective_timeout_s",return_value=657), \
             patch.object(p.planner,"plan",return_value={
                 "text":json.dumps(proposal),
                 "input_tokens":selected,
                 "effective_timeout_s":657,
                 "duration_s":1.5,
                 "model":"brain-qwen3.5-9b",
                 "transport":"PINNED_LOCAL_QWEN_LLAMA_CPP_TOOL_CALL__EXACT_SERVER_TOKEN_COUNT",
                 "endpoint":"http://127.0.0.1:8080/v1/chat/completions",
                 "token_count_endpoint":"http://127.0.0.1:8080/v1/chat/completions/input_tokens",
             }):
            out=p.run_preflight()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["benchmark_task_exposure"],0)
        self.assertEqual(out["observed_input_tokens"],selected)
        self.assertEqual(out["proposal_candidate_count"],1)

    def test_run_preflight_fails_on_token_count_drift(self):
        with patch.object(p,"select_prompt",return_value=("synthetic",7200,1)), \
             patch.object(p.planner,"effective_timeout_s",return_value=660), \
             patch.object(p.planner,"plan",return_value={
                 "text":"{}",
                 "input_tokens":7199,
                 "effective_timeout_s":660,
             }):
            with self.assertRaisesRegex(Exception,"TOKEN_COUNT_NOT_STABLE"):
                p.run_preflight()


if __name__=="__main__":
    unittest.main(verbosity=2)
