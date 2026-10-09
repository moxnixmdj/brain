import unittest

from canonical.runtime.d_finality_coverage_gate_v1 import (
    DFinalityCoverageError,
    evaluate,
)

H = "a" * 64
I = "b" * 64
J = "c" * 64
K = "d" * 64
L = "e" * 64
M = "f" * 64


def row(capability_id, *, provider=J, material=I, cert=H, policy=K, epoch=L, closure=M):
    return {
        "capability_id": capability_id,
        "status": "VERIFIED_D_FINAL_CURRENT",
        "d_certificate_sha256": cert,
        "material_certificate_sha256": material,
        "provider_theorem_sha256": provider,
        "policy_sha256": policy,
        "execution_epoch_sha256": epoch,
        "material_closure_root": closure,
        "fresh_replay_pass": True,
        "independent_replay_pass": True,
        "donor_authority_zero": True,
        "undeclared_dependency_count": 0,
    }


def registry(rows):
    return {
        "schema": "PROJECT_BRAIN_D_FINALITY_CERTIFICATE_REGISTRY_V1",
        "status": "ACTIVE_FAIL_CLOSED",
        "default": "NOT_D_FINAL_UNLESS_EXACT_CURRENT_ROW",
        "rows": rows,
    }


class CoverageTests(unittest.TestCase):
    def test_empty_registry_fails_with_exact_missing_set(self):
        out = evaluate(["engine:A", "bound:B"], registry([]))
        self.assertFalse(out["pass"])
        self.assertEqual(out["missing_d_certificate_ids"], ["bound:B", "engine:A"])
        self.assertEqual(out["d_final_owned_capability_count"], 0)

    def test_exact_current_rows_close_coverage(self):
        out = evaluate(
            ["engine:A", "bound:B"],
            registry([
                row("engine:A", provider="1" * 64, material="2" * 64, cert="3" * 64),
                row("bound:B", provider="4" * 64, material="5" * 64, cert="6" * 64),
            ]),
        )
        self.assertTrue(out["pass"])
        self.assertEqual(out["d_final_owned_capability_count"], 2)
        self.assertEqual(out["missing_d_certificate_count"], 0)

    def test_provider_theorem_can_be_shared_but_material_certificate_remains_per_member(self):
        shared = "1" * 64
        out = evaluate(
            ["bound:A", "bound:B"],
            registry([
                row("bound:A", provider=shared, material="2" * 64, cert="3" * 64),
                row("bound:B", provider=shared, material="4" * 64, cert="5" * 64),
            ]),
        )
        self.assertTrue(out["pass"])
        self.assertEqual(out["provider_theorem_count"], 1)
        self.assertEqual(out["provider_theorem_reuse"][0]["member_count"], 2)
        self.assertTrue(out["member_material_certificate_required_even_under_provider_reuse"])

    def test_noncurrent_row_does_not_cover(self):
        r = row("engine:A")
        r["status"] = "HISTORICAL_D_FINAL"
        out = evaluate(["engine:A"], registry([r]))
        self.assertFalse(out["pass"])
        self.assertEqual(out["missing_d_certificate_ids"], ["engine:A"])

    def test_false_replay_or_donor_claim_fails_not_merely_omits(self):
        for key, expected in (
            ("fresh_replay_pass", "ROW_FRESH_REPLAY_NOT_PASS"),
            ("independent_replay_pass", "ROW_INDEPENDENT_REPLAY_NOT_PASS"),
            ("donor_authority_zero", "ROW_DONOR_AUTHORITY_NOT_ZERO"),
        ):
            with self.subTest(key=key):
                r = row("engine:A")
                r[key] = False
                with self.assertRaisesRegex(DFinalityCoverageError, expected):
                    evaluate(["engine:A"], registry([r]))

    def test_undeclared_dependency_fails(self):
        r = row("engine:A")
        r["undeclared_dependency_count"] = 1
        with self.assertRaisesRegex(DFinalityCoverageError, "UNDECLARED_DEPENDENCY_COUNT_NOT_ZERO"):
            evaluate(["engine:A"], registry([r]))

    def test_stale_nonlive_certificates_do_not_expand_live_ownership(self):
        out = evaluate(
            ["engine:A"],
            registry([row("engine:A"), row("engine:OLD", cert="1" * 64)]),
        )
        self.assertTrue(out["pass"])
        self.assertEqual(out["d_final_owned_capability_count"], 1)
        self.assertEqual(out["stale_nonlive_certificate_ids"], ["engine:OLD"])

    def test_duplicate_capability_row_fails(self):
        with self.assertRaisesRegex(DFinalityCoverageError, "DUPLICATE_CAPABILITY_ROW"):
            evaluate(["engine:A"], registry([row("engine:A"), row("engine:A", cert="1" * 64)]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
