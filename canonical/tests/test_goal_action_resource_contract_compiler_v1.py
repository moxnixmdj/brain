from __future__ import annotations

import unittest
from unittest.mock import patch

import canonical.runtime.goal_action_resource_contract_compiler_v1 as compiler


class GoalActionResourceContractCompilerTests(unittest.TestCase):
    def source(self):
        return (compiler.ROOT / compiler.RUNTIME_REL).read_text(encoding="utf-8")

    def test_exact_bound_partition(self):
        out = compiler.evaluate()
        self.assertEqual(out["status"], "PASS__DIRECT_RESOURCE_CONTRACT_PARTITION_COMPILED", out)
        self.assertEqual(out["action_count"], 48)
        self.assertEqual(out["direct_contractible_count"], 29)
        self.assertEqual(out["blocked_pending_gateway_count"], 19)
        self.assertFalse(out["runtime_enforcement_proved"])
        self.assertFalse(out["transitive_helper_completeness_proved"])
        self.assertFalse(out["no_bypass_credit"])

    def test_file_writer_and_reader_are_direct_contracts(self):
        out = compiler.compile_contracts(self.source())
        rows = {x["action_type"]: x for x in out["rows"]}
        self.assertEqual(rows["write_json_records"]["repo_write_argument_fields"], ["output_path"])
        self.assertEqual(rows["read_file"]["repo_read_argument_fields"], ["path"])
        self.assertEqual(rows["write_json_records"]["status"], "DIRECT_CONTRACTIBLE")
        self.assertEqual(rows["read_file"]["status"], "DIRECT_CONTRACTIBLE")

    def test_search_text_direct_root_access_is_blocked(self):
        out = compiler.compile_contracts(self.source())
        rows = {x["action_type"]: x for x in out["rows"]}
        row = rows["search_text"]
        self.assertEqual(row["status"], "BLOCKED_PENDING_GATEWAY_PROOF")
        self.assertIn("DIRECT_ROOT_ACCESS_OUTSIDE_SAFE_PATH_GATEWAY", row["missing_gateway_proofs"])

    def test_dynamic_capability_actions_are_blocked(self):
        out = compiler.compile_contracts(self.source())
        rows = {x["action_type"]: x for x in out["rows"]}
        for name in ("invoke_capability", "invoke_capability_by_runtime_value", "invoke_capability_fanout"):
            self.assertIn("DYNAMIC_BOUND_CAPABILITY_EFFECT", rows[name]["missing_gateway_proofs"])

    def test_direct_process_action_is_blocked(self):
        out = compiler.compile_contracts(self.source())
        rows = {x["action_type"]: x for x in out["rows"]}
        self.assertIn("DIRECT_PROCESS_EFFECT", rows["assert_python_test_audit_supported_by_fresh_execution"]["missing_gateway_proofs"])

    def test_derived_path_blocks_read_file(self):
        src = self.source().replace(
            '_safe_repo_path(args.get("path",""))',
            '_safe_repo_path(str(args.get("path","")) + "extra")',
            1,
        )
        out = compiler.compile_contracts(src)
        rows = {x["action_type"]: x for x in out["rows"]}
        self.assertEqual(rows["read_file"]["status"], "BLOCKED_PENDING_GATEWAY_PROOF")
        self.assertIn("DERIVED_OR_UNBOUND_REPO_PATH", rows["read_file"]["missing_gateway_proofs"])

    def test_runtime_blob_drift_fails_closed(self):
        with patch.object(compiler, "EXPECTED_RUNTIME_BLOB", "0" * 40):
            out = compiler.evaluate()
        self.assertEqual(out["status"], "FAIL_CLOSED__RUNTIME_BLOB_DRIFT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
