from __future__ import annotations

import copy
import unittest

from canonical.runtime.proof_obligation_delta_compiler_v1 import INPUT_SCHEMA, compile_delta

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40


def base():
    return {
        "schema": INPUT_SCHEMA,
        "target": {
            "id": "TARGET",
            "scope_components": [
                {"id": "semantic_self_check", "source_path": "target.json", "source_sha": SHA_A},
                {"id": "recovery", "source_path": "target.json", "source_sha": SHA_A},
            ],
            "required_atoms": ["A", "B"],
            "required_invariants": ["I"],
            "metric_requirements": [
                {"metric": "success", "direction": "higher", "threshold": 0.0},
                {"metric": "misses", "direction": "lower", "threshold": 0.0},
            ],
        },
        "witness": {
            "id": "WITNESS",
            "scope_components": [
                {"id": "w_semantic", "source_path": "witness.json", "source_sha": SHA_B},
                {"id": "w_recovery", "source_path": "witness.json", "source_sha": SHA_B},
            ],
            "proved_atoms": ["WA", "WB"],
            "proved_invariants": ["WI"],
            "metric_bounds": {
                "w_success": {"lower": 0.2},
                "w_misses": {"upper": 0.0},
            },
        },
        "scope_bindings": [
            {
                "witness_component": "w_semantic",
                "target_component": "semantic_self_check",
                "relation": "EXACT",
                "verified": True,
                "independent": True,
                "receipt": {"path": "canonical/verification/scope1.json", "git_blob_sha": SHA_C},
            },
            {
                "witness_component": "w_recovery",
                "target_component": "recovery",
                "relation": "EXACT",
                "verified": True,
                "independent": True,
                "receipt": {"path": "canonical/verification/scope2.json", "git_blob_sha": SHA_D},
            },
        ],
        "atom_bindings": [
            {
                "witness_atom": "WA",
                "target_atom": "A",
                "verified": True,
                "independent": True,
                "receipt": {"path": "canonical/verification/atom-a.json", "git_blob_sha": SHA_C},
            },
            {
                "witness_atom": "WB",
                "target_atom": "B",
                "verified": True,
                "independent": True,
                "receipt": {"path": "canonical/verification/atom-b.json", "git_blob_sha": SHA_D},
            },
        ],
        "invariant_bindings": [
            {
                "witness_invariant": "WI",
                "target_invariant": "I",
                "verified": True,
                "independent": True,
                "receipt": {"path": "canonical/verification/invariant-i.json", "git_blob_sha": SHA_C},
            }
        ],
        "metric_bindings": [
            {
                "witness_metric": "w_success",
                "target_metric": "success",
                "verified": True,
                "independent": True,
                "receipt": {"path": "canonical/verification/metric-success.json", "git_blob_sha": SHA_C},
            },
            {
                "witness_metric": "w_misses",
                "target_metric": "misses",
                "verified": True,
                "independent": True,
                "receipt": {"path": "canonical/verification/metric-misses.json", "git_blob_sha": SHA_D},
            },
        ],
    }


class ProofObligationDeltaCompilerTests(unittest.TestCase):
    def test_exact_explicit_bindings_close(self):
        out = compile_delta(base())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["status"], "CLOSED_BY_EXPLICIT_VERIFIED_BINDINGS")
        self.assertEqual(out["scope_relation"], "EXACT")

    def test_perfect_atoms_and_metrics_do_not_cover_missing_scope(self):
        d = base()
        d["scope_bindings"] = d["scope_bindings"][:1]
        out = compile_delta(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "RESIDUAL_DELTA_OPEN")
        self.assertEqual(out["residual"]["missing_scope_components"], ["recovery"])

    def test_same_names_never_self_bind(self):
        d = base()
        d["witness"]["proved_atoms"] = ["A", "B"]
        d["atom_bindings"] = []
        out = compile_delta(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["residual"]["missing_atoms"], ["A", "B"])

    def test_missing_atom_is_exact_delta(self):
        d = base()
        d["atom_bindings"] = d["atom_bindings"][:1]
        out = compile_delta(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["residual"]["missing_atoms"], ["B"])

    def test_missing_metric_binding_is_exact_delta(self):
        d = base()
        d["metric_bindings"] = d["metric_bindings"][:1]
        out = compile_delta(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["residual"]["missing_metric_bindings"], ["misses"])

    def test_failing_bound_stays_open(self):
        d = base()
        d["witness"]["metric_bounds"]["w_success"]["lower"] = -0.1
        out = compile_delta(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["residual"]["failing_metric_bounds"][0]["metric"], "success")

    def test_unverified_binding_fails_closed(self):
        d = base()
        d["scope_bindings"][0]["independent"] = False
        out = compile_delta(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("SCOPE_BINDING_NOT_INDEPENDENTLY_VERIFIED:0", out["errors"])

    def test_non_content_addressed_receipt_fails_closed(self):
        d = base()
        d["scope_bindings"][0]["receipt"] = "receipt://self-asserted"
        out = compile_delta(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("SCOPE_BINDING_RECEIPT_NOT_CONTENT_ADDRESSED:0", out["errors"])

    def test_duplicate_target_atom_binding_fails_closed(self):
        d = base()
        duplicate = copy.deepcopy(d["atom_bindings"][0])
        duplicate["witness_atom"] = "WB"
        duplicate["receipt"] = {"path": "canonical/verification/duplicate.json", "git_blob_sha": SHA_D}
        d["atom_bindings"].append(duplicate)
        out = compile_delta(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("TARGET_ATOM_MULTIPLY_BOUND:A", out["errors"])

    def test_unbound_scope_provenance_fails_closed(self):
        d = base()
        d["target"]["scope_components"][0]["source_sha"] = "not-a-sha"
        out = compile_delta(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("TARGET_COMPONENT_PROVENANCE_INVALID:semantic_self_check", out["errors"])

    def test_verified_extra_witness_scope_is_proven_stronger(self):
        d = base()
        d["witness"]["scope_components"].append(
            {"id": "extra", "source_path": "witness.json", "source_sha": SHA_C}
        )
        out = compile_delta(d)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["scope_relation"], "PROVEN_STRONGER")


if __name__ == "__main__":
    unittest.main(verbosity=2)
