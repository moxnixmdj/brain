from __future__ import annotations

import unittest
from unittest.mock import patch

import canonical.runtime.root3_subprocess_effect_class_registry_v1 as registry


class Root3SubprocessEffectClassRegistryTests(unittest.TestCase):
    def test_exact_current_22_site_partition(self):
        out = registry.compile_effect_classes()
        self.assertEqual(out["site_count"], 22)
        self.assertEqual(out["class_count"], 7)
        self.assertEqual(
            out["class_counts"],
            {
                "ARBITRARY_COMMAND_EXECUTION": 2,
                "BOUND_CHILD_CODE_EXECUTION": 5,
                "DECLARED_ARTIFACT_PRODUCTION": 1,
                "LOCAL_LOOPBACK_SERVICE": 1,
                "PACKAGE_ENV_MUTATION": 3,
                "READ_ONLY_DECLARED_QUERY": 8,
                "TEMPORARY_FILESYSTEM_TRANSFORM": 2,
            },
        )
        self.assertEqual(out["duplicate_policy_obligations_deleted"], 15)
        self.assertEqual(
            len({(x["module_path"], x["lineno"], x["process_api"]) for x in out["classified_sites"]}),
            29,
        )

    def test_every_class_has_explicit_proof_residuals(self):
        out = registry.compile_effect_classes()
        self.assertEqual(
            set(out["class_proof_residuals"]),
            set(out["class_counts"]),
        )
        for residuals in out["class_proof_residuals"].values():
            self.assertTrue(residuals)

    def test_missing_site_mapping_fails_closed(self):
        reduced = dict(registry.EXPECTED)
        reduced.pop(next(iter(reduced)))
        with patch.object(registry, "EXPECTED", reduced):
            with self.assertRaisesRegex(
                registry.EffectClassRegistryError,
                "PROCESS_SITE_UNIVERSE_DRIFT",
            ):
                registry.compile_effect_classes()

    def test_new_fake_site_mapping_fails_closed(self):
        expanded = dict(registry.EXPECTED)
        expanded[("canonical/runtime/fake.py", 1, "subprocess.run")] = (
            "READ_ONLY_DECLARED_QUERY"
        )
        with patch.object(registry, "EXPECTED", expanded):
            with self.assertRaisesRegex(
                registry.EffectClassRegistryError,
                "PROCESS_SITE_UNIVERSE_DRIFT",
            ):
                registry.compile_effect_classes()

    def test_classification_does_not_claim_hidden_child_safety(self):
        out = registry.compile_effect_classes()
        truth = out["truth_boundary"]
        self.assertFalse(truth["classification_proves_child_internal_effect_safety"])
        self.assertFalse(truth["classification_proves_semantic_authorization"])
        self.assertFalse(truth["classification_proves_c1_or_c2_complete"])
        self.assertEqual(out["accounting"]["acceptance_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
