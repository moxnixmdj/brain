from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import raw_goal_python_test_audit_acceptance_v1 as a
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract


GOAL = (
    "Audit Python unittest files under canonical/tests matching test_*.py and "
    "save the report to canonical/astra_runtime/tmp/R2_TEST_AUDIT.json, "
    "reporting tests, passed, failed, errors, and skipped counts."
)


class RawGoalPythonTestAuditAcceptanceV1Tests(unittest.TestCase):
    def test_strict_preflight_binds_exact_inputs(self):
        out = a.preflight(GOAL)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["matched"])
        self.assertEqual(out["capability_id"], a.CAPABILITY)
        self.assertEqual(
            out["bound_inputs"],
            {
                "source_root": "canonical/tests",
                "pattern": "test_*.py",
                "output_path": "canonical/astra_runtime/tmp/R2_TEST_AUDIT.json",
                "timeout_s": 180,
            },
        )
        self.assertFalse(out["semantic_authority"])
        self.assertFalse(out["execution_authority"])

    def test_unmodeled_extra_instruction_does_not_match(self):
        out = a.preflight(GOAL + " Also delete the source tests.")
        self.assertFalse(out["pass"])
        self.assertFalse(out["matched"])

    def test_non_ephemeral_output_does_not_match(self):
        out = a.preflight(
            "Audit Python unittest files under canonical/tests matching test_*.py "
            "and save the report to canonical/governance/report.json, reporting "
            "tests, passed, failed, errors, and skipped counts."
        )
        self.assertFalse(out["matched"])

    @patch.object(a.astra_runtime, "_goal_action")
    def test_verified_execution_plus_fresh_replay_accepts_all_raw_obligations(self, fresh):
        pf = a.preflight(GOAL)
        self.assertTrue(pf["pass"])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "canonical/tests"
            output = root / "canonical/astra_runtime/tmp/R2_TEST_AUDIT.json"
            source.mkdir(parents=True)
            output.parent.mkdir(parents=True)
            test_file = source / "test_demo.py"
            test_file.write_text(
                "import unittest\n"
                "class T(unittest.TestCase):\n"
                "    def test_ok(self): self.assertTrue(True)\n"
                "if __name__ == '__main__': unittest.main()\n",
                encoding="utf-8",
            )
            report = {
                "schema": "PROJECT_BRAIN_PYTHON_TEST_AUDIT_V1",
                "source_root": "canonical/tests",
                "pattern": "test_*.py",
                "records": [{
                    "path": "canonical/tests/test_demo.py",
                    "sha256": __import__("hashlib").sha256(test_file.read_bytes()).hexdigest(),
                    "exit_code": 0,
                    "tests": 1,
                    "passed": 1,
                    "failed": 0,
                    "errors": 0,
                    "skipped": 0,
                    "duration_s": 0.01,
                    "reported_test_duration_s": 0.0,
                }],
                "totals": {
                    "files": 1,
                    "tests": 1,
                    "passed": 1,
                    "failed": 0,
                    "errors": 0,
                    "skipped": 0,
                },
            }
            output.write_text(json.dumps(report), encoding="utf-8")
            raw_contract = compile_contract(
                GOAL,
                source_id="test",
                routing_target_effects=[a.ROUTING_EFFECT],
            )
            result = {
                "output_path": "canonical/astra_runtime/tmp/R2_TEST_AUDIT.json",
                "output_sha256": __import__("hashlib").sha256(output.read_bytes()).hexdigest(),
                "file_count": 1,
                "test_count": 1,
                "passed_count": 1,
                "failed_count": 0,
                "error_count": 0,
                "skipped_count": 0,
                "output_verified": True,
            }
            execution = {
                "pass": True,
                "capability_id": a.CAPABILITY,
                "composition_capsule_head_hash": "sha256:verified",
                "rendered_action": {
                    "type": "invoke_capability",
                    "args": {
                        "capability_id": a.CAPABILITY,
                        **pf["bound_inputs"],
                    },
                },
                "result": result,
            }
            fresh.return_value = {
                "type": "assert_python_test_audit_supported_by_fresh_execution",
                "verified": True,
                "audit_path": pf["bound_inputs"]["output_path"],
                "source_root": pf["bound_inputs"]["source_root"],
                "pattern": pf["bound_inputs"]["pattern"],
                "totals": dict(report["totals"]),
                "errors": [],
            }
            out = a.verify(
                goal=GOAL,
                inputs=pf["bound_inputs"],
                execution=execution,
                raw_contract=raw_contract,
                root=root,
            )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertEqual(
            out["accepted_obligation_ids"],
            raw_contract["acceptance_contract"]["required_obligation_ids"],
        )
        fresh.assert_called_once()

    @patch.object(a.astra_runtime, "_goal_action")
    def test_fresh_replay_failure_blocks_acceptance(self, fresh):
        pf = a.preflight(GOAL)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "canonical/tests"
            output = root / "canonical/astra_runtime/tmp/R2_TEST_AUDIT.json"
            source.mkdir(parents=True)
            output.parent.mkdir(parents=True)
            test_file = source / "test_demo.py"
            test_file.write_text("x=1\n", encoding="utf-8")
            report = {
                "schema": "PROJECT_BRAIN_PYTHON_TEST_AUDIT_V1",
                "source_root": "canonical/tests",
                "pattern": "test_*.py",
                "records": [{"path": "canonical/tests/test_demo.py"}],
                "totals": {"files": 1, "tests": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0},
            }
            output.write_text(json.dumps(report), encoding="utf-8")
            raw_contract = compile_contract(
                GOAL,
                source_id="test",
                routing_target_effects=[a.ROUTING_EFFECT],
            )
            execution = {
                "pass": True,
                "capability_id": a.CAPABILITY,
                "composition_capsule_head_hash": "sha256:verified",
                "rendered_action": {
                    "args": {"capability_id": a.CAPABILITY, **pf["bound_inputs"]}
                },
                "result": {"output_verified": True},
            }
            fresh.return_value = {
                "verified": False,
                "errors": ["record_mismatch:canonical/tests/test_demo.py"],
            }
            out = a.verify(
                goal=GOAL,
                inputs=pf["bound_inputs"],
                execution=execution,
                raw_contract=raw_contract,
                root=root,
            )
        self.assertFalse(out["pass"])
        self.assertFalse(out["semantic_acceptance_complete"])
        self.assertFalse(out["actual_goal_satisfaction_verified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
