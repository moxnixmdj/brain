from __future__ import annotations

import unittest

from canonical.runtime import science_typed_action_protocol_v1 as p


class ProtocolTests(unittest.TestCase):
    def test_shell_remains_shell(self):
        cmd, keys = p.compile_typed_source("shell", "printf ok")
        self.assertEqual(cmd, "printf ok")
        self.assertEqual(keys, set())

    def test_python_is_wrapped_not_sent_as_shell(self):
        cmd, keys = p.compile_typed_source("python", "print('ok')")
        self.assertTrue(cmd.startswith("python -c "))
        self.assertIn("print", cmd)
        self.assertEqual(keys, set())

    def test_python_literal_schema_key_requires_declaration(self):
        with self.assertRaisesRegex(p.ScienceTypedActionError, "UNDECLARED:box"):
            p.compile_typed_source(
                "python",
                "print(spec['box'])",
                schema_requirements=[],
            )

    def test_python_literal_schema_key_passes_when_declared(self):
        req = p.normalize_schema_requirements([
            {"path": "/app/spec.json", "format": "json", "keys": ["box"]}
        ])
        cmd, keys = p.compile_typed_source(
            "python",
            "print(spec['box'])",
            schema_requirements=req,
        )
        self.assertTrue(cmd.startswith("python -c "))
        self.assertEqual(keys, {"box"})

    def test_schema_probe_is_read_only_and_content_bound(self):
        row = p.normalize_schema_requirements([
            {"path": "/app/spec.json", "format": "json", "keys": ["box", "output"]}
        ])[0]
        cmd = p.schema_probe_command(row)
        self.assertIn("python -c", cmd)
        self.assertIn("spec.json", cmd)
        self.assertNotIn("curl", cmd)
        self.assertNotIn("wget", cmd)

    def test_deliverable_npz_gets_format_check(self):
        row = p.normalize_deliverables([
            {"path": "/app/result.npz", "format": "npz"}
        ])[0]
        cmd = p.deliverable_check_command(row)
        self.assertIn("test -s", cmd)
        self.assertIn("np.load", cmd)

    def test_action_fingerprint_changes_when_source_changes(self):
        base = {
            "executor": "python",
            "command_source": "print(1)",
            "verify_executor": "shell",
            "verify_source": "true",
            "schema_requirements": [],
            "deliverables": [],
        }
        a = p.action_fingerprint(base)
        b = p.action_fingerprint({**base, "command_source": "print(2)"})
        self.assertEqual(len(a), 64)
        self.assertNotEqual(a, b)

    def test_source_output_field_creates_only_postcondition(self):
        out = p.source_observed_deliverables([
            {
                "path": "/app/spec.json",
                "selected_scalars": {
                    "output": "/app/result.npz",
                    "other": "/app/not-authoritative.bin",
                },
            }
        ])
        self.assertEqual(out, [{"path": "/app/result.npz", "format": "npz"}])

    def test_paths_outside_app_fail_closed(self):
        with self.assertRaisesRegex(p.ScienceTypedActionError, "OUTSIDE_APP"):
            p.normalize_deliverables([{"path": "/tmp/x.json", "format": "json"}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
