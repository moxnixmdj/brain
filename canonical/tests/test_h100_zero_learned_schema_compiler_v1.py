from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.h100_zero_learned_schema_compiler_v1 import (
    SchemaCompilerError,
    compile_observations,
)

PRE = Path(__file__).resolve().parents[1] / "governance" / "H100_ZERO_LEARNED_SCHEMA_STRESS_PREEXPOSURE_V1.json"


class H100ZeroLearnedSchemaCompilerTests(unittest.TestCase):
    def test_all_preexposed_tasks_compile_exactly(self):
        doc = json.loads(PRE.read_text())
        self.assertEqual(doc["task_count"], 8)
        self.assertEqual(len(doc["tasks"]), 8)
        for task in doc["tasks"]:
            out = compile_observations(
                task["payload"],
                inputs=task["expected_inputs"],
                target=task["target"],
                format_hint=task["format"],
            )
            self.assertEqual(out["status"], "TYPED_NUMERIC_SCHEMA_COMPILED", task["task_id"])
            self.assertEqual(out["inputs"], task["expected_inputs"], task["task_id"])
            self.assertEqual(out["target"], task["target"], task["task_id"])
            self.assertGreater(out["row_count"], 0, task["task_id"])
            self.assertEqual(out["persistent_learned_bytes"], 0)
            self.assertEqual(out["external_frontier_model_calls"], 0)
            self.assertEqual(out["external_learned_capability_calls"], 0)

    def test_scientific_notation_is_exactly_numeric(self):
        out = compile_observations(
            ["x = +1e-3 ; z = -2.5E+1 ; y = -2.4999e1"],
            inputs=["x", "z"],
            target="y",
            format_hint="FREE_TEXT_KEY_VALUE",
        )
        self.assertAlmostEqual(out["rows"][0]["x"], 0.001)
        self.assertAlmostEqual(out["rows"][0]["z"], -25.0)
        self.assertAlmostEqual(out["rows"][0]["y"], -24.999)

    def test_missing_field_fails_closed(self):
        with self.assertRaisesRegex(SchemaCompilerError, "TEXT_REQUIRED_FIELD_MISSING"):
            compile_observations(
                ["x=1.0, y=2.0"],
                inputs=["x", "z"],
                target="y",
                format_hint="FREE_TEXT_KEY_VALUE",
            )

    def test_tool_conflict_fails_closed(self):
        with self.assertRaisesRegex(SchemaCompilerError, "TOOL_TRACE_FIELD_CONFLICT"):
            compile_observations(
                [{"arguments":{"x":1.0,"y":2.0},"result":{"y":3.0}}],
                inputs=["x"],
                target="y",
                format_hint="TOOL_TRACE",
            )

    def test_unsupported_format_fails_closed(self):
        with self.assertRaisesRegex(SchemaCompilerError, "UNSUPPORTED_OR_MISSING_FORMAT_HINT"):
            compile_observations("x=1 y=2", inputs=["x"], target="y", format_hint="PROSE_MAGIC")

    def test_semantic_role_is_not_inferred(self):
        with self.assertRaisesRegex(SchemaCompilerError, "INPUT_SCHEMA_INVALID"):
            compile_observations(["x=1,y=2"], inputs=[], target="y", format_hint="FREE_TEXT_KEY_VALUE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
