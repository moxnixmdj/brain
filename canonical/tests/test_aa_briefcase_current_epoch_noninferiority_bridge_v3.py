import unittest

from canonical.runtime.aa_briefcase_current_epoch_noninferiority_bridge_v3 import (
    PREDICATES,
    compile_current_epoch_noninferiority,
)
from canonical.tests.test_aa_briefcase_scope_complete_dominance_v1 import (
    certificate,
    target,
)
from canonical.tests.test_aa_briefcase_minimal_owner_attestation_v1 import statement
from canonical.tests.test_aa_briefcase_core_owner_attestation_v2 import statement as core_statement
from canonical.tests.test_aa_briefcase_official_github_publication_v1 import publication
from canonical.tests.test_aa_briefcase_owner_signature_verifier_v1 import make_signed


def score_result(score=1807):
    return {
        "schema": "X",
        "status": "VERIFIED_COMPARABLE_BRAIN_SCORE",
        "independent_or_owner_verified": True,
        "benchmark": "AA-Briefcase v1.1",
        "model": "Claude Opus 5.5 (Max, Default Fallback)",
        "unit": "Elo",
        "brain_score": score,
        "subject_sha256": "a" * 64,
        "matched_current_owner_epoch": True,
        "target_observed_date": "2026-10-08",
        "opus55_reference_score": 1807,
    }


class T(unittest.TestCase):
    def test_direct_dominance_passes_both_aliases(self):
        out = compile_current_epoch_noninferiority(
            target(),
            {"mode": "SCOPE_COMPLETE_DIRECT_DOMINANCE", "payload": certificate()},
        )
        self.assertEqual(out["predicate_results"], {p: True for p in PREDICATES})
        self.assertFalse(out["numeric_elo_reconstruction_required"])
        self.assertFalse(out["numeric_comparable_elo_used"])
        self.assertFalse(out["official_owner_elo_claimed"])
        self.assertTrue(out["single_result_reused_across_predicates"])
        self.assertFalse(out["historical_epoch_rewritten"])

    def test_official_github_publication_passes_both_aliases(self):
        out = compile_current_epoch_noninferiority(
            target(),
            {
                "mode": "OFFICIAL_GITHUB_PUBLICATION",
                "payload": {"publication": publication()},
            },
        )
        self.assertEqual(out["predicate_results"], {p: True for p in PREDICATES})
        self.assertEqual(out["comparison_route"], "OFFICIAL_GITHUB_PUBLICATION")
        self.assertFalse(out["numeric_elo_reconstruction_required"])
        self.assertFalse(out["numeric_comparable_elo_used"])
        self.assertFalse(out["official_owner_elo_claimed"])

    def test_core_owner_attestation_passes_both_aliases(self):
        s = core_statement()
        bundle, binding = make_signed(s)
        out = compile_current_epoch_noninferiority(
            target(binding),
            {
                "mode": "CORE_OWNER_ATTESTATION",
                "payload": {
                    "statement": s,
                    "signature_bundle": bundle,
                },
            },
        )
        self.assertEqual(out["predicate_results"], {p: True for p in PREDICATES})
        self.assertEqual(out["comparison_route"], "CORE_OWNER_ATTESTATION")
        self.assertFalse(out["numeric_elo_reconstruction_required"])
        self.assertFalse(out["numeric_comparable_elo_used"])
        self.assertFalse(out["official_owner_elo_claimed"])

    def test_minimal_owner_attestation_passes_both_aliases(self):
        s = statement()
        bundle, binding = make_signed(s)
        out = compile_current_epoch_noninferiority(
            target(binding),
            {
                "mode": "MINIMAL_OWNER_ATTESTATION",
                "payload": {
                    "statement": s,
                    "signature_bundle": bundle,
                },
            },
        )
        self.assertEqual(out["predicate_results"], {p: True for p in PREDICATES})
        self.assertEqual(out["comparison_route"], "MINIMAL_OWNER_ATTESTATION")
        self.assertFalse(out["numeric_elo_reconstruction_required"])
        self.assertFalse(out["numeric_comparable_elo_used"])
        self.assertFalse(out["official_owner_elo_claimed"])

    def test_score_route_still_works(self):
        out = compile_current_epoch_noninferiority(
            target(),
            {"mode": "MATCHED_CURRENT_EPOCH_ELO", "payload": score_result(1807)},
        )
        self.assertEqual(out["predicate_results"], {p: True for p in PREDICATES})
        self.assertTrue(out["numeric_elo_reconstruction_required"])
        self.assertTrue(out["numeric_comparable_elo_used"])
        self.assertFalse(out["official_owner_elo_claimed"])

    def test_below_score_fails_without_affecting_direct_route(self):
        out = compile_current_epoch_noninferiority(
            target(),
            {"mode": "MATCHED_CURRENT_EPOCH_ELO", "payload": score_result(1806.9)},
        )
        self.assertEqual(out["predicate_results"], {p: False for p in PREDICATES})
