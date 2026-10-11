from __future__ import annotations

import json
import pathlib
import unittest

from canonical.runtime.pure_projection_consumer_guard_v1 import (
    evaluate_pure_consumer,
)
from canonical.runtime.pure_sealed_projection_consumer_v1 import (
    run_pure_sealed_consumer,
)
from canonical.runtime.sealed_field_projection_consumer_v1 import (
    PROJECTION_FILE,
    RUNNER_SCHEMA,
)


GOOD = """
def helper(x):
    return x == 7

def evaluate(projection):
    proved = projection["sources"][0]["projection"]["/authority/proved"]
    open_count = projection["sources"][0]["projection"]["/authority/open"]
    return {
        "still_valid": helper(proved) and open_count == 12,
        "source_count": projection["source_count"],
    }
"""


class ExecutingFakeLauncher:
    def __init__(self):
        self.policies = []

    def __call__(self, policy):
        self.policies.append(policy)
        root = pathlib.Path(policy["input_dir"])
        projection = json.loads(
            (root / PROJECTION_FILE).read_text(encoding="utf-8")
        )
        source = (root / "consumer.py").read_text(encoding="utf-8")
        result = evaluate_pure_consumer(
            source=source,
            projection=projection,
        )
        if not result["pass"]:
            return {
                "status": "CHILD_EXITED",
                "returncode": 1,
                "policy_sha256": "f" * 64,
                "broker_payload": b"{}",
            }
        payload = {
            "schema": RUNNER_SCHEMA,
            "projection_bundle_sha256": projection[
                "projection_bundle_sha256"
            ],
            "consumer_result": result["consumer_result"],
        }
        return {
            "status": "CHILD_EXITED",
            "returncode": 0,
            "policy_sha256": "f" * 64,
            "broker_payload": json.dumps(
                payload, separators=(",", ":")
            ).encode(),
        }


class PureSealedProjectionConsumerTests(unittest.TestCase):
    def documents(self):
        return {
            "canonical/governance/A.json": {
                "authority": {"proved": 7, "open": 12},
                "scheduler": {"generation": 44},
            }
        }

    def dependencies(self):
        return {
            "canonical/governance/A.json": [
                "/authority/proved",
                "/authority/open",
            ]
        }

    def test_valid_consumer_is_both_pure_and_sealed(self):
        launcher = ExecutingFakeLauncher()
        out = run_pure_sealed_consumer(
            source_documents=self.documents(),
            field_dependencies=self.dependencies(),
            consumer_source=GOOD,
            launcher=launcher,
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["consumer_result"]["still_valid"])
        self.assertEqual(out["consumer_result"]["source_count"], 1)
        self.assertEqual(out["closed_world_input_entry_count"], 3)
        self.assertFalse(out["helper_files_allowed"])
        self.assertFalse(out["undeclared_host_repository_reads_available"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_import_fails_before_sealed_execution(self):
        launcher = ExecutingFakeLauncher()
        out = run_pure_sealed_consumer(
            source_documents=self.documents(),
            field_dependencies=self.dependencies(),
            consumer_source=(
                "import os\n"
                "def evaluate(projection):\n"
                "    return {'x': 1}\n"
            ),
            launcher=launcher,
        )
        self.assertFalse(out["pass"])
        self.assertIn("MODULE_BODY_MUST_CONTAIN_ONLY_FUNCTIONS", out["reason"])
        self.assertEqual(launcher.policies, [])

    def test_ambient_open_fails_before_sealed_execution(self):
        launcher = ExecutingFakeLauncher()
        out = run_pure_sealed_consumer(
            source_documents=self.documents(),
            field_dependencies=self.dependencies(),
            consumer_source=(
                "def evaluate(projection):\n"
                "    x = open('/tmp/x')\n"
                "    return {'x': x}\n"
            ),
            launcher=launcher,
        )
        self.assertFalse(out["pass"])
        self.assertIn("UNKNOWN_GLOBAL_NAME:evaluate:open", out["reason"])
        self.assertEqual(launcher.policies, [])

    def test_missing_evaluate_entry_fails_closed(self):
        launcher = ExecutingFakeLauncher()
        out = run_pure_sealed_consumer(
            source_documents=self.documents(),
            field_dependencies=self.dependencies(),
            consumer_source="def helper(x):\n    return x\n",
            launcher=launcher,
        )
        self.assertFalse(out["pass"])
        self.assertIn("EVALUATE_ENTRY_REQUIRED", out["reason"])
        self.assertEqual(launcher.policies, [])

    def test_declared_field_change_changes_projection_binding(self):
        launcher_a = ExecutingFakeLauncher()
        a = run_pure_sealed_consumer(
            source_documents=self.documents(),
            field_dependencies=self.dependencies(),
            consumer_source=GOOD,
            launcher=launcher_a,
        )
        docs = self.documents()
        docs["canonical/governance/A.json"]["authority"]["open"] = 13
        launcher_b = ExecutingFakeLauncher()
        b = run_pure_sealed_consumer(
            source_documents=docs,
            field_dependencies=self.dependencies(),
            consumer_source=GOOD,
            launcher=launcher_b,
        )
        self.assertTrue(a["pass"], a)
        self.assertTrue(b["pass"], b)
        self.assertNotEqual(
            a["projection_bundle_sha256"],
            b["projection_bundle_sha256"],
        )
        self.assertFalse(b["consumer_result"]["still_valid"])

    def test_unrelated_same_file_churn_does_not_change_projection_binding(self):
        launcher_a = ExecutingFakeLauncher()
        a = run_pure_sealed_consumer(
            source_documents=self.documents(),
            field_dependencies=self.dependencies(),
            consumer_source=GOOD,
            launcher=launcher_a,
        )
        docs = self.documents()
        docs["canonical/governance/A.json"]["scheduler"]["generation"] = 999
        launcher_b = ExecutingFakeLauncher()
        b = run_pure_sealed_consumer(
            source_documents=docs,
            field_dependencies=self.dependencies(),
            consumer_source=GOOD,
            launcher=launcher_b,
        )
        self.assertTrue(a["pass"], a)
        self.assertTrue(b["pass"], b)
        self.assertEqual(
            a["projection_bundle_sha256"],
            b["projection_bundle_sha256"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
