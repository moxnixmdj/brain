from __future__ import annotations

import unittest

from canonical.runtime.composition_state_capsule_guard_v2 import validate_plan


class CompositionAmbientFileBypassCounterexampleTests(unittest.TestCase):
    def test_undeclared_persistent_file_channel_is_accepted_by_v2_guard(self):
        actions = [
            {
                "type": "write_json_records",
                "args": {
                    "output_path": "canonical/tmp/ambient_bridge.json",
                    "fields": ["value"],
                    "records": [{"value": "SECRET_FROM_STEP_0"}],
                },
            },
            {
                "type": "read_file",
                "args": {"path": "canonical/tmp/ambient_bridge.json"},
            },
            {"type": "finish", "args": {}},
        ]
        # Deliberately declare no dependency from row 1 on row 0. There are no
        # $result references, so V2's declared-result-reference checks have
        # nothing to bind. Yet at runtime row 1 can observe row 0's file.
        contract = [
            {
                "cycle": 0,
                "capability_id": "writer",
                "requires": [],
                "provides": ["writer_done"],
                "result_fields": [],
                "provider_bindings": {},
            },
            {
                "cycle": 1,
                "capability_id": "reader",
                "requires": [],
                "provides": ["reader_done"],
                "result_fields": [],
                "provider_bindings": {},
            },
        ]
        out = validate_plan(actions, contract, [])
        self.assertEqual(out["status"], "PASS", out)
        self.assertTrue(out["declared_cross_capability_state_no_bypass"], out)
        self.assertEqual(out["semantic_declaration_completeness"], "UNVERIFIED")

    def test_result_reference_bypass_is_still_rejected(self):
        actions = [
            {"type": "invoke_capability", "args": {}},
            {
                "type": "read_file",
                "args": {"path": {"$result": {"cycle": 0, "field": "path"}}},
            },
            {"type": "finish", "args": {}},
        ]
        contract = [
            {
                "cycle": 0,
                "capability_id": "writer",
                "requires": [],
                "provides": ["writer_done"],
                "result_fields": ["path"],
                "provider_bindings": {},
            },
            {
                "cycle": 1,
                "capability_id": "reader",
                "requires": [],
                "provides": ["reader_done"],
                "result_fields": [],
                "provider_bindings": {},
            },
        ]
        with self.assertRaisesRegex(
            Exception, "RESULT_REFERENCE_BYPASSES_REQUIRED_EFFECT"
        ):
            validate_plan(actions, contract, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
