from __future__ import annotations

import unittest

from canonical.runtime.opus55_causal_trace_ir_v1 import (
    TraceIRError,
    append_event,
    new_trace,
    verify_trace,
)


class Opus55CausalTraceIRTests(unittest.TestCase):
    def test_sequence_branch_parallel_join_and_state_refs(self) -> None:
        trace = new_trace()
        start = append_event(
            trace,
            {"prompt": "solve"},
            schema_path="MessageParam",
            actor="USER_OR_ENVIRONMENT",
            channel="R0_EXTERNAL_OBSERVATION_OR_CONFIGURATION_IN",
        )
        tool_a = append_event(
            trace,
            {"type": "tool_use", "name": "a"},
            schema_path="ToolUseBlock",
            actor="OPUS55_POLICY",
            channel="R2_MODEL_ACTION_OR_TOOL_INTENT",
            causal_parent_hashes=[start],
        )
        tool_b = append_event(
            trace,
            {"type": "tool_use", "name": "b"},
            schema_path="ToolUseBlock",
            actor="OPUS55_POLICY",
            channel="R2_MODEL_ACTION_OR_TOOL_INTENT",
            causal_parent_hashes=[start],
        )
        result_a = append_event(
            trace,
            {"type": "tool_result", "value": 1},
            schema_path="ToolResultBlockParam",
            actor="EXTERNAL_EXECUTOR",
            channel="R0_EXTERNAL_OBSERVATION_OR_CONFIGURATION_IN",
            causal_parent_hashes=[tool_a],
        )
        result_b = append_event(
            trace,
            {"type": "tool_result", "value": 2},
            schema_path="ToolResultBlockParam",
            actor="EXTERNAL_EXECUTOR",
            channel="R0_EXTERNAL_OBSERVATION_OR_CONFIGURATION_IN",
            causal_parent_hashes=[tool_b],
        )
        answer = append_event(
            trace,
            {"type": "text", "text": "3"},
            schema_path="TextBlock",
            actor="OPUS55_POLICY",
            channel="R1_MODEL_VISIBLE_SEMANTIC_OUTPUT",
            causal_parent_hashes=[result_a, result_b],
            state_ref_hashes=[start],
        )

        verify_trace(trace)
        self.assertEqual(trace["head_sha256"], answer)
        self.assertEqual(len(trace["events"]), 6)

    def test_fallback_model_requires_identity(self) -> None:
        trace = new_trace()
        with self.assertRaisesRegex(
            TraceIRError,
            "FALLBACK_MODEL_REQUIRES_MODEL_ID",
        ):
            append_event(
                trace,
                {"type": "text", "text": "fallback"},
                schema_path="TextBlock",
                actor="FALLBACK_MODEL",
                channel="R1_MODEL_VISIBLE_SEMANTIC_OUTPUT",
            )

    def test_unknown_actor_and_channel_fail_closed(self) -> None:
        trace = new_trace()
        with self.assertRaisesRegex(TraceIRError, "UNKNOWN_ACTOR"):
            append_event(
                trace,
                {},
                schema_path="x",
                actor="MYSTERY",
                channel="R0_EXTERNAL_OBSERVATION_OR_CONFIGURATION_IN",
            )

        with self.assertRaisesRegex(TraceIRError, "UNKNOWN_CAUSAL_CHANNEL"):
            append_event(
                trace,
                {},
                schema_path="x",
                actor="OPUS55_POLICY",
                channel="R99_MAGIC",
            )

    def test_forward_or_unknown_causal_reference_fails_closed(self) -> None:
        trace = new_trace()
        with self.assertRaisesRegex(
            TraceIRError,
            "UNKNOWN_OR_FORWARD_REFERENCE",
        ):
            append_event(
                trace,
                {},
                schema_path="x",
                actor="USER_OR_ENVIRONMENT",
                channel="R0_EXTERNAL_OBSERVATION_OR_CONFIGURATION_IN",
                causal_parent_hashes=["0" * 64],
            )

    def test_event_tamper_breaks_hash_chain(self) -> None:
        trace = new_trace()
        append_event(
            trace,
            {"type": "text", "text": "x"},
            schema_path="TextBlock",
            actor="OPUS55_POLICY",
            channel="R1_MODEL_VISIBLE_SEMANTIC_OUTPUT",
        )
        trace["events"][0]["actor_model_id"] = "tampered"

        with self.assertRaisesRegex(TraceIRError, "EVENT_HASH_MISMATCH"):
            verify_trace(trace)

    def test_state_reference_must_point_backward(self) -> None:
        trace = new_trace()
        first = append_event(
            trace,
            {"state": 1},
            schema_path="State",
            actor="OPUS55_POLICY",
            channel="R3_MODEL_OPAQUE_CONTINUATION_STATE",
        )
        append_event(
            trace,
            {"state": 2},
            schema_path="State",
            actor="OPUS55_POLICY",
            channel="R3_MODEL_OPAQUE_CONTINUATION_STATE",
            state_ref_hashes=[first],
        )
        verify_trace(trace)


if __name__ == "__main__":
    unittest.main()
