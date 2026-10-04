from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.h100_zero_learned_tool_trace_normalizer_v1 import (
    normalize_tool_trace,
)

PRE = (
    Path(__file__).resolve().parents[1]
    / "governance"
    / "H100_ZERO_LEARNED_TOOL_TRACE_VARIATION_PREEXPOSURE_V1.json"
)


class H100ZeroLearnedToolTraceNormalizerTests(unittest.TestCase):
    def test_all_preexposed_tasks_exact(self):
        doc = json.loads(PRE.read_text(encoding="utf-8"))
        schema = doc["declared_schema"]
        self.assertEqual(len(doc["tasks"]), 10)
        for task in doc["tasks"]:
            out = normalize_tool_trace(
                task["payload"],
                inputs=schema["inputs"],
                target=schema["target"],
                format_hint=task["format"],
            )
            self.assertEqual(out["status"], task["expected_status"], (task["task_id"], out))
            self.assertEqual(out["rows"], task["expected_rows"], (task["task_id"], out))
            self.assertEqual(out["persistent_learned_bytes"], 0)
            self.assertEqual(out["external_frontier_model_calls"], 0)
            self.assertEqual(out["external_learned_capability_calls"], 0)

    def test_unknown_wrapper_never_guesses_by_position(self):
        out = normalize_tool_trace(
            [{"left":{"x":1,"z":2},"right":{"y":3}}],
            inputs=["x","z"], target="y", format_hint="JSON_ROWS"
        )
        self.assertEqual(out["status"], "ABSTAIN_TRACE_STRUCTURE_UNKNOWN")

    def test_retry_input_change_conflicts(self):
        out = normalize_tool_trace(
            [
                {"call_id":"a","attempt":1,"event":"request","data":{"x":1,"z":2}},
                {"call_id":"a","attempt":1,"event":"error","data":{"type":"timeout"}},
                {"call_id":"a","attempt":2,"event":"request","data":{"x":9,"z":2}},
                {"call_id":"a","attempt":2,"event":"response","data":{"y":11}},
            ],
            inputs=["x","z"], target="y", format_hint="EVENT_STREAM"
        )
        self.assertEqual(out["status"], "ABSTAIN_TRACE_CONFLICT")

    def test_identical_duplicate_response_is_stable(self):
        out = normalize_tool_trace(
            [
                {"call_id":"a","event":"request","data":{"x":1,"z":2}},
                {"call_id":"a","event":"response","data":{"y":3}},
                {"call_id":"a","event":"response","data":{"y":3}},
            ],
            inputs=["x","z"], target="y", format_hint="EVENT_STREAM"
        )
        self.assertEqual(out["status"], "TYPED_NUMERIC_SCHEMA_COMPILED")
        self.assertEqual(out["rows"], [{"x":1.0,"z":2.0,"y":3.0}])

    def test_nonfinite_fails_closed(self):
        out = normalize_tool_trace(
            [{"request":{"x":float("inf"),"z":2},"response":{"y":3}}],
            inputs=["x","z"], target="y", format_hint="JSON_ROWS"
        )
        self.assertEqual(out["status"], "ABSTAIN_TRACE_NONNUMERIC")


if __name__ == "__main__":
    unittest.main(verbosity=2)
