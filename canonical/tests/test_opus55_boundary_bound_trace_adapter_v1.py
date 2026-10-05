from __future__ import annotations

import unittest

from canonical.runtime.opus55_boundary_bound_trace_adapter_v1 import (
    BOUNDARY_BINDINGS,
    BoundaryBindingError,
    CaptureBoundary,
    append_boundary_event,
    boundary_binding,
)
from canonical.runtime.opus55_causal_trace_ir_v1 import (
    ALLOWED_ACTORS,
    ALLOWED_CHANNELS,
    new_trace,
    verify_trace,
)


class Opus55BoundaryBoundTraceAdapterTests(unittest.TestCase):
    def test_every_boundary_maps_to_allowed_actor_channel(self) -> None:
        self.assertEqual(set(BOUNDARY_BINDINGS), set(CaptureBoundary))
        for boundary in CaptureBoundary:
            binding = boundary_binding(boundary)
            self.assertIn(binding.actor, ALLOWED_ACTORS)
            self.assertIn(binding.channel, ALLOWED_CHANNELS)

    def test_policy_visible_output_is_derived_not_declared(self) -> None:
        trace = new_trace()
        event_hash = append_boundary_event(
            trace,
            {"type": "text", "text": "answer"},
            boundary=CaptureBoundary.OPUS55_VISIBLE_OUT,
            schema_path="TextBlock",
        )
        verify_trace(trace)
        event = trace["events"][0]
        self.assertEqual(event_hash, event["event_sha256"])
        self.assertEqual(event["capsule"]["actor"], "OPUS55_POLICY")
        self.assertEqual(
            event["capsule"]["channel"],
            "R1_MODEL_VISIBLE_SEMANTIC_OUTPUT",
        )

    def test_external_executor_result_is_r0_without_policy_credit(self) -> None:
        trace = new_trace()
        append_boundary_event(
            trace,
            {"type": "tool_result", "value": 7},
            boundary=CaptureBoundary.EXTERNAL_EXECUTOR_IN,
            schema_path="ToolResultBlockParam",
        )
        event = trace["events"][0]
        self.assertEqual(event["capsule"]["actor"], "EXTERNAL_EXECUTOR")
        self.assertEqual(
            event["capsule"]["channel"],
            "R0_EXTERNAL_OBSERVATION_OR_CONFIGURATION_IN",
        )

    def test_fallback_boundaries_require_model_identity(self) -> None:
        trace = new_trace()
        with self.assertRaisesRegex(
            BoundaryBindingError,
            "FALLBACK_BOUNDARY_REQUIRES_MODEL_ID",
        ):
            append_boundary_event(
                trace,
                {"type": "text", "text": "x"},
                boundary=CaptureBoundary.FALLBACK_VISIBLE_OUT,
                schema_path="BetaFallbackBlock",
            )

        append_boundary_event(
            trace,
            {"type": "text", "text": "x"},
            boundary=CaptureBoundary.FALLBACK_VISIBLE_OUT,
            schema_path="BetaFallbackBlock",
            actor_model_id="fallback-model-x",
        )
        verify_trace(trace)

    def test_unknown_boundary_fails_closed(self) -> None:
        with self.assertRaisesRegex(BoundaryBindingError, "UNKNOWN_CAPTURE_BOUNDARY"):
            boundary_binding("CLASSIFIED_BY_VIBES")

    def test_callers_cannot_pass_actor_or_channel(self) -> None:
        trace = new_trace()
        with self.assertRaises(TypeError):
            append_boundary_event(
                trace,
                {},
                boundary=CaptureBoundary.OPUS55_VISIBLE_OUT,
                schema_path="TextBlock",
                actor="FALLBACK_MODEL",  # type: ignore[call-arg]
            )
        with self.assertRaises(TypeError):
            append_boundary_event(
                trace,
                {},
                boundary=CaptureBoundary.OPUS55_VISIBLE_OUT,
                schema_path="TextBlock",
                channel="R0_EXTERNAL_OBSERVATION_OR_CONFIGURATION_IN",  # type: ignore[call-arg]
            )


if __name__ == "__main__":
    unittest.main()
