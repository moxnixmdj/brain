from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import tb_science_rank20_preclaim_binding_v1 as v


class Rank20PreclaimBindingTests(unittest.TestCase):
    def test_current_preclaim_passes_and_derives_exact_identity(self):
        result = v.verify()
        self.assertTrue(result["pass"], result)
        self.assertEqual(
            result["execution_claim_binding_digest"],
            "sha256:8ffb9a1041ef950a8f8fa3a876a9deeb964ebd099ebbd4e2d182b8f256f87d23",
        )
        self.assertEqual(
            result["logical_attempt_id_v2"],
            "7d5b448bf14e7c6ed675e131e693e53b986288af1a5498edc434e8071219f2ce",
        )
        self.assertFalse(result["execution_authority"])
        self.assertFalse(result["activation_authority"])
        self.assertEqual(result["benchmark_trials_consumed"], 0)

    def _mutated_json(self, source: Path, mutate):
        value = json.loads(source.read_text(encoding="utf-8"))
        mutate(value)
        td = tempfile.TemporaryDirectory()
        path = Path(td.name) / source.name
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return td, path

    def test_task_content_in_claim_fails_closed(self):
        td, path = self._mutated_json(v.CLAIM, lambda x: x.__setitem__("task_content", "forbidden"))
        try:
            with patch.object(v, "CLAIM", path):
                result = v.verify()
            self.assertFalse(result["pass"])
            self.assertTrue(any("PRECLAIM_FORBIDDEN_FIELDS" in x for x in result["errors"]))
        finally:
            td.cleanup()

    def test_premature_execution_authority_fails_closed(self):
        td, path = self._mutated_json(v.ADMISSION, lambda x: x.__setitem__("execution_authority", True))
        try:
            with patch.object(v, "ADMISSION", path):
                result = v.verify()
            self.assertFalse(result["pass"])
            self.assertIn("ADMISSION_EXECUTION_AUTHORITY_MUST_BE_FALSE", result["errors"])
        finally:
            td.cleanup()

    def test_claim_task_digest_drift_fails_closed(self):
        td, path = self._mutated_json(
            v.CLAIM,
            lambda x: x.__setitem__("task_digest", "sha256:" + "0" * 64),
        )
        try:
            with patch.object(v, "CLAIM", path):
                result = v.verify()
            self.assertFalse(result["pass"])
            self.assertIn("CLAIM_TASK_DIGEST_MISMATCH", result["errors"])
        finally:
            td.cleanup()

    def test_bound_source_blob_drift_fails_closed(self):
        td, path = self._mutated_json(
            v.CLAIM,
            lambda x: x.__setitem__("agent_v13_blob", "0" * 40),
        )
        try:
            with patch.object(v, "CLAIM", path):
                result = v.verify()
            self.assertFalse(result["pass"])
            self.assertIn("AGENT_V13_BLOB_MISMATCH", result["errors"])
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
