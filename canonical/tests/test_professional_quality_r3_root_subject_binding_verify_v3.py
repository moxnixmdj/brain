from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r3_root_subject_binding_verify_v3 as v3

ROOT = Path(__file__).resolve().parents[2]


class R3V3SuccessorTests(unittest.TestCase):
    def _docs(self):
        binding = json.loads((ROOT / v3.BINDING_PATH).read_text(encoding="utf-8"))
        prior = json.loads((ROOT / v3.PRIOR_PATH).read_text(encoding="utf-8"))
        return binding, prior

    def test_current_successor_replays_v2_and_passes(self):
        out = v3.verify(repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["root_subject_binding_authority"])
        self.assertFalse(out["global_subject_identity_authority"])
        self.assertFalse(out["global_r3_root_closed"])
        self.assertFalse(out["terminal_authority"])

    def test_global_subject_self_authority_true_fails(self):
        binding, prior = self._docs()
        binding["global_subject_identity_authority"] = True
        self.assertEqual(
            v3._validate_successor(binding, prior),
            "V3_GLOBAL_SUBJECT_SELF_AUTHORITY_FORBIDDEN",
        )

    def test_exact_instance_drift_fails(self):
        binding, prior = self._docs()
        binding["exact_instance"] = deepcopy(binding["exact_instance"])
        binding["exact_instance"]["run_context_sha256"] = "sha256:drift"
        self.assertEqual(
            v3._validate_successor(binding, prior),
            "V3_EXACT_INSTANCE_DRIFT",
        )

    def test_prior_limitation_cannot_be_removed(self):
        binding, prior = self._docs()
        binding["binding_scope"] = deepcopy(binding["binding_scope"])
        lost = prior["binding_scope"]["limitations"][0]
        binding["binding_scope"]["limitations"] = [
            x for x in binding["binding_scope"]["limitations"] if x != lost
        ]
        self.assertEqual(
            v3._validate_successor(binding, prior),
            "V3_PRIOR_LIMITATION_LOST",
        )

    def test_predecessor_binding_is_exactly_named(self):
        binding, prior = self._docs()
        binding["supersedes"] = deepcopy(binding["supersedes"])
        binding["supersedes"]["git_blob_sha"] = "0" * 40
        self.assertEqual(
            v3._validate_successor(binding, prior),
            "V3_SUPERSEDES_INVALID",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
