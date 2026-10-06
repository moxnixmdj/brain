from __future__ import annotations

import pathlib
import tempfile
import unittest

import canonical.runtime.goal_action_transitive_effect_compiler_v1 as c


class CompilerTests(unittest.TestCase):
    def test_transitive_process_sink(self):
        src = """
import subprocess
def helper():
    return subprocess.run(["x"])
def _goal_action(action):
    typ=action.get("type")
    if typ=="a":
        return helper()
"""
        out = c.compile_effects(src)
        row = out["rows"][0]
        self.assertIn("PROCESS", row["channels"])
        self.assertIn("helper", row["traversed_local_functions"])

    def test_nested_external_gateway(self):
        src = """
def _external_tool_bridge(kind,payload):
    return {}
def helper():
    return _external_tool_bridge("x",{})
def _goal_action(action):
    typ=action.get("type")
    if typ=="a":
        return helper()
"""
        row = c.compile_effects(src)["rows"][0]
        self.assertIn("NETWORK_OR_EXTERNAL", row["channels"])

    def test_unknown_call_fails_local_closure(self):
        src = """
def _goal_action(action):
    typ=action.get("type")
    if typ=="a":
        return mystery(action)
"""
        row = c.compile_effects(src)["rows"][0]
        self.assertEqual(row["status"], "OPEN_UNRESOLVED_CALLS")
        self.assertIn("mystery", row["unresolved_calls"])

    def test_recursive_local_cycle_terminates(self):
        src = """
def a(): return b()
def b(): return a()
def _goal_action(action):
    typ=action.get("type")
    if typ=="x":
        return a()
"""
        row = c.compile_effects(src)["rows"][0]
        self.assertEqual(row["status"], "LOCAL_CALLGRAPH_RESOLVED_UNDER_ALLOWLIST")
        self.assertEqual(set(row["traversed_local_functions"]), {"a","b"})

    def test_path_reads_and_writes(self):
        src = """
def _goal_action(action):
    typ=action.get("type")
    if typ=="x":
        p=action.get("p")
        return p.read_text(), p.write_text("x")
"""
        row = c.compile_effects(src)["rows"][0]
        self.assertIn("HOST_READ", row["channels"])
        self.assertIn("HOST_WRITE", row["channels"])

    def test_env_read_classified(self):
        src = """
import os
def _goal_action(action):
    typ=action.get("type")
    if typ=="x":
        return os.environ["X"]
"""
        row = c.compile_effects(src)["rows"][0]
        self.assertIn("HOST_ENV", row["channels"])

    def test_bound_runtime_compiles_48_actions(self):
        out = c.evaluate()
        self.assertEqual(
            out["status"],
            "PASS__LOCAL_TRANSITIVE_EFFECT_SURFACE_COMPILED",
            out,
        )
        self.assertEqual(out["action_count"], 48)
        self.assertFalse(out["no_bypass_credit"])

    def test_runtime_blob_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            p = root / c.RUNTIME_REL
            p.parent.mkdir(parents=True)
            p.write_text(
                "def _goal_action(action):\n    return {}\n",
                encoding="utf-8",
            )
            out = c.evaluate(root)
            self.assertEqual(out["status"], "FAIL_CLOSED__RUNTIME_BLOB_DRIFT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
