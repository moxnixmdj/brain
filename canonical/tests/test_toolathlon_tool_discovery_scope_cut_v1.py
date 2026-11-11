from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.toolathlon_tool_discovery_scope_cut_v1 import (
    BIND_SERVERS_MARKER,
    CONNECT_MARKER,
    GET_TOOLS_MARKER,
    evaluate_checkout,
)


def _make_checkout(root: Path, task_count: int = 108, include_server_field: bool = True, correct_order: bool = True) -> None:
    for i in range(task_count):
        d = root / "tasks" / "finalpool" / f"task-{i:03d}"
        d.mkdir(parents=True, exist_ok=True)
        payload = {"needed_local_tools": ["claim_done"]}
        if include_server_field:
            payload["needed_mcp_servers"] = ["server-a"]
        (d / "task_config.json").write_text(json.dumps(payload), encoding="utf-8")

    p = root / "utils" / "roles"
    p.mkdir(parents=True, exist_ok=True)
    if correct_order:
        source = f"""
async def setup():
    {CONNECT_MARKER}
    self.agent = Agent({BIND_SERVERS_MARKER})
    {GET_TOOLS_MARKER}
"""
    else:
        source = f"""
async def setup():
    {GET_TOOLS_MARKER}
    {CONNECT_MARKER}
    self.agent = Agent({BIND_SERVERS_MARKER})
"""
    (p / "task_agent.py").write_text(source, encoding="utf-8")


class ToolathlonToolDiscoveryScopeCutV1Tests(unittest.TestCase):
    def test_exact_108_predeclared_server_configs_prove_partial_scope_cut(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_checkout(root)
            out = evaluate_checkout(root)
            self.assertTrue(out["public_harness_observation_pass"])
            self.assertEqual(out["benchmark_task_count"], 108)
            self.assertEqual(out["configs_with_needed_mcp_servers_list"], 108)
            self.assertEqual(out["scope_relation"], "PARTIAL_STRICT_SUBSET__SUPPLEMENT_REQUIRED")
            self.assertFalse(out["toolathlon_standalone_whole_family_closure_admissible"])
            self.assertEqual(
                out["remaining_scope_leaf"],
                "BRAIN_OWNED_UNKNOWN_TOOL_IDENTITY_OR_DISCOVERY_SOURCE_EXPANSION_PROOF",
            )
            self.assertEqual(out["family_credit_delta"], 0)

    def test_107_tasks_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_checkout(root, task_count=107)
            out = evaluate_checkout(root)
            self.assertFalse(out["public_harness_observation_pass"])
            self.assertIn("TASK_CONFIG_COUNT_NOT_108::107", out["errors"])

    def test_missing_needed_mcp_servers_field_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_checkout(root, include_server_field=False)
            out = evaluate_checkout(root)
            self.assertFalse(out["public_harness_observation_pass"])
            self.assertIn("NEEDED_MCP_SERVERS_NOT_LIST_IN_ALL_TASKS::0", out["errors"])

    def test_tool_enumeration_must_follow_server_connection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _make_checkout(root, correct_order=False)
            out = evaluate_checkout(root)
            self.assertFalse(out["public_harness_observation_pass"])
            self.assertIn("TOOL_SURFACE_PREEXECUTION_ENUMERATION_NOT_PROVED", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
