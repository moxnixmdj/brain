from __future__ import annotations

import json
import unittest

from canonical.runtime import astra_runtime as runtime


class WriteJsonRecordsConfinementTests(unittest.TestCase):
    def test_ephemeral_json_output_is_allowed(self):
        rel = "canonical/astra_runtime/tmp/WRITE_JSON_RECORDS_CONFINEMENT_TEST.json"
        path = runtime.ROOT / rel
        try:
            out = runtime._goal_action({
                "type": "write_json_records",
                "args": {
                    "output_path": rel,
                    "fields": ["value"],
                    "records": [{"value": 7}],
                },
            })
            self.assertTrue(out["verified"])
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), [{"value": 7}])
        finally:
            if path.exists():
                path.unlink()

    def test_governance_output_is_denied_before_write(self):
        rel = "canonical/governance/__WRITE_JSON_RECORDS_DENIED_SENTINEL__.json"
        path = runtime.ROOT / rel
        self.assertFalse(path.exists())
        with self.assertRaisesRegex(
            runtime.Blocker,
            "RUNTIME_MUTATION_OUTSIDE_EPHEMERAL_TMP",
        ):
            runtime._goal_action({
                "type": "write_json_records",
                "args": {
                    "output_path": rel,
                    "fields": ["value"],
                    "records": [{"value": 7}],
                },
            })
        self.assertFalse(path.exists())

    def test_tmp_traversal_into_missions_is_denied(self):
        rel = "canonical/astra_runtime/tmp/../missions/__WRITE_JSON_RECORDS_DENIED_SENTINEL__.json"
        path = (runtime.ROOT / rel).resolve()
        self.assertFalse(path.exists())
        with self.assertRaisesRegex(
            runtime.Blocker,
            "RUNTIME_MUTATION_OUTSIDE_EPHEMERAL_TMP",
        ):
            runtime._goal_action({
                "type": "write_json_records",
                "args": {
                    "output_path": rel,
                    "fields": ["value"],
                    "records": [{"value": 7}],
                },
            })
        self.assertFalse(path.exists())


    def test_shared_mutation_helper_allows_nested_tmp_artifact(self):
        rel = "canonical/astra_runtime/tmp/nested/artifact.png"
        observed = runtime._safe_repo_mutation_path(rel)
        self.assertEqual(
            observed,
            (runtime.ROOT / rel).resolve(),
        )

    def test_shared_mutation_helper_denies_canonical_runtime(self):
        with self.assertRaisesRegex(
            runtime.Blocker,
            "RUNTIME_MUTATION_OUTSIDE_EPHEMERAL_TMP",
        ):
            runtime._safe_repo_mutation_path("canonical/runtime/overwrite.py")



if __name__ == "__main__":
    unittest.main(verbosity=2)
