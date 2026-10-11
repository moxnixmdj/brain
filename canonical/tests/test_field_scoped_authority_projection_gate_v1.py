from __future__ import annotations

import copy
import unittest

from canonical.runtime.field_scoped_authority_projection_gate_v1 import (
    GateError,
    bind_receipt,
    check_manifest,
    freeze_manifest,
    sealed_projection,
)


class FieldScopedAuthorityProjectionGateTests(unittest.TestCase):
    def setUp(self):
        self.base = {
            "authority": {
                "proved": 7,
                "open": 12,
                "next": "R2",
            },
            "scheduler": {
                "generation": 44,
                "worker": "alpha",
            },
            "notes": ["a", "b"],
        }
        self.pointers = [
            "/authority/proved",
            "/authority/open",
            "/authority/next",
        ]

    def manifest(self):
        return freeze_manifest(
            self.base,
            self.pointers,
            source_path="canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
            source_blob_sha="1" * 40,
        )

    def test_unrelated_same_file_churn_is_not_stale(self):
        live = copy.deepcopy(self.base)
        live["scheduler"]["generation"] = 45
        live["scheduler"]["worker"] = "beta"
        out = check_manifest(live, self.manifest())
        self.assertFalse(out["stale"], out)
        self.assertEqual(out["changed_dependencies"], [])

    def test_declared_value_change_is_stale(self):
        live = copy.deepcopy(self.base)
        live["authority"]["proved"] = 8
        out = check_manifest(live, self.manifest())
        self.assertTrue(out["stale"])
        self.assertEqual(
            [x["pointer"] for x in out["changed_dependencies"]],
            ["/authority/proved"],
        )

    def test_declared_value_disappearance_is_stale(self):
        live = copy.deepcopy(self.base)
        del live["authority"]["next"]
        out = check_manifest(live, self.manifest())
        self.assertTrue(out["stale"])
        self.assertEqual(out["changed_dependencies"][0]["reason"], "UNRESOLVABLE")

    def test_parent_child_overlap_fails_closed(self):
        with self.assertRaises(GateError):
            freeze_manifest(
                self.base,
                ["/authority", "/authority/proved"],
                source_path="x.json",
            )

    def test_manifest_tampering_fails_closed(self):
        manifest = self.manifest()
        manifest["dependencies"][0]["value_sha256"] = "0" * 64
        with self.assertRaises(GateError):
            check_manifest(self.base, manifest)

    def test_float_authority_value_fails_closed(self):
        with self.assertRaises(GateError):
            freeze_manifest(
                {"x": 1.25},
                ["/x"],
                source_path="x.json",
            )

    def test_projection_exposes_only_declared_inputs(self):
        out = sealed_projection(self.base, ["/authority/proved"])
        self.assertEqual(out, {"/authority/proved": 7})
        self.assertNotIn("/scheduler/generation", out)

    def test_receipt_is_content_bound_and_zero_credit(self):
        manifest = self.manifest()
        out = bind_receipt(
            manifest=manifest,
            candidate_diff_sha256="2" * 64,
            verifier_sha256="3" * 64,
            test_suite_sha256="4" * 64,
            live_parent_commit_sha="5" * 40,
            verdict="PASS",
        )
        self.assertEqual(out["dependency_manifest_sha256"], manifest["manifest_sha256"])
        self.assertEqual(out["projection_sha256"], manifest["projection_sha256"])
        self.assertEqual(out["terminal_credit_delta"], 0)
        self.assertEqual(len(out["receipt_sha256"]), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
