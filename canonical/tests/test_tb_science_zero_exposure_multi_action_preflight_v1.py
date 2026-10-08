from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from canonical.runtime import tb_science_zero_exposure_multi_action_preflight_v1 as p


class MultiActionPreflightTests(unittest.TestCase):
    def test_prompt_is_synthetic_and_requires_three_actions(self):
        prompt=p._prompt(2)
        self.assertIn("ZERO-BENCHMARK-EXPOSURE",prompt)
        self.assertIn("exactly three harmless local candidates",prompt)
        self.assertNotIn("terminal-bench-science/",prompt.lower())

    def test_select_prompt_finds_exact_token_window(self):
        def fake_count(payload):
            user=payload["messages"][1]["content"]
            return 1000 + user.count(p._FILLER)
        with patch.object(p.planner,"count_input_tokens",side_effect=fake_count):
            prompt,tokens,calls=p.select_prompt()
        self.assertGreaterEqual(tokens,p.TARGET_MIN_INPUT_TOKENS)
        self.assertLessEqual(tokens,p.TARGET_MAX_INPUT_TOKENS)
        self.assertEqual(tokens,1000+prompt.count(p._FILLER))
        self.assertLessEqual(calls,p.MAX_SEARCH_CALLS)

    def test_validate_exact_three_action_shape(self):
        proposal={
            "material_requirements":["PRECHECK_A","PRECHECK_B","PRECHECK_C"],
            "candidates":[
                {"action_id":"PREFLIGHT_A","covers":["PRECHECK_A"],"command":"printf preflight-a","verify_command":"printf verify-a"},
                {"action_id":"PREFLIGHT_B","covers":["PRECHECK_B"],"depends_on":["PREFLIGHT_A"],"timeout_sec":1200,"verify_timeout_sec":300,"command":"printf preflight-b","verify_command":"printf verify-b"},
                {"action_id":"PREFLIGHT_C","covers":["PRECHECK_C"],"command":"printf preflight-c","verify_command":"printf verify-c"},
            ],
        }
        out=p._validate_proposal(json.dumps(proposal))
        self.assertEqual(len(out["candidates"]),3)

    def test_run_preflight_binds_three_candidates_and_dependency(self):
        proposal={
            "material_requirements":["PRECHECK_A","PRECHECK_B","PRECHECK_C"],
            "candidates":[
                {"action_id":"PREFLIGHT_A","covers":["PRECHECK_A"],"command":"printf preflight-a","verify_command":"printf verify-a"},
                {"action_id":"PREFLIGHT_B","covers":["PRECHECK_B"],"depends_on":["PREFLIGHT_A"],"timeout_sec":1200,"verify_timeout_sec":300,"command":"printf preflight-b","verify_command":"printf verify-b"},
                {"action_id":"PREFLIGHT_C","covers":["PRECHECK_C"],"command":"printf preflight-c","verify_command":"printf verify-c"},
            ],
        }
        with patch.object(p,"select_prompt",return_value=("synthetic",7200,4)), \
             patch.object(p.planner,"effective_timeout_s",return_value=660), \
             patch.object(p.planner,"plan",return_value={
                 "text":json.dumps(proposal),
                 "input_tokens":7200,
                 "effective_timeout_s":660,
                 "duration_s":1.0,
                 "model":"brain-qwen3.5-9b",
                 "transport":"PINNED_LOCAL_QWEN_LLAMA_CPP_TOOL_CALL__EXACT_SERVER_TOKEN_COUNT",
                 "endpoint":"http://127.0.0.1:8080/v1/chat/completions",
                 "token_count_endpoint":"http://127.0.0.1:8080/v1/chat/completions/input_tokens",
             }):
            out=p.run_preflight()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proposal_candidate_count"],3)
        self.assertTrue(out["dependency_edge_verified"])
        self.assertEqual(out["benchmark_task_exposure"],0)

    def test_rejects_single_candidate_regression(self):
        proposal={
            "material_requirements":["PRECHECK_A","PRECHECK_B","PRECHECK_C"],
            "candidates":[
                {"action_id":"PREFLIGHT_A","covers":["PRECHECK_A"],"command":"printf preflight-a","verify_command":"printf verify-a"},
            ],
        }
        with self.assertRaisesRegex(Exception,"EXACTLY_THREE"):
            p._validate_proposal(json.dumps(proposal))


if __name__=="__main__":
    unittest.main(verbosity=2)
