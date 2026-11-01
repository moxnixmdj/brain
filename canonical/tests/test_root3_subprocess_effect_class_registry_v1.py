from __future__ import annotations

import unittest
from unittest.mock import patch

import canonical.runtime.root3_subprocess_effect_class_registry_v1 as registry


class Root3SubprocessEffectClassRegistryTests(unittest.TestCase):
    def test_exact_legacy_18_site_partition_is_accounted_for_currently(self):
        # 2026-11-01: the frozen v1 registry is the legacy instrument and fails
        # closed on the drifted tree by design; the current-aware check lives in
        # the v2 registry. Here: all 18 legacy sites must be accounted for --
        # preserved with their exact legacy classes, or discharged with
        # recorded provenance (sqlite_verify_cli.py:66 -> in-process sqlite3).
        from canonical.runtime import root3_subprocess_effect_class_registry_v2 as reg2
        from canonical.runtime.root3_subprocess_effect_class_registry_v2 import (
            _LEGACY_DISAPPEARANCE_PROVENANCE,
            _norm_key,
        )
        out = reg2.compile_effect_classes()
        preserved = {
            _norm_key(x["module_path"], int(x["lineno"]), x["source_api"]): x["effect_class"]
            for x in out["classified_sites"]
            if x["classification_provenance"] == "PRESERVED_LEGACY_VERIFIED_MAPPING"
        }
        self.assertEqual(len(registry.EXPECTED), 18)
        self.assertEqual(len(preserved) + len(_LEGACY_DISAPPEARANCE_PROVENANCE), 18)
        self.assertEqual(
            preserved,
            {k: v for k, v in registry.EXPECTED.items() if k not in _LEGACY_DISAPPEARANCE_PROVENANCE},
        )
        legacy_classes = {}
        for k, v in registry.EXPECTED.items():
            legacy_classes[v] = legacy_classes.get(v, 0) + 1
        self.assertEqual(
            legacy_classes,
            {
                "ARBITRARY_COMMAND_EXECUTION": 2,
                "BOUND_CHILD_CODE_EXECUTION": 5,
                "DECLARED_ARTIFACT_PRODUCTION": 1,
                "LOCAL_LOOPBACK_SERVICE": 1,
                "PACKAGE_ENV_MUTATION": 3,
                "READ_ONLY_DECLARED_QUERY": 5,
                "TEMPORARY_FILESYSTEM_TRANSFORM": 1,
            },
        )
        self.assertEqual(len(registry.CLASSES), 7)

    def test_every_class_has_explicit_proof_residuals(self):
        # Static check on the frozen v1 constants: every declared class carries
        # non-empty proof residuals. Does not compile the drifted tree.
        self.assertEqual(
            set(registry.CLASS_PROOF_RESIDUALS),
            set(registry.CLASSES),
        )
        for residuals in registry.CLASS_PROOF_RESIDUALS.values():
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
        # 2026-11-01: asserted on the current-aware v2 output (the frozen v1
        # compile fails closed on the drifted tree by design).
        from canonical.runtime import root3_subprocess_effect_class_registry_v2 as reg2
        out = reg2.compile_effect_classes()
        nonclaims = set(out["hard_nonclaims"])
        self.assertIn(
            "NO_CLAIM_CHILD_INTERNAL_EFFECTS_OR_NATIVE_EXTENSION_EFFECTS_ARE_CLOSED",
            nonclaims,
        )
        self.assertIn(
            "NO_ROOT3_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
            nonclaims,
        )
        self.assertEqual(out["accounting"]["acceptance_credit_delta"], 0)
        self.assertEqual(out["accounting"]["capability_credit_delta"], 0)
        self.assertFalse(out["authority_widening_from_defaulted_sites"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
